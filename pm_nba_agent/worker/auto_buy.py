"""Legacy AutoBuy 处理器"""

import copy
from typing import Any, Callable, Optional

from loguru import logger

from .event_bus import EventPublisher
from .market_state import BOTH_SIDE, MarketState
from .order_executor import OrderExecutor, OrderRequest
from .sse_utils import calculate_size, now_iso


class AutoBuyHandler:
    """Legacy AutoBuy：根据策略信号自动买入。"""

    def __init__(
        self,
        task_id: str,
        config_provider: Callable[[], Any],
        market_state: MarketState,
        publisher: EventPublisher,
    ) -> None:
        self.task_id = task_id
        self._config_provider = config_provider
        self.market_state = market_state
        self.publisher = publisher

        self._is_ordering = False
        self._last_order_time: Optional[str] = None
        self._stats: dict[str, dict[str, Any]] = {}

    @property
    def _config(self) -> Any:
        return self._config_provider()

    def _get_auto_buy_config(self) -> dict[str, Any]:
        config = self._config
        auto_buy = config.auto_buy if isinstance(config.auto_buy, dict) else {}
        return copy.deepcopy(auto_buy)

    async def publish_state(self) -> None:
        cfg = self._get_auto_buy_config()
        payload = {
            "enabled": bool(cfg.get("enabled", False)),
            "is_ordering": self._is_ordering,
            "last_order_time": self._last_order_time,
            "stats": self._stats,
            "default": cfg.get("default", {}),
            "strategy_rules": cfg.get("strategy_rules", {}),
            "timestamp": now_iso(),
        }
        await self.publisher.publish("auto_buy_state", payload)

    async def on_strategy_signal(self, strategy_id: str, rule: dict[str, Any]) -> dict[str, Any]:
        if self._is_ordering:
            return {
                "success": False,
                "orders": [],
                "error": "下单中",
                "source": "task_auto_buy",
                "strategy_id": strategy_id,
            }

        self._is_ordering = True
        await self.publish_state()

        cfg = self._get_auto_buy_config()
        default_cfg = cfg.get("default", {})

        config = self._config
        side = str(rule.get("side", BOTH_SIDE))
        amount = float(rule.get("amount", default_cfg.get("amount", 10.0)))
        round_size = bool(rule.get("round_size", default_cfg.get("round_size", False)))
        order_type = str(rule.get("order_type", default_cfg.get("order_type", "GTC")))
        private_key = config.private_key
        proxy_address = config.proxy_address

        outcomes = self.market_state.resolve_outcomes(side)
        orders: list[dict[str, Any]] = []
        error_messages: list[str] = []

        try:
            if amount <= 0:
                return {
                    "success": False,
                    "orders": [],
                    "error": "amount 必须大于 0",
                    "source": "task_auto_buy",
                    "strategy_id": strategy_id,
                }
            if not private_key:
                return {
                    "success": False,
                    "orders": [],
                    "error": "private_key 不能为空",
                    "source": "task_auto_buy",
                    "strategy_id": strategy_id,
                }

            for outcome in outcomes:
                token_id = self.market_state.token_by_outcome.get(outcome)
                if not token_id:
                    continue

                best_ask = self.market_state.best_ask_by_token.get(token_id)
                if best_ask is None or best_ask <= 0 or best_ask >= 1:
                    continue

                size = calculate_size(amount, best_ask, round_size)
                if size <= 0:
                    continue

                order_info = {
                    "token_id": token_id,
                    "side": "BUY",
                    "price": best_ask,
                    "size": size,
                    "order_type": order_type,
                    "outcome": outcome,
                }

                request = OrderRequest(
                    token_id=token_id,
                    side="BUY",
                    price=best_ask,
                    size=size,
                    order_type=order_type,
                    private_key=private_key,
                    proxy_address=proxy_address,
                )
                result = await OrderExecutor.execute(request)
                if result.success:
                    orders.append({**order_info, "status": "SUBMITTED", "result": result.result})
                    logger.info(
                        "自动买入成功 task={} strategy={} outcome={} price={} size={}",
                        self.task_id, strategy_id, outcome, best_ask, size,
                    )
                    self._record_stat(outcome, amount)
                else:
                    message = result.error or "下单失败"
                    logger.error("自动买入失败 task={} strategy={} outcome={}: {}", self.task_id, strategy_id, outcome, message)
                    error_messages.append(message)
                    orders.append({**order_info, "status": "FAILED", "error": message})

            success = bool(orders) and all(order.get("status") != "FAILED" for order in orders)
            if success:
                self._last_order_time = now_iso()

            return {
                "success": success,
                "orders": orders,
                "error": "; ".join(error_messages) if error_messages else None,
                "source": "task_auto_buy",
                "strategy_id": strategy_id,
            }
        finally:
            self._is_ordering = False
            await self.publish_state()

    def _record_stat(self, outcome: str, amount: float) -> None:
        if outcome not in self._stats:
            self._stats[outcome] = {"count": 0, "amount": 0.0}
        self._stats[outcome]["count"] += 1
        self._stats[outcome]["amount"] += amount

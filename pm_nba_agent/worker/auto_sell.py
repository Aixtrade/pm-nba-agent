"""AutoSell 处理器"""

import asyncio
import copy
from typing import Any, Callable, Optional

from loguru import logger

from .event_bus import EventPublisher
from .market_state import MarketState
from .order_executor import OrderExecutor, OrderRequest
from .position_manager import PositionManager
from .sse_utils import calculate_profit_rate, now_iso, seconds_since_iso


class AutoSellHandler:
    """AutoSell 处理器：根据持仓盈利率自动卖出。"""

    def __init__(
        self,
        task_id: str,
        config_provider: Callable[[], Any],
        market_state: MarketState,
        position_manager: PositionManager,
        publisher: EventPublisher,
    ) -> None:
        self.task_id = task_id
        self._config_provider = config_provider
        self.market_state = market_state
        self.position_manager = position_manager
        self.publisher = publisher

        self._is_ordering = False
        self._last_order_time: Optional[str] = None
        self._stats: dict[str, dict[str, Any]] = {}
        self._last_sell_time: dict[str, str] = {}

    @property
    def _config(self) -> Any:
        return self._config_provider()

    def _get_auto_sell_config(self) -> dict[str, Any]:
        config = self._config
        auto_sell = config.auto_sell if isinstance(config.auto_sell, dict) else {}
        return copy.deepcopy(auto_sell)

    async def publish_state(self) -> None:
        cfg = self._get_auto_sell_config()
        payload = {
            "enabled": bool(cfg.get("enabled", False)),
            "is_ordering": self._is_ordering,
            "last_order_time": self._last_order_time,
            "last_sell_time": self._last_sell_time,
            "stats": self._stats,
            "default": cfg.get("default", {}),
            "outcome_rules": cfg.get("outcome_rules", {}),
            "timestamp": now_iso(),
        }
        await self.publisher.publish("auto_sell_state", payload)

    async def maybe_execute(self) -> None:
        cfg = self._get_auto_sell_config()
        if not cfg.get("enabled", False):
            return
        if self._is_ordering:
            return
        config = self._config
        if not config.private_key or not config.proxy_address:
            return

        default_cfg = cfg.get("default", {}) if isinstance(cfg.get("default"), dict) else {}
        max_stale_seconds = float(default_cfg.get("max_stale_seconds", 7.0))
        if self.position_manager.updated_at is None or self.position_manager.is_stale(max_stale_seconds):
            await self.position_manager.refresh_once()
            if self.position_manager.updated_at is None or self.position_manager.is_stale(max_stale_seconds):
                return

        outcome_rules = cfg.get("outcome_rules", {}) if isinstance(cfg.get("outcome_rules"), dict) else {}
        candidates: list[dict[str, Any]] = []
        for side in self.position_manager.sides:
            outcome = str(side.get("outcome") or "").strip()
            if not outcome:
                continue

            rule = outcome_rules.get(outcome, {})
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue

            size = float(side.get("size", 0) or 0)
            avg_price = side.get("avg_price")
            avg = float(avg_price) if avg_price is not None else 0.0
            if size <= 0 or avg <= 0:
                continue

            token_id = self.market_state.token_by_outcome.get(outcome)
            if not token_id:
                continue
            best_bid = self.market_state.best_bid_by_token.get(token_id)
            if best_bid is None or best_bid <= 0 or best_bid >= 1:
                continue

            profit_rate = calculate_profit_rate(avg, best_bid)
            min_profit_rate = float(rule.get("min_profit_rate", default_cfg.get("min_profit_rate", 5.0)))
            if profit_rate < (min_profit_rate / 100.0):
                continue

            cooldown_time = float(rule.get("cooldown_time", default_cfg.get("cooldown_time", 30.0)))
            last_sell_iso = self._last_sell_time.get(outcome)
            if last_sell_iso and seconds_since_iso(last_sell_iso) < cooldown_time:
                continue

            sell_ratio = float(rule.get("sell_ratio", default_cfg.get("sell_ratio", 100.0)))
            sell_size = float(int(size * (sell_ratio / 100.0) * 100) / 100.0)
            if sell_size <= 0:
                continue

            order_type = str(rule.get("order_type", default_cfg.get("order_type", "GTC")))
            candidates.append({
                "outcome": outcome,
                "token_id": token_id,
                "price": best_bid,
                "size": sell_size,
                "order_type": order_type,
                "profit_rate": profit_rate,
            })

        if not candidates:
            return

        self._is_ordering = True
        await self.publish_state()

        success_count = 0
        orders: list[dict[str, Any]] = []
        error_messages: list[str] = []
        try:
            for order in candidates:
                outcome = order["outcome"]
                now = now_iso()
                previous = self._last_sell_time.get(outcome)
                self._last_sell_time[outcome] = now

                request = OrderRequest(
                    token_id=order["token_id"],
                    side="SELL",
                    price=float(order["price"]),
                    size=float(order["size"]),
                    order_type=str(order["order_type"]),
                    private_key=config.private_key,
                    proxy_address=config.proxy_address,
                )
                result = await OrderExecutor.execute(request)
                if result.success:
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "SUBMITTED",
                    })
                    logger.info(
                        "自动卖出成功 task={} outcome={} price={} size={} profit_rate={:.2%}",
                        self.task_id, outcome, order["price"], order["size"], order["profit_rate"],
                    )
                    self._record_stat(outcome, float(order["size"]) * float(order["price"]))
                    success_count += 1
                else:
                    message = result.error or "下单失败"
                    logger.error("自动卖出失败 task={} outcome={}: {}", self.task_id, outcome, message)
                    error_messages.append(message)
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "FAILED",
                        "error": message,
                    })
                    if previous:
                        self._last_sell_time[outcome] = previous
                    else:
                        self._last_sell_time.pop(outcome, None)

            success = success_count > 0 and all(item.get("status") != "FAILED" for item in orders)
            await self._publish_execution(
                success=success,
                orders=orders,
                error="; ".join(error_messages) if error_messages else None,
            )
            if success_count > 0:
                self._last_order_time = now_iso()
                await asyncio.sleep(2.0)
                await self.position_manager.refresh_once()
        finally:
            self._is_ordering = False
            await self.publish_state()

    def _record_stat(self, outcome: str, amount: float) -> None:
        if outcome not in self._stats:
            self._stats[outcome] = {"count": 0, "amount": 0.0}
        self._stats[outcome]["count"] += 1
        self._stats[outcome]["amount"] += amount

    async def _publish_execution(
        self,
        success: bool,
        orders: list[dict[str, Any]],
        error: Optional[str] = None,
    ) -> None:
        payload = {
            "success": success,
            "orders": orders,
            "error": error,
            "source": "task_auto_sell",
            "timestamp": now_iso(),
        }
        await self.publisher.publish("auto_sell_execution", payload)

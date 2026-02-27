"""ProfitSellBot — 持仓达到利润率时卖出。"""

from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.shared.channels import SignalType, StreamName
from pm_nba_agent.worker.execution_dedupe import ExecutionDedupe

from .base import BaseRobot, Signal, _now_iso
from .composer import register_robot
from .signal_buy_bot import _extract_best_ask


@register_robot("profit_sell")
class ProfitSellBot(BaseRobot):
    """持仓利润率达标时自动卖出。

    接收信号：polymarket_book（价格更新）, position_state（持仓更新）, polymarket_info（token 映射）
    发出信号：trade_execution
    """

    input_streams = [StreamName.BOOK, StreamName.POSITION]
    output_streams = [StreamName.TRADE]

    @property
    def robot_type(self) -> str:
        return "profit_sell"

    async def setup(self) -> None:
        self._dedupe = ExecutionDedupe(self.redis, self.task_id, ttl_seconds=10)
        self._token_by_outcome: dict[str, str] = {}
        self._best_bid_by_token: dict[str, float] = {}
        self._position_sides: list[dict[str, Any]] = []
        self._private_key = self.config.get("private_key") or ""
        self._proxy_address = self.config.get("proxy_address") or ""
        self._is_ordering = False
        self._last_sell_time: dict[str, float] = {}  # outcome -> timestamp

        # 从 auto_sell 配置读取参数
        auto_sell = self.config.get("auto_sell", {})
        if not isinstance(auto_sell, dict):
            auto_sell = {}
        self._auto_sell_config = auto_sell

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._update_token_mapping(info)

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            self._update_best_bids(signal.data)
            await self._check_profit_sell()
        elif signal.type == SignalType.POSITION_STATE:
            self._update_positions(signal.data)

    def _update_token_mapping(self, data: dict[str, Any]) -> None:
        tokens = data.get("tokens", [])
        for token in tokens:
            if not isinstance(token, dict):
                continue
            outcome = str(token.get("outcome", "")).strip()
            token_id = str(token.get("token_id", "")).strip()
            if outcome and token_id:
                self._token_by_outcome[outcome] = token_id

    def _update_best_bids(self, data: dict[str, Any]) -> None:
        price_changes = data.get("price_changes")
        if isinstance(price_changes, list):
            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                asset_id = change.get("asset_id", "")
                best_bid = change.get("best_bid")
                if asset_id and best_bid is not None:
                    try:
                        val = float(best_bid)
                        if 0 < val < 1:
                            self._best_bid_by_token[asset_id] = val
                    except (TypeError, ValueError):
                        pass
            return

        asset_id = data.get("asset_id") or data.get("assetId") or data.get("token_id") or ""
        bids = data.get("bids") or data.get("buys") or []
        if asset_id and isinstance(bids, list) and bids:
            best_bid = _extract_best_bid(bids)
            if best_bid is not None:
                self._best_bid_by_token[asset_id] = best_bid

    def _update_positions(self, data: dict[str, Any]) -> None:
        sides = data.get("sides", [])
        if isinstance(sides, list):
            self._position_sides = sides

    async def _check_profit_sell(self) -> None:
        if self._is_ordering or not self._private_key:
            return
        if not self._auto_sell_config.get("enabled", False):
            return

        default_cfg = self._auto_sell_config.get("default", {})
        if not isinstance(default_cfg, dict):
            default_cfg = {}
        outcome_rules = self._auto_sell_config.get("outcome_rules", {})
        if not isinstance(outcome_rules, dict):
            outcome_rules = {}

        now = time.time()
        candidates: list[dict[str, Any]] = []

        for side in self._position_sides:
            if not isinstance(side, dict):
                continue
            outcome = str(side.get("outcome", "")).strip()
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

            token_id = self._token_by_outcome.get(outcome)
            if not token_id:
                continue
            best_bid = self._best_bid_by_token.get(token_id)
            if best_bid is None or best_bid <= 0 or best_bid >= 1:
                continue

            # 利润率检查
            profit_rate = (best_bid - avg) / avg if avg > 0 else -1.0
            min_profit_rate = float(
                rule.get("min_profit_rate", default_cfg.get("min_profit_rate", 5.0))
            )
            if profit_rate < (min_profit_rate / 100.0):
                continue

            # 冷却检查
            cooldown = float(rule.get("cooldown_time", default_cfg.get("cooldown_time", 30.0)))
            last_sell = self._last_sell_time.get(outcome, 0.0)
            if cooldown > 0 and now - last_sell < cooldown:
                continue

            # 卖出比例
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
        orders: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            for order in candidates:
                outcome = order["outcome"]

                # 去重
                dedupe_key = self._dedupe.key_for("profit_sell", {
                    "outcome": outcome,
                    "price": round(order["price"], 3),
                })
                if not await self._dedupe.acquire(dedupe_key):
                    continue

                try:
                    result = await create_polymarket_order(
                        token_id=order["token_id"],
                        side="SELL",
                        price=float(order["price"]),
                        size=float(order["size"]),
                        order_type=order["order_type"],
                        private_key=self._private_key,
                        proxy_address=self._proxy_address,
                    )
                    self._last_sell_time[outcome] = now
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "SUBMITTED",
                        "result": result,
                    })
                    logger.info(
                        "ProfitSellBot 卖出: outcome={} price={} size={} profit_rate={:.2%}",
                        outcome, order["price"], order["size"], order["profit_rate"],
                    )
                except Exception as exc:
                    msg = str(exc)
                    errors.append(msg)
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "FAILED",
                        "error": msg,
                    })
                    logger.error("ProfitSellBot 卖出失败: {}", exc)

            if orders:
                success = all(o.get("status") != "FAILED" for o in orders)
                await self.emit(StreamName.TRADE, SignalType.TRADE_EXECUTION, {
                    "success": success,
                    "orders": orders,
                    "error": "; ".join(errors) if errors else None,
                    "source": "profit_sell_bot",
                    "timestamp": _now_iso(),
                })
        finally:
            self._is_ordering = False


def _extract_best_bid(bids: list[Any]) -> Optional[float]:
    values: list[float] = []
    for bid in bids:
        price = None
        if isinstance(bid, dict):
            raw = bid.get("price")
            if raw is not None:
                try:
                    price = float(raw)
                except (TypeError, ValueError):
                    pass
        elif isinstance(bid, (list, tuple)) and len(bid) >= 1:
            try:
                price = float(bid[0])
            except (TypeError, ValueError):
                pass
        if price is not None and 0 < price < 1:
            values.append(price)
    return max(values) if values else None

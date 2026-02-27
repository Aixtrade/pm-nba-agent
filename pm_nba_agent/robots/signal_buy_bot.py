"""SignalBuyBot — 收到策略 BUY 信号时下单。"""

from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.shared.channels import SignalType, StreamName
from pm_nba_agent.worker.execution_dedupe import ExecutionDedupe

from .base import BaseRobot, Signal, _now_iso
from .composer import register_robot


BOTH_SIDE = "__BOTH__"


@register_robot("signal_buy")
class SignalBuyBot(BaseRobot):
    """收到策略 BUY 信号时按配置下单。

    接收信号：strategy_signal（从策略 Bot）, polymarket_info（获取 token 映射）, polymarket_book（更新价格）
    发出信号：trade_execution
    """

    input_streams = [StreamName.STRATEGY, StreamName.BOOK]
    output_streams = [StreamName.TRADE]

    @property
    def robot_type(self) -> str:
        return "signal_buy"

    async def setup(self) -> None:
        self._dedupe = ExecutionDedupe(self.redis, self.task_id, ttl_seconds=5)
        self._is_ordering = False
        self._token_by_outcome: dict[str, str] = {}
        self._best_ask_by_token: dict[str, float] = {}
        self._private_key = self.config.get("private_key") or ""
        self._proxy_address = self.config.get("proxy_address") or ""

        # 从 auto_trade rules 提取 signal_buy 规则
        self._rules = self._extract_rules()

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._update_token_mapping(info)

    def _extract_rules(self) -> list[dict[str, Any]]:
        """从配置提取 signal_buy 规则。"""
        auto_trade = self.config.get("auto_trade", {})
        if not isinstance(auto_trade, dict) or not auto_trade.get("enabled", False):
            # 回退到 legacy auto_buy
            return self._extract_legacy_rules()

        rules = auto_trade.get("rules", [])
        if not isinstance(rules, list):
            return []

        return [
            r for r in rules
            if isinstance(r, dict) and r.get("type") == "signal_buy" and r.get("enabled", True)
        ]

    def _extract_legacy_rules(self) -> list[dict[str, Any]]:
        """从 legacy auto_buy 提取规则。"""
        auto_buy = self.config.get("auto_buy", {})
        if not isinstance(auto_buy, dict) or not auto_buy.get("enabled", False):
            return []

        default_cfg = auto_buy.get("default", {})
        strategy_rules = auto_buy.get("strategy_rules", {})
        rules = []
        for strategy_id, rule in strategy_rules.items():
            if not isinstance(rule, dict) or not rule.get("enabled", True):
                continue
            rules.append({
                "id": f"legacy_signal_buy_{strategy_id}",
                "type": "signal_buy",
                "enabled": True,
                "scope": {
                    "strategy_id": strategy_id,
                    "outcome": str(rule.get("side", BOTH_SIDE)),
                },
                "config": {
                    "signal_types": rule.get("signal_types", ["BUY"]),
                    "amount": float(rule.get("amount", default_cfg.get("amount", 10.0))),
                    "round_size": bool(rule.get("round_size", default_cfg.get("round_size", False))),
                    "order_type": str(rule.get("order_type", default_cfg.get("order_type", "GTC"))),
                },
            })
        return rules

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            self._update_best_prices(signal.data)
        elif signal.type == SignalType.STRATEGY_SIGNAL:
            await self._handle_strategy_signal(signal.data)

    def _update_token_mapping(self, data: dict[str, Any]) -> None:
        tokens = data.get("tokens", [])
        for token in tokens:
            if not isinstance(token, dict):
                continue
            outcome = str(token.get("outcome", "")).strip()
            token_id = str(token.get("token_id", "")).strip()
            if outcome and token_id:
                self._token_by_outcome[outcome] = token_id

    def _update_best_prices(self, data: dict[str, Any]) -> None:
        price_changes = data.get("price_changes")
        if isinstance(price_changes, list):
            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                asset_id = change.get("asset_id", "")
                best_ask = change.get("best_ask")
                if asset_id and best_ask is not None:
                    try:
                        val = float(best_ask)
                        if 0 < val < 1:
                            self._best_ask_by_token[asset_id] = val
                    except (TypeError, ValueError):
                        pass
            return

        asset_id = data.get("asset_id") or data.get("assetId") or data.get("token_id") or ""
        asks = data.get("asks") or data.get("sells") or []
        if asset_id and isinstance(asks, list) and asks:
            best_ask = _extract_best_ask(asks)
            if best_ask is not None:
                self._best_ask_by_token[asset_id] = best_ask

    async def _handle_strategy_signal(self, payload: dict[str, Any]) -> None:
        signal_data = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
        strategy_data = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        signal_type = str(signal_data.get("type", "")).upper()
        strategy_id = str(strategy_data.get("id", "")).strip()

        if not signal_type or not strategy_id:
            return

        for rule in self._rules:
            scope = rule.get("scope", {}) if isinstance(rule.get("scope"), dict) else {}
            target_strategy = str(scope.get("strategy_id", "")).strip()
            target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE

            cfg = rule.get("config", {}) if isinstance(rule.get("config"), dict) else {}
            allowed_types = {str(t).upper() for t in (cfg.get("signal_types") or ["BUY"])}

            if allowed_types and signal_type not in allowed_types:
                continue
            if target_strategy and strategy_id != target_strategy:
                continue

            amount = float(cfg.get("amount", 10.0))
            round_size = bool(cfg.get("round_size", False))
            order_type = str(cfg.get("order_type", "GTC"))
            rule_id = str(rule.get("id", "signal_buy"))

            outcomes = self._resolve_outcomes(target_outcome)
            await self._execute_orders(
                rule_id, outcomes, amount, round_size, order_type, strategy_id,
            )

    def _resolve_outcomes(self, side: str) -> list[str]:
        if side == BOTH_SIDE:
            return list(self._token_by_outcome.keys())
        if side in self._token_by_outcome:
            return [side]
        return []

    async def _execute_orders(
        self,
        rule_id: str,
        outcomes: list[str],
        amount: float,
        round_size: bool,
        order_type: str,
        strategy_id: str,
    ) -> None:
        if self._is_ordering or not self._private_key:
            return
        if amount <= 0:
            return

        self._is_ordering = True
        orders: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            for outcome in outcomes:
                token_id = self._token_by_outcome.get(outcome)
                if not token_id:
                    continue
                best_ask = self._best_ask_by_token.get(token_id)
                if best_ask is None or best_ask <= 0 or best_ask >= 1:
                    continue

                size = _calculate_size(amount, best_ask, round_size)
                if size <= 0:
                    continue

                # 去重
                dedupe_payload = {
                    "rule_id": rule_id,
                    "token_id": token_id,
                    "side": "BUY",
                    "price": round(best_ask, 3),
                }
                dedupe_key = self._dedupe.key_for("signal_buy", dedupe_payload)
                if not await self._dedupe.acquire(dedupe_key):
                    continue

                order_info = {
                    "token_id": token_id,
                    "side": "BUY",
                    "price": best_ask,
                    "size": size,
                    "order_type": order_type,
                    "outcome": outcome,
                    "rule_id": rule_id,
                }

                try:
                    result = await create_polymarket_order(
                        token_id=token_id,
                        side="BUY",
                        price=best_ask,
                        size=size,
                        order_type=order_type,
                        private_key=self._private_key,
                        proxy_address=self._proxy_address,
                    )
                    orders.append({**order_info, "status": "SUBMITTED", "result": result})
                    logger.info(
                        "SignalBuyBot 下单成功: outcome={} price={} size={}",
                        outcome, best_ask, size,
                    )
                except Exception as exc:
                    msg = str(exc)
                    errors.append(msg)
                    orders.append({**order_info, "status": "FAILED", "error": msg})
                    logger.error("SignalBuyBot 下单失败: outcome={} err={}", outcome, exc)

            if orders:
                success = all(o.get("status") != "FAILED" for o in orders)
                await self.emit(StreamName.TRADE, SignalType.TRADE_EXECUTION, {
                    "success": success,
                    "orders": orders,
                    "error": "; ".join(errors) if errors else None,
                    "source": "signal_buy_bot",
                    "strategy_id": strategy_id,
                    "timestamp": _now_iso(),
                })
        finally:
            self._is_ordering = False


def _calculate_size(amount: float, price: float, round_size: bool) -> float:
    if price <= 0 or price >= 1:
        return 0.0
    raw_size = amount / price
    if round_size:
        return float(int(raw_size))
    return float(int(raw_size * 100) / 100)


def _extract_best_ask(asks: list[Any]) -> Optional[float]:
    values: list[float] = []
    for ask in asks:
        price = None
        if isinstance(ask, dict):
            raw = ask.get("price")
            if raw is not None:
                try:
                    price = float(raw)
                except (TypeError, ValueError):
                    pass
        elif isinstance(ask, (list, tuple)) and len(ask) >= 1:
            try:
                price = float(ask[0])
            except (TypeError, ValueError):
                pass
        if price is not None and 0 < price < 1:
            values.append(price)
    return min(values) if values else None

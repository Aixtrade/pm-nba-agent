"""ConditionBuyBot — 价格满足条件时下单。"""

from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.shared.channels import SignalType, StreamName
from pm_nba_agent.worker.execution_dedupe import ExecutionDedupe

from .base import BaseRobot, Signal, _now_iso
from .composer import register_robot
from .signal_buy_bot import BOTH_SIDE, _extract_best_ask


@register_robot("condition_buy")
class ConditionBuyBot(BaseRobot):
    """价格 <= 阈值时买入。

    接收信号：polymarket_book, polymarket_info
    发出信号：trade_execution
    """

    input_streams = [StreamName.BOOK]
    output_streams = [StreamName.TRADE]

    @property
    def robot_type(self) -> str:
        return "condition_buy"

    async def setup(self) -> None:
        self._dedupe = ExecutionDedupe(self.redis, self.task_id, ttl_seconds=10)
        self._token_by_outcome: dict[str, str] = {}
        self._best_ask_by_token: dict[str, float] = {}
        self._private_key = self.config.get("private_key") or ""
        self._proxy_address = self.config.get("proxy_address") or ""
        self._last_order_at: dict[str, float] = {}  # rule_id -> timestamp

        # 提取 condition_buy 规则
        self._rules = self._extract_rules()

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._update_token_mapping(info)

    def _extract_rules(self) -> list[dict[str, Any]]:
        auto_trade = self.config.get("auto_trade", {})
        if not isinstance(auto_trade, dict) or not auto_trade.get("enabled", False):
            return []
        rules = auto_trade.get("rules", [])
        if not isinstance(rules, list):
            return []
        return [
            r for r in rules
            if isinstance(r, dict) and r.get("type") == "condition_buy" and r.get("enabled", True)
        ]

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            self._update_best_prices(signal.data)
            await self._check_conditions()

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

    async def _check_conditions(self) -> None:
        if not self._private_key:
            return

        now = time.time()
        for rule in self._rules:
            rule_id = str(rule.get("id", "condition_buy"))
            cooldown = float(rule.get("cooldown_seconds", 0.0))
            if cooldown > 0:
                last = self._last_order_at.get(rule_id, 0.0)
                if now - last < cooldown:
                    continue

            scope = rule.get("scope", {}) if isinstance(rule.get("scope"), dict) else {}
            target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE
            outcomes = self._resolve_outcomes(target_outcome)

            cfg = rule.get("config", {}) if isinstance(rule.get("config"), dict) else {}
            trigger = float(cfg.get("trigger_price_lte", 0.45))
            budget = float(cfg.get("budget_usdc", 10.0))
            order_type = str(cfg.get("order_type", "GTC"))

            for outcome in outcomes:
                token_id = self._token_by_outcome.get(outcome)
                if not token_id:
                    continue
                ask = self._best_ask_by_token.get(token_id)
                if ask is None or ask > trigger:
                    continue

                size = float(int((budget / ask) * 100) / 100)
                if size <= 0:
                    continue

                # 去重
                dedupe_key = self._dedupe.key_for("condition_buy", {
                    "rule_id": rule_id,
                    "token_id": token_id,
                    "price": round(ask, 3),
                })
                if not await self._dedupe.acquire(dedupe_key):
                    continue

                try:
                    result = await create_polymarket_order(
                        token_id=token_id,
                        side="BUY",
                        price=ask,
                        size=size,
                        order_type=order_type,
                        private_key=self._private_key,
                        proxy_address=self._proxy_address,
                    )
                    self._last_order_at[rule_id] = now
                    await self.emit(StreamName.TRADE, SignalType.TRADE_EXECUTION, {
                        "success": True,
                        "orders": [{
                            "rule_id": rule_id,
                            "rule_type": "condition_buy",
                            "token_id": token_id,
                            "side": "BUY",
                            "price": ask,
                            "size": size,
                            "outcome": outcome,
                            "status": "SUBMITTED",
                            "result": result,
                        }],
                        "error": None,
                        "source": "condition_buy_bot",
                        "timestamp": _now_iso(),
                    })
                    logger.info(
                        "ConditionBuyBot 下单: outcome={} price={} <= trigger={} size={}",
                        outcome, ask, trigger, size,
                    )
                    break  # 每个规则每次只触发一个 outcome
                except Exception as exc:
                    logger.error("ConditionBuyBot 下单失败: {}", exc)
                    await self.emit(StreamName.TRADE, SignalType.TRADE_EXECUTION, {
                        "success": False,
                        "orders": [{
                            "rule_id": rule_id,
                            "rule_type": "condition_buy",
                            "token_id": token_id,
                            "side": "BUY",
                            "price": ask,
                            "size": size,
                            "outcome": outcome,
                            "status": "FAILED",
                            "error": str(exc),
                        }],
                        "error": str(exc),
                        "source": "condition_buy_bot",
                        "timestamp": _now_iso(),
                    })

    def _resolve_outcomes(self, side: str) -> list[str]:
        if side == BOTH_SIDE:
            return list(self._token_by_outcome.keys())
        if side in self._token_by_outcome:
            return [side]
        return []

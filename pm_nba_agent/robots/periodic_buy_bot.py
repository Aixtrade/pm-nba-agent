"""PeriodicBuyBot — 定时定额买入（DCA）。"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.shared.channels import SignalType, StreamName
from pm_nba_agent.worker.execution_dedupe import ExecutionDedupe

from .base import BaseRobot, Signal, _now_iso
from .composer import register_robot
from .signal_buy_bot import BOTH_SIDE, _extract_best_ask


@register_robot("periodic_buy")
class PeriodicBuyBot(BaseRobot):
    """每 N 秒定额买入。

    接收信号：polymarket_info（获取 token 映射）, polymarket_book（更新价格）
    发出信号：trade_execution

    自驱动定时器模式：在 setup() 中启动定时任务。
    同时也监听 book stream 来更新价格。
    """

    input_streams = [StreamName.BOOK]
    output_streams = [StreamName.TRADE]

    @property
    def robot_type(self) -> str:
        return "periodic_buy"

    async def setup(self) -> None:
        self._dedupe = ExecutionDedupe(self.redis, self.task_id, ttl_seconds=10)
        self._token_by_outcome: dict[str, str] = {}
        self._best_ask_by_token: dict[str, float] = {}
        self._private_key = self.config.get("private_key") or ""
        self._proxy_address = self.config.get("proxy_address") or ""
        self._total_spent: dict[str, float] = {}  # rule_id -> total spent

        self._rules = self._extract_rules()

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._update_token_mapping(info)

        self._timer_task: Optional[asyncio.Task] = None
        if self._rules:
            self._timer_task = asyncio.create_task(self._timer_loop())

    def _extract_rules(self) -> list[dict[str, Any]]:
        auto_trade = self.config.get("auto_trade", {})
        if not isinstance(auto_trade, dict) or not auto_trade.get("enabled", False):
            return []
        rules = auto_trade.get("rules", [])
        if not isinstance(rules, list):
            return []
        return [
            r for r in rules
            if isinstance(r, dict) and r.get("type") == "periodic_buy" and r.get("enabled", True)
        ]

    async def teardown(self) -> None:
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            self._update_best_prices(signal.data)

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

    async def _timer_loop(self) -> None:
        """定时器主循环。"""
        try:
            while not self._cancelled:
                await asyncio.sleep(1.0)
                if self._cancelled:
                    break
                await self._tick()
        except asyncio.CancelledError:
            pass

    async def _tick(self) -> None:
        if not self._private_key or not self._token_by_outcome:
            return

        now = time.time()
        for rule in self._rules:
            rule_id = str(rule.get("id", "periodic_buy"))
            scope = rule.get("scope", {}) if isinstance(rule.get("scope"), dict) else {}
            target_outcome = str(scope.get("outcome", BOTH_SIDE)).strip() or BOTH_SIDE

            cfg = rule.get("config", {}) if isinstance(rule.get("config"), dict) else {}
            interval = max(5, int(cfg.get("interval_seconds", 120)))
            budget = float(cfg.get("budget_usdc", 10.0))
            max_total = max(0.0, float(cfg.get("max_total_budget", 0.0)))
            order_type = str(cfg.get("order_type", "GTC"))

            # 通过去重器实现间隔控制
            time_bucket = int(now // interval)
            dedupe_key = self._dedupe.key_for("periodic_buy", {
                "rule_id": rule_id,
                "bucket": time_bucket,
            })
            if not await self._dedupe.acquire(dedupe_key):
                continue

            # 预算检查
            spent = self._total_spent.get(rule_id, 0.0)
            if max_total > 0 and spent >= max_total:
                continue

            effective_budget = budget
            if max_total > 0:
                effective_budget = min(effective_budget, max_total - spent)
            if effective_budget <= 0:
                continue

            outcomes = self._resolve_outcomes(target_outcome)
            for outcome in outcomes:
                token_id = self._token_by_outcome.get(outcome)
                if not token_id:
                    continue
                ask = self._best_ask_by_token.get(token_id)
                if ask is None or ask <= 0 or ask >= 1:
                    continue

                size = float(int((effective_budget / ask) * 100) / 100)
                if size <= 0:
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
                    cost = ask * size
                    self._total_spent[rule_id] = spent + cost
                    await self.emit(StreamName.TRADE, SignalType.TRADE_EXECUTION, {
                        "success": True,
                        "orders": [{
                            "rule_id": rule_id,
                            "rule_type": "periodic_buy",
                            "token_id": token_id,
                            "side": "BUY",
                            "price": ask,
                            "size": size,
                            "outcome": outcome,
                            "status": "SUBMITTED",
                            "result": result,
                        }],
                        "error": None,
                        "source": "periodic_buy_bot",
                        "timestamp": _now_iso(),
                    })
                    logger.info(
                        "PeriodicBuyBot 定时买入: outcome={} price={} size={} total_spent={:.2f}",
                        outcome, ask, size, self._total_spent[rule_id],
                    )
                    break  # 每个规则每次只触发一个 outcome
                except Exception as exc:
                    logger.error("PeriodicBuyBot 下单失败: {}", exc)

    def _resolve_outcomes(self, side: str) -> list[str]:
        if side == BOTH_SIDE:
            return list(self._token_by_outcome.keys())
        if side in self._token_by_outcome:
            return [side]
        return []

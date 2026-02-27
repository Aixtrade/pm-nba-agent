"""PositionBot — 定期刷新 Polymarket 持仓。"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.positions import get_current_positions
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot, _now_iso
from .composer import register_robot


@register_robot("position")
class PositionBot(BaseRobot):
    """定期查询 Polymarket 持仓并发出 position_state 信号。

    接收信号：polymarket_info（从 BookBot 获取 condition_id 和 outcomes）
    发出信号：position_state
    """

    input_streams = []
    output_streams = [StreamName.POSITION]

    @property
    def robot_type(self) -> str:
        return "position"

    async def setup(self) -> None:
        self._condition_id: str | None = None
        self._outcomes: list[str] = []
        self._proxy_address = self.config.get("proxy_address") or ""
        self._position_sides: list[dict[str, Any]] = []
        self._positions_loading = False
        self._positions_updated_at: str | None = None
        self._refresh_interval = 3.0

        # 从 auto_sell 配置读取刷新间隔
        auto_sell = self.config.get("auto_sell", {})
        if isinstance(auto_sell, dict):
            default_cfg = auto_sell.get("default", {})
            if isinstance(default_cfg, dict):
                self._refresh_interval = max(
                    1.0,
                    min(60.0, float(default_cfg.get("refresh_interval", 3.0))),
                )

        self._refresh_task: Optional[asyncio.Task] = None
        self._refresh_lock = asyncio.Lock()
        self._last_refresh_at = 0.0
        # 初始发布空状态
        await self._publish_position_state()

        # 从 snapshot 读取 polymarket_info 并初始化
        info = await self.load_snapshot("polymarket_info")
        if info:
            condition_id = info.get("condition_id")
            tokens = info.get("tokens", [])
            if condition_id:
                self._condition_id = condition_id
                self._outcomes = [
                    t.get("outcome", "")
                    for t in tokens
                    if isinstance(t, dict) and t.get("outcome")
                ]
                logger.info(
                    "PositionBot: 从 snapshot 获取 condition_id={}, outcomes={}",
                    self._condition_id,
                    self._outcomes,
                )
                if self._proxy_address:
                    await self._refresh_positions()
                if not self._refresh_task and self._proxy_address:
                    self._refresh_task = asyncio.create_task(self._refresh_loop())

    async def teardown(self) -> None:
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    def get_runtime_metrics(self) -> dict[str, Any]:
        return {
            "condition_id": self._condition_id,
            "proxy_address": bool(self._proxy_address),
            "refresh_interval": self._refresh_interval,
            "positions_count": len(self._position_sides),
        }

    async def _refresh_loop(self) -> None:
        """定期刷新持仓。"""
        try:
            while not self._cancelled:
                await asyncio.sleep(self._refresh_interval)
                if self._cancelled:
                    break
                if self._condition_id and self._proxy_address:
                    await self.refresh_positions_once()
        except asyncio.CancelledError:
            pass

    async def refresh_positions_once(self, force: bool = False) -> None:
        """立即刷新一次持仓。"""
        if not self._condition_id or not self._proxy_address:
            return
        if not force and not self._should_refresh_now():
            return
        if self._refresh_lock.locked():
            return

        async with self._refresh_lock:
            self._last_refresh_at = time.monotonic()
            await self._refresh_positions()

    def _should_refresh_now(self) -> bool:
        min_gap = max(0.8, min(self._refresh_interval * 0.6, 5.0))
        return (time.monotonic() - self._last_refresh_at) >= min_gap

    async def _refresh_positions(self) -> None:
        """查询持仓并发布状态。"""
        if not self._condition_id or not self._proxy_address:
            return

        self._positions_loading = True
        await self._publish_position_state()

        try:
            positions = await get_current_positions(
                user_address=self._proxy_address,
                condition_ids=[self._condition_id],
                proxy_address=self._proxy_address,
            )
            if not isinstance(positions, list):
                return

            self._position_sides = _build_position_sides(positions, self._outcomes)
            self._positions_updated_at = _now_iso()
        except Exception as exc:
            logger.error("PositionBot: 刷新持仓失败: {}", exc)
        finally:
            self._positions_loading = False
            await self._publish_position_state()

    async def _publish_position_state(self) -> None:
        """发布 position_state 信号。"""
        payload = {
            "sides": self._position_sides,
            "loading": self._positions_loading,
            "updated_at": self._positions_updated_at,
            "condition_id": self._condition_id,
            "timestamp": _now_iso(),
        }
        await self.emit(StreamName.POSITION, SignalType.POSITION_STATE, payload)


def _build_position_sides(
    positions: list[dict[str, Any]],
    outcomes: list[str] | None,
) -> list[dict[str, Any]]:
    """从 API 持仓数据构建 position_sides 列表。"""
    sizes: dict[str, float] = {}
    initial_values: dict[str, float] = {}
    avg_prices: dict[str, float | None] = {}
    cur_prices: dict[str, float | None] = {}

    for position in positions:
        outcome = str(position.get("outcome") or "").strip()
        if outcome:
            try:
                size = float(position.get("size", 0))
            except (TypeError, ValueError):
                size = 0.0
            sizes[outcome] = sizes.get(outcome, 0.0) + size

            try:
                cost = float(position.get("initialValue", 0))
            except (TypeError, ValueError):
                cost = 0.0
            initial_values[outcome] = initial_values.get(outcome, 0.0) + cost

            if outcome not in avg_prices:
                avg_value = position.get("avgPrice")
                if avg_value is not None:
                    try:
                        avg_prices[outcome] = float(avg_value)
                    except (TypeError, ValueError):
                        avg_prices[outcome] = None

            if outcome not in cur_prices:
                cur_value = position.get("curPrice")
                if cur_value is not None:
                    try:
                        cur_prices[outcome] = float(cur_value)
                    except (TypeError, ValueError):
                        cur_prices[outcome] = None

        opposite_outcome = str(position.get("oppositeOutcome") or "").strip()
        if opposite_outcome and opposite_outcome not in sizes:
            sizes[opposite_outcome] = 0.0
            initial_values[opposite_outcome] = 0.0

    if outcomes:
        for outcome in outcomes:
            if outcome not in sizes:
                sizes[outcome] = 0.0
            if outcome not in initial_values:
                initial_values[outcome] = 0.0

    ordered_outcomes = outcomes or list(sizes.keys())
    return [
        {
            "outcome": outcome,
            "size": sizes.get(outcome, 0.0),
            "initial_value": initial_values.get(outcome, 0.0),
            "avg_price": avg_prices.get(outcome),
            "cur_price": cur_prices.get(outcome),
        }
        for outcome in ordered_outcomes
    ]

"""LockedProfitBot — 持仓对冲保底利润策略。"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.models import (
    MarketSnapshot,
    OrderBookContext,
    OrderLevel,
    PositionContext,
)
from pm_nba_agent.polymarket.strategies.locked_profit_strategy import LockedProfitStrategy
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot, Signal
from .composer import register_robot
from .merge_long_bot import (
    _build_signal_metrics,
    _build_snapshot,
    _update_order_book,
)


@register_robot("locked_profit")
class LockedProfitBot(BaseRobot):
    """收到 polymarket_book 时运行 LockedProfit 策略。

    接收信号：polymarket_book（从 BookBot）, position_state（从 PositionBot）
    发出信号：strategy_signal
    """

    input_streams = [StreamName.BOOK, StreamName.POSITION]
    output_streams = [StreamName.STRATEGY]

    @property
    def robot_type(self) -> str:
        return "locked_profit"

    async def setup(self) -> None:
        self._strategy = LockedProfitStrategy()
        self._params = self.config.get("strategy_params", {})

        # 订单簿状态
        self._yes_token_id = ""
        self._no_token_id = ""
        self._yes_bids: list[OrderLevel] = []
        self._yes_asks: list[OrderLevel] = []
        self._no_bids: list[OrderLevel] = []
        self._no_asks: list[OrderLevel] = []
        self._yes_price = 0.0
        self._no_price = 0.0
        self._condition_id = ""

        # 持仓缓存
        self._position = PositionContext()

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._handle_info(info)

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            await self._handle_book(signal.data)
        elif signal.type == SignalType.POSITION_STATE:
            self._handle_position(signal.data)

    def _handle_info(self, data: dict[str, Any]) -> None:
        """从 polymarket_info 提取 token_id 映射。"""
        tokens = data.get("tokens", [])
        self._condition_id = data.get("condition_id", "")
        for token in tokens:
            if not isinstance(token, dict):
                continue
            outcome = str(token.get("outcome", "")).upper()
            token_id = token.get("token_id", "")
            if outcome in ("YES", "UP"):
                self._yes_token_id = token_id
            elif outcome in ("NO", "DOWN"):
                self._no_token_id = token_id

    def _handle_position(self, data: dict[str, Any]) -> None:
        """从 position_state 更新内部持仓缓存。"""
        sides = data.get("sides", [])
        if not isinstance(sides, list):
            return

        yes_size = 0.0
        no_size = 0.0
        yes_avg_cost = 0.0
        no_avg_cost = 0.0
        yes_initial = 0.0
        no_initial = 0.0

        for side in sides:
            if not isinstance(side, dict):
                continue
            outcome = str(side.get("outcome", "")).upper()
            size = float(side.get("size", 0) or 0)
            avg_price = side.get("avg_price")
            initial_value = float(side.get("initial_value", 0) or 0)

            if outcome in ("YES", "UP"):
                yes_size = size
                yes_initial = initial_value
                if avg_price is not None:
                    try:
                        yes_avg_cost = float(avg_price)
                    except (TypeError, ValueError):
                        pass
            elif outcome in ("NO", "DOWN"):
                no_size = size
                no_initial = initial_value
                if avg_price is not None:
                    try:
                        no_avg_cost = float(avg_price)
                    except (TypeError, ValueError):
                        pass

        self._position = PositionContext(
            yes_size=yes_size,
            no_size=no_size,
            yes_avg_cost=yes_avg_cost,
            no_avg_cost=no_avg_cost,
            yes_total_cost=yes_initial,
            no_total_cost=no_initial,
        )

    async def _handle_book(self, data: dict[str, Any]) -> None:
        """处理订单簿更新，运行策略。"""
        _update_order_book(
            data,
            self._yes_token_id,
            self._no_token_id,
            self._yes_bids,
            self._yes_asks,
            self._no_bids,
            self._no_asks,
            self,
        )

        # 构建快照
        snapshot = _build_snapshot(
            self._yes_token_id, self._no_token_id,
            self._yes_bids, self._yes_asks,
            self._no_bids, self._no_asks,
            self._yes_price, self._no_price,
        )
        if not snapshot:
            return

        order_book = OrderBookContext.from_snapshot(snapshot)

        signal = self._strategy.generate_signal(
            snapshot, order_book, self._position, self._params
        )
        if signal and signal.is_actionable:
            await self._emit_signal(signal, snapshot)

    async def _emit_signal(self, signal, snapshot: MarketSnapshot) -> None:
        """发出策略信号。"""
        market_data = snapshot.to_dict()
        metrics = _build_signal_metrics("locked_profit", signal.metadata)

        payload = {
            "signal": {
                "type": signal.signal_type.value,
                "reason": signal.reason,
                "yes_size": signal.yes_size,
                "no_size": signal.no_size,
                "yes_price": signal.yes_price,
                "no_price": signal.no_price,
                "metadata": signal.metadata or {},
            },
            "market": market_data,
            "position": self._position.to_dict(),
            "execution": None,
            "strategy": {"id": "locked_profit"},
            "metrics": metrics,
        }
        await self.emit(StreamName.STRATEGY, SignalType.STRATEGY_SIGNAL, payload)

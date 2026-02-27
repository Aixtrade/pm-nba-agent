"""MergeLongBot — 合并做多套利检测。"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.models import (
    MarketSnapshot,
    OrderBookContext,
    OrderLevel,
    PositionContext,
    SideData,
)
from pm_nba_agent.polymarket.strategies.merge_long_strategy import MergeLongStrategy
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot, Signal
from .composer import register_robot


@register_robot("merge_long")
class MergeLongBot(BaseRobot):
    """收到 polymarket_book 信号时运行 MergeLong 策略。

    接收信号：polymarket_book（从 BookBot）
    发出信号：strategy_signal
    """

    input_streams = [StreamName.BOOK]
    output_streams = [StreamName.STRATEGY]

    @property
    def robot_type(self) -> str:
        return "merge_long"

    async def setup(self) -> None:
        self._strategy = MergeLongStrategy()
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

        # 从 snapshot 读取 polymarket_info
        info = await self.load_snapshot("polymarket_info")
        if info:
            self._handle_info(info)

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.POLYMARKET_BOOK:
            await self._handle_book(signal.data)

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
        position = PositionContext()  # merge_long 不需要持仓

        signal = self._strategy.generate_signal(snapshot, order_book, position, self._params)
        if signal and signal.is_actionable:
            await self._emit_signal(signal, snapshot, position)

    async def _emit_signal(
        self,
        signal,
        snapshot: MarketSnapshot,
        position: PositionContext,
    ) -> None:
        """发出策略信号。"""
        market_data = snapshot.to_dict()
        metrics = _build_signal_metrics("merge_long", signal.metadata)

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
            "position": position.to_dict(),
            "execution": None,
            "strategy": {"id": "merge_long"},
            "metrics": metrics,
        }
        await self.emit(StreamName.STRATEGY, SignalType.STRATEGY_SIGNAL, payload)


# ========== 共享工具函数 ==========


def _update_order_book(
    data: dict[str, Any],
    yes_token_id: str,
    no_token_id: str,
    yes_bids: list[OrderLevel],
    yes_asks: list[OrderLevel],
    no_bids: list[OrderLevel],
    no_asks: list[OrderLevel],
    bot: BaseRobot,
) -> None:
    """从 polymarket_book 数据更新订单簿。"""
    price_changes = data.get("price_changes")
    if isinstance(price_changes, list) and price_changes:
        for change in price_changes:
            if not isinstance(change, dict):
                continue
            asset_id = change.get("asset_id", "")
            bids = change.get("bids") or change.get("buys") or []
            asks = change.get("asks") or change.get("sells") or []
            _apply_book_update(
                asset_id, bids, asks,
                yes_token_id, no_token_id,
                yes_bids, yes_asks, no_bids, no_asks, bot,
            )
        return

    asset_id = (
        data.get("asset_id") or data.get("assetId") or
        data.get("token_id") or data.get("tokenId") or ""
    )
    bids = data.get("bids") or data.get("buys") or []
    asks = data.get("asks") or data.get("sells") or []
    _apply_book_update(
        asset_id, bids, asks,
        yes_token_id, no_token_id,
        yes_bids, yes_asks, no_bids, no_asks, bot,
    )


def _apply_book_update(
    asset_id: str,
    bids: list,
    asks: list,
    yes_token_id: str,
    no_token_id: str,
    yes_bids: list[OrderLevel],
    yes_asks: list[OrderLevel],
    no_bids: list[OrderLevel],
    no_asks: list[OrderLevel],
    bot: BaseRobot,
) -> None:
    """应用单个 asset 的订单簿更新。"""
    if not asset_id:
        return

    parsed_bids = [OrderLevel.from_raw(b) if isinstance(b, dict) else OrderLevel(price=float(b[0]), size=float(b[1])) for b in bids if b]
    parsed_asks = [OrderLevel.from_raw(a) if isinstance(a, dict) else OrderLevel(price=float(a[0]), size=float(a[1])) for a in asks if a]

    if asset_id == yes_token_id:
        yes_bids.clear()
        yes_bids.extend(parsed_bids)
        yes_asks.clear()
        yes_asks.extend(parsed_asks)
        if parsed_asks:
            bot._yes_price = min(a.price for a in parsed_asks)
    elif asset_id == no_token_id:
        no_bids.clear()
        no_bids.extend(parsed_bids)
        no_asks.clear()
        no_asks.extend(parsed_asks)
        if parsed_asks:
            bot._no_price = min(a.price for a in parsed_asks)


def _build_snapshot(
    yes_token_id: str,
    no_token_id: str,
    yes_bids: list[OrderLevel],
    yes_asks: list[OrderLevel],
    no_bids: list[OrderLevel],
    no_asks: list[OrderLevel],
    yes_price: float,
    no_price: float,
) -> Optional[MarketSnapshot]:
    """构建市场快照。"""
    if not yes_token_id or not no_token_id:
        return None
    if not yes_bids and not yes_asks and not no_bids and not no_asks:
        return None

    return MarketSnapshot(
        yes_data=SideData(
            token_id=yes_token_id,
            price=yes_price,
            bids=list(yes_bids),
            asks=list(yes_asks),
        ),
        no_data=SideData(
            token_id=no_token_id,
            price=no_price,
            bids=list(no_bids),
            asks=list(no_asks),
        ),
    )


def _build_signal_metrics(
    strategy_id: str,
    metadata: Optional[dict[str, Any]],
) -> list[dict[str, Any]]:
    """将策略 metadata 映射为前端展示的通用 metrics。"""
    md = metadata or {}

    provided_metrics = md.get("metrics")
    if isinstance(provided_metrics, list):
        return [m for m in provided_metrics if isinstance(m, dict)]

    metric_specs: list[tuple[str, str, str, int]]
    if strategy_id == "merge_long":
        metric_specs = [
            ("expected_profit_pct", "预期利润", "%", 100),
            ("long_cost", "成本", "", 90),
            ("threshold", "阈值", "", 80),
        ]
    elif strategy_id == "locked_profit":
        metric_specs = [
            ("new_locked_profit", "新锁定利润", "USD", 100),
            ("locked_profit", "当前锁定利润", "USD", 90),
            ("target_profit", "目标利润", "USD", 80),
        ]
    else:
        return []

    metrics: list[dict[str, Any]] = []
    for key, label, unit, priority in metric_specs:
        value = md.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float, str, bool)):
            continue
        metrics.append({
            "key": key,
            "label": label,
            "value": value,
            "unit": unit or None,
            "priority": priority,
        })
    return metrics

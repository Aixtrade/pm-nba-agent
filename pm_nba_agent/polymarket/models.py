"""Polymarket 数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TokenInfo:
    """Token 信息"""

    token_id: str
    outcome: str
    condition_id: str
    market_slug: str

    def to_dict(self) -> dict:
        return {
            "token_id": self.token_id,
            "outcome": self.outcome,
            "condition_id": self.condition_id,
            "market_slug": self.market_slug,
        }


@dataclass
class MarketInfo:
    """市场信息"""

    slug: str
    question: Optional[str]
    description: Optional[str]
    condition_id: Optional[str]
    outcomes: list[str]
    clob_token_ids: list[str]
    market_id: Optional[str]
    raw_data: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "question": self.question,
            "description": self.description,
            "condition_id": self.condition_id,
            "outcomes": self.outcomes,
            "clob_token_ids": self.clob_token_ids,
            "market_id": self.market_id,
            "raw_data": self.raw_data,
        }


@dataclass
class EventInfo:
    """事件信息"""

    event_id: str
    title: str
    interval: str
    asset: str
    tokens: list[TokenInfo]
    condition_id: Optional[str]
    market_info: Optional[MarketInfo]
    event_data: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "interval": self.interval,
            "asset": self.asset,
            "condition_id": self.condition_id,
            "tokens": [token.to_dict() for token in self.tokens],
            "market_info": self.market_info.to_dict() if self.market_info else None,
            "event_data": self.event_data,
        }


# =============================================================================
# 订单簿与持仓上下文
# =============================================================================


@dataclass
class OrderLevel:
    """订单簿单层"""

    price: float
    size: float

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "OrderLevel":
        return cls(
            price=float(raw.get("price", 0)),
            size=float(raw.get("size", 0)),
        )


@dataclass
class SideData:
    """单边（YES/NO）市场数据"""

    token_id: str
    price: float
    bids: list[OrderLevel] = field(default_factory=list)
    asks: list[OrderLevel] = field(default_factory=list)

    @property
    def best_bid(self) -> Optional[float]:
        """最优买价"""
        if not self.bids:
            return None
        return max(level.price for level in self.bids)

    @property
    def best_ask(self) -> Optional[float]:
        """最优卖价"""
        if not self.asks:
            return None
        return min(level.price for level in self.asks)

    @property
    def spread(self) -> Optional[float]:
        """买卖价差"""
        bid = self.best_bid
        ask = self.best_ask
        if bid is None or ask is None:
            return None
        return ask - bid


@dataclass
class MarketSnapshot:
    """市场快照（双边数据）

    包含 YES（UP）和 NO（DOWN）两侧的订单簿数据。
    """

    yes_data: SideData
    no_data: SideData
    timestamp: Optional[float] = None
    raw_message: Optional[dict[str, Any]] = None

    @property
    def price_sum(self) -> float:
        """YES + NO 最优卖价之和"""
        yes_ask = self.yes_data.best_ask or self.yes_data.price
        no_ask = self.no_data.best_ask or self.no_data.price
        return yes_ask + no_ask

    def to_dict(self) -> dict[str, Any]:
        return {
            "yes_token_id": self.yes_data.token_id,
            "no_token_id": self.no_data.token_id,
            "yes_price": self.yes_data.price,
            "no_price": self.no_data.price,
            "yes_best_bid": self.yes_data.best_bid,
            "yes_best_ask": self.yes_data.best_ask,
            "no_best_bid": self.no_data.best_bid,
            "no_best_ask": self.no_data.best_ask,
            "price_sum": self.price_sum,
            "timestamp": self.timestamp,
        }


@dataclass
class OrderBookContext:
    """订单簿上下文

    提供统一的订单簿访问接口。
    """

    yes_bids: list[OrderLevel] = field(default_factory=list)
    yes_asks: list[OrderLevel] = field(default_factory=list)
    no_bids: list[OrderLevel] = field(default_factory=list)
    no_asks: list[OrderLevel] = field(default_factory=list)
    yes_token_id: str = ""
    no_token_id: str = ""

    @property
    def yes_best_bid(self) -> Optional[float]:
        if not self.yes_bids:
            return None
        return max(level.price for level in self.yes_bids)

    @property
    def yes_best_ask(self) -> Optional[float]:
        if not self.yes_asks:
            return None
        return min(level.price for level in self.yes_asks)

    @property
    def no_best_bid(self) -> Optional[float]:
        if not self.no_bids:
            return None
        return max(level.price for level in self.no_bids)

    @property
    def no_best_ask(self) -> Optional[float]:
        if not self.no_asks:
            return None
        return min(level.price for level in self.no_asks)

    @classmethod
    def from_snapshot(cls, snapshot: MarketSnapshot) -> "OrderBookContext":
        """从市场快照创建上下文"""
        return cls(
            yes_bids=snapshot.yes_data.bids.copy(),
            yes_asks=snapshot.yes_data.asks.copy(),
            no_bids=snapshot.no_data.bids.copy(),
            no_asks=snapshot.no_data.asks.copy(),
            yes_token_id=snapshot.yes_data.token_id,
            no_token_id=snapshot.no_data.token_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "yes_best_bid": self.yes_best_bid,
            "yes_best_ask": self.yes_best_ask,
            "no_best_bid": self.no_best_bid,
            "no_best_ask": self.no_best_ask,
            "yes_token_id": self.yes_token_id,
            "no_token_id": self.no_token_id,
        }


@dataclass
class PositionContext:
    """持仓上下文

    自动追踪持仓数量和均价。
    """

    yes_size: float = 0.0
    no_size: float = 0.0
    yes_avg_cost: float = 0.0
    no_avg_cost: float = 0.0
    yes_total_cost: float = 0.0
    no_total_cost: float = 0.0

    @property
    def avg_sum(self) -> float:
        """YES + NO 平均成本之和"""
        return self.yes_avg_cost + self.no_avg_cost

    @property
    def total_size(self) -> float:
        """总持仓份额"""
        return self.yes_size + self.no_size

    @property
    def imbalance(self) -> float:
        """持仓不平衡度（YES - NO）"""
        return self.yes_size - self.no_size

    def is_balanced(self, tolerance: float = 0.5) -> bool:
        """持仓是否平衡"""
        return abs(self.imbalance) <= tolerance

    def has_position(self) -> bool:
        """是否有持仓"""
        return self.yes_size > 0 or self.no_size > 0

    def update_position(
        self,
        side: str,
        size: float,
        price: float,
        is_buy: bool = True,
    ) -> None:
        """更新持仓

        Args:
            side: "YES" 或 "NO"
            size: 成交份额
            price: 成交价格
            is_buy: 是否为买入
        """
        side = side.upper()
        if side == "YES":
            if is_buy:
                new_cost = self.yes_total_cost + size * price
                new_size = self.yes_size + size
                self.yes_total_cost = new_cost
                self.yes_size = new_size
                self.yes_avg_cost = new_cost / new_size if new_size > 0 else 0
            else:
                self.yes_size = max(0, self.yes_size - size)
                if self.yes_size == 0:
                    self.yes_total_cost = 0
                    self.yes_avg_cost = 0
        elif side == "NO":
            if is_buy:
                new_cost = self.no_total_cost + size * price
                new_size = self.no_size + size
                self.no_total_cost = new_cost
                self.no_size = new_size
                self.no_avg_cost = new_cost / new_size if new_size > 0 else 0
            else:
                self.no_size = max(0, self.no_size - size)
                if self.no_size == 0:
                    self.no_total_cost = 0
                    self.no_avg_cost = 0

    @classmethod
    def from_api_positions(
        cls,
        positions: list[dict[str, Any]],
        yes_token_id: str,
        no_token_id: str,
    ) -> "PositionContext":
        """从 API 持仓数据创建上下文"""
        ctx = cls()
        for pos in positions:
            token_id = pos.get("asset") or pos.get("token_id")
            size = float(pos.get("size", 0))
            avg_price = float(pos.get("avgPrice", 0) or pos.get("avg_price", 0))

            if token_id == yes_token_id:
                ctx.yes_size = size
                ctx.yes_avg_cost = avg_price
                ctx.yes_total_cost = size * avg_price
            elif token_id == no_token_id:
                ctx.no_size = size
                ctx.no_avg_cost = avg_price
                ctx.no_total_cost = size * avg_price

        return ctx

    def to_dict(self) -> dict[str, Any]:
        return {
            "yes_size": self.yes_size,
            "no_size": self.no_size,
            "yes_avg_cost": self.yes_avg_cost,
            "no_avg_cost": self.no_avg_cost,
            "avg_sum": self.avg_sum,
            "imbalance": self.imbalance,
            "is_balanced": self.is_balanced(),
        }


# =============================================================================
# 信号事件（推送前端）
# =============================================================================


class SignalEventType:
    """信号事件类型"""

    SIGNAL = "signal"  # 策略信号
    ORDER = "order"  # 订单执行
    POSITION = "position"  # 持仓变化
    ERROR = "error"  # 错误
    STATUS = "status"  # 状态更新


@dataclass
class SignalEvent:
    """信号事件（用于推送前端）

    统一的事件数据结构，包含策略信号、市场状态、持仓和执行结果。

    Attributes:
        event_type: 事件类型
        timestamp: 事件时间戳（毫秒）
        signal: 信号信息
        market: 市场快照摘要
        position: 持仓状态
        execution: 执行结果
        strategy: 策略信息
        error: 错误信息
    """

    event_type: str
    timestamp: int
    signal: Optional[dict[str, Any]] = None
    market: Optional[dict[str, Any]] = None
    position: Optional[dict[str, Any]] = None
    execution: Optional[dict[str, Any]] = None
    strategy: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_signal(
        cls,
        signal_type: str,
        reason: str,
        snapshot: "MarketSnapshot",
        position: "PositionContext",
        *,
        strategy_id: str = "",
        yes_size: Optional[float] = None,
        no_size: Optional[float] = None,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
        orders: Optional[list[dict[str, Any]]] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "SignalEvent":
        """从信号数据创建事件"""
        import time

        # 市场摘要
        market_data = {
            "yes_token_id": snapshot.yes_data.token_id,
            "no_token_id": snapshot.no_data.token_id,
            "yes_price": snapshot.yes_data.price,
            "no_price": snapshot.no_data.price,
            "yes_best_bid": snapshot.yes_data.best_bid,
            "yes_best_ask": snapshot.yes_data.best_ask,
            "no_best_bid": snapshot.no_data.best_bid,
            "no_best_ask": snapshot.no_data.best_ask,
            "price_sum": snapshot.price_sum,
        }

        # 信号数据
        signal_data = {
            "type": signal_type,
            "reason": reason,
            "yes_size": yes_size,
            "no_size": no_size,
            "yes_price": yes_price,
            "no_price": no_price,
            "metadata": metadata or {},
        }

        # 执行数据
        execution_data = None
        if orders is not None:
            execution_data = {
                "success": success,
                "orders": orders,
                "error": error,
            }

        # 策略数据
        strategy_data = None
        if strategy_id:
            strategy_data = {
                "id": strategy_id,
            }

        return cls(
            event_type=SignalEventType.SIGNAL,
            timestamp=int(time.time() * 1000),
            signal=signal_data,
            market=market_data,
            position=position.to_dict(),
            execution=execution_data,
            strategy=strategy_data,
            error=error,
        )

    @classmethod
    def from_order(
        cls,
        orders: list[dict[str, Any]],
        snapshot: "MarketSnapshot",
        position: "PositionContext",
        *,
        success: bool = True,
        error: Optional[str] = None,
    ) -> "SignalEvent":
        """从订单执行结果创建事件"""
        import time

        market_data = {
            "yes_price": snapshot.yes_data.price,
            "no_price": snapshot.no_data.price,
            "price_sum": snapshot.price_sum,
        }

        execution_data = {
            "success": success,
            "orders": orders,
            "error": error,
        }

        return cls(
            event_type=SignalEventType.ORDER,
            timestamp=int(time.time() * 1000),
            market=market_data,
            position=position.to_dict(),
            execution=execution_data,
            error=error,
        )

    @classmethod
    def from_error(cls, error: str, context: Optional[dict[str, Any]] = None) -> "SignalEvent":
        """创建错误事件"""
        import time

        return cls(
            event_type=SignalEventType.ERROR,
            timestamp=int(time.time() * 1000),
            error=error,
            execution={"success": False, "error": error, "context": context},
        )

    @classmethod
    def status(cls, message: str, data: Optional[dict[str, Any]] = None) -> "SignalEvent":
        """创建状态事件"""
        import time

        return cls(
            event_type=SignalEventType.STATUS,
            timestamp=int(time.time() * 1000),
            signal={"type": "STATUS", "reason": message, "metadata": data or {}},
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "signal": self.signal,
            "market": self.market,
            "position": self.position,
            "execution": self.execution,
            "strategy": self.strategy,
            "error": self.error,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)

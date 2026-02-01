"""Polymarket 模块"""

from .auth import PolymarketAuthProvider
from .book_stream import PolymarketBookStream
from .executor import StrategyExecutor, ExecutorConfig, ExecutionMode, ExecutionResult
from .models import (
    EventInfo,
    TokenInfo,
    MarketInfo,
    MarketSnapshot,
    SideData,
    OrderLevel,
    OrderBookContext,
    PositionContext,
    SignalEvent,
    SignalEventType,
)
from .positions import get_current_positions
from .resolver import MarketResolver
from .ws_client import PolymarketWebSocketClient

__all__ = [
    # 认证
    "PolymarketAuthProvider",
    # WebSocket
    "PolymarketBookStream",
    "PolymarketWebSocketClient",
    # 执行器
    "StrategyExecutor",
    "ExecutorConfig",
    "ExecutionMode",
    "ExecutionResult",
    # 数据模型
    "EventInfo",
    "TokenInfo",
    "MarketInfo",
    "MarketSnapshot",
    "SideData",
    "OrderLevel",
    "OrderBookContext",
    "PositionContext",
    "SignalEvent",
    "SignalEventType",
    # 工具
    "MarketResolver",
    "get_current_positions",
]

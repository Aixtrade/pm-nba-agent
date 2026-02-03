"""Polymarket 策略模块

策略系统提供决策与执行分离的架构，支持可插拔的策略实现。

使用方式：
    from pm_nba_agent.polymarket.strategies import (
        StrategyRegistry,
        BaseStrategy,
        TradingSignal,
        SignalType,
    )

    # 获取已注册的策略
    strategy = StrategyRegistry.get("relative_low_sum_hedge")

    # 生成交易信号
    signal = strategy.generate_signal(snapshot, order_book, position, params)
"""

from .base import BaseStrategy, TradingSignal, SignalType
from .registry import StrategyRegistry

# 自动注册内置策略
from . import merge_long_strategy  # noqa: F401
from . import locked_profit_strategy  # noqa: F401

__all__ = [
    "BaseStrategy",
    "TradingSignal",
    "SignalType",
    "StrategyRegistry",
]

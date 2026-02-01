"""策略基类和信号定义"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..models import OrderBookContext, PositionContext, MarketSnapshot


class SignalType(Enum):
    """交易信号类型"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradingSignal:
    """策略生成的交易信号

    Attributes:
        signal_type: 信号类型（BUY/SELL/HOLD）
        yes_size: YES/UP 方向份额
        no_size: NO/DOWN 方向份额
        yes_price: YES 方向建议价格
        no_price: NO 方向建议价格
        reason: 信号原因说明
        metadata: 策略特定元数据
    """

    signal_type: SignalType
    yes_size: Optional[float] = None
    no_size: Optional[float] = None
    yes_price: Optional[float] = None
    no_price: Optional[float] = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_actionable(self) -> bool:
        """信号是否可执行（非 HOLD 且有有效的 size/price）"""
        if self.signal_type == SignalType.HOLD:
            return False
        has_yes = self.yes_size is not None and self.yes_size > 0
        has_no = self.no_size is not None and self.no_size > 0
        return has_yes or has_no

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_type": self.signal_type.value,
            "yes_size": self.yes_size,
            "no_size": self.no_size,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class BaseStrategy(ABC):
    """策略抽象基类

    所有策略必须继承此类并实现 generate_signal 方法。

    Example:
        @StrategyRegistry.register("my_strategy")
        class MyStrategy(BaseStrategy):
            @property
            def strategy_id(self) -> str:
                return "my_strategy"

            def generate_signal(self, snapshot, order_book, position, params):
                # 策略逻辑...
                return TradingSignal(signal_type=SignalType.HOLD, reason="等待")
    """

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """策略唯一标识符"""
        ...

    @property
    def description(self) -> str:
        """策略描述"""
        return self.__class__.__doc__ or ""

    @abstractmethod
    def generate_signal(
        self,
        snapshot: "MarketSnapshot",
        order_book: "OrderBookContext",
        position: "PositionContext",
        params: dict[str, Any],
    ) -> Optional[TradingSignal]:
        """生成交易信号

        Args:
            snapshot: 市场快照数据
            order_book: 订单簿上下文
            position: 持仓上下文
            params: 策略参数

        Returns:
            交易信号；无决策时返回 None 或 HOLD 信号
        """
        ...

    def validate_signal(
        self,
        signal: TradingSignal,
        order_book: "OrderBookContext",
        position: "PositionContext",
        params: dict[str, Any],
    ) -> tuple[bool, str]:
        """验证信号是否合理

        子类可覆盖此方法添加自定义验证逻辑。

        Args:
            signal: 待验证的信号
            order_book: 订单簿上下文
            position: 持仓上下文
            params: 策略参数

        Returns:
            (是否有效, 原因)
        """
        if signal.signal_type == SignalType.HOLD:
            return True, "HOLD 信号无需验证"

        if signal.signal_type == SignalType.BUY:
            if signal.yes_size and signal.yes_size > 0:
                if signal.yes_price is None:
                    return False, "BUY YES 信号缺少价格"
            if signal.no_size and signal.no_size > 0:
                if signal.no_price is None:
                    return False, "BUY NO 信号缺少价格"

        if signal.signal_type == SignalType.SELL:
            if signal.yes_size and signal.yes_size > 0:
                if position.yes_size < signal.yes_size:
                    return False, f"YES 持仓不足: {position.yes_size} < {signal.yes_size}"
            if signal.no_size and signal.no_size > 0:
                if position.no_size < signal.no_size:
                    return False, f"NO 持仓不足: {position.no_size} < {signal.no_size}"

        return True, "验证通过"

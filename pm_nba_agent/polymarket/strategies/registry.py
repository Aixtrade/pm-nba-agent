"""策略注册表"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Type

from .base import BaseStrategy


logger = logging.getLogger(__name__)


class StrategyRegistry:
    """策略注册表

    提供策略的注册、查找和动态加载功能。

    Example:
        # 使用装饰器注册
        @StrategyRegistry.register("my_strategy")
        class MyStrategy(BaseStrategy):
            ...

        # 获取策略实例
        strategy = StrategyRegistry.get("my_strategy")

        # 列出所有策略
        for name in StrategyRegistry.list_strategies():
            print(name)
    """

    _strategies: dict[str, Type[BaseStrategy]] = {}
    _instances: dict[str, BaseStrategy] = {}

    @classmethod
    def register(
        cls,
        strategy_id: str,
    ) -> Callable[[Type[BaseStrategy]], Type[BaseStrategy]]:
        """注册策略的装饰器

        Args:
            strategy_id: 策略唯一标识符

        Returns:
            装饰器函数

        Example:
            @StrategyRegistry.register("my_strategy")
            class MyStrategy(BaseStrategy):
                ...
        """

        def decorator(strategy_cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
            if strategy_id in cls._strategies:
                logger.warning(
                    "策略 %s 已注册，将被覆盖: %s -> %s",
                    strategy_id,
                    cls._strategies[strategy_id].__name__,
                    strategy_cls.__name__,
                )
            cls._strategies[strategy_id] = strategy_cls
            logger.debug("已注册策略: %s -> %s", strategy_id, strategy_cls.__name__)
            return strategy_cls

        return decorator

    @classmethod
    def get(cls, strategy_id: str) -> Optional[BaseStrategy]:
        """获取策略实例（单例模式）

        Args:
            strategy_id: 策略标识符

        Returns:
            策略实例；未找到时返回 None
        """
        if strategy_id in cls._instances:
            return cls._instances[strategy_id]

        strategy_cls = cls._strategies.get(strategy_id)
        if strategy_cls is None:
            logger.error("策略未注册: %s", strategy_id)
            return None

        try:
            instance = strategy_cls()
            cls._instances[strategy_id] = instance
            return instance
        except Exception as exc:
            logger.error("策略实例化失败: %s - %s", strategy_id, exc)
            return None

    @classmethod
    def get_or_raise(cls, strategy_id: str) -> BaseStrategy:
        """获取策略实例，未找到时抛出异常

        Args:
            strategy_id: 策略标识符

        Returns:
            策略实例

        Raises:
            ValueError: 策略未注册或实例化失败
        """
        strategy = cls.get(strategy_id)
        if strategy is None:
            available = ", ".join(cls._strategies.keys()) or "(无)"
            raise ValueError(
                f"策略 '{strategy_id}' 未注册或加载失败，可用策略: {available}"
            )
        return strategy

    @classmethod
    def list_strategies(cls) -> list[str]:
        """列出所有已注册的策略 ID"""
        return list(cls._strategies.keys())

    @classmethod
    def is_registered(cls, strategy_id: str) -> bool:
        """检查策略是否已注册"""
        return strategy_id in cls._strategies

    @classmethod
    def clear(cls) -> None:
        """清空注册表（用于测试）"""
        cls._strategies.clear()
        cls._instances.clear()

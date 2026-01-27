"""数据收集器基类。"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from ..cache import CacheManager
from ..rate_limiter import RateLimiter


class BaseCollector(ABC):
    """所有数据收集器的基类。

    封装缓存和限流逻辑，子类只需实现 collect 方法。
    """

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """初始化收集器。

        Args:
            cache_manager: 缓存管理器实例，如果不提供则不使用缓存
        """
        self.cache = cache_manager
        self.rate_limiter = RateLimiter(delay=0.6)

    @abstractmethod
    def collect(self, *args, **kwargs) -> Any:
        """收集数据（子类必须实现）。

        Args:
            *args: 子类特定的参数
            **kwargs: 子类特定的参数

        Returns:
            收集到的数据
        """
        pass

    def _fetch_with_cache(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        verbose: bool = False
    ) -> Any:
        """带缓存的数据获取。

        先检查缓存，缓存未命中则调用 API 并缓存结果。

        Args:
            key: 缓存键
            fetch_func: 获取数据的函数（无参数）
            verbose: 是否输出详细日志

        Returns:
            获取到的数据，失败返回 None
        """
        # 1. 检查缓存
        if self.cache:
            cached = self.cache.get(key)
            if cached is not None:
                if verbose:
                    print(f"  ✓ 使用缓存: {key}")
                return cached

        # 2. 限流
        self.rate_limiter.wait()

        # 3. 调用API
        try:
            if verbose:
                print(f"  → API 调用: {key}")
            data = fetch_func()

            # 4. 缓存结果
            if self.cache and data is not None:
                self.cache.set(key, data)

            return data

        except Exception as e:
            if verbose:
                print(f"  ❌ API 调用失败: {e}")
            return None

"""API 限流器，控制请求频率避免被限流。"""

import time
from typing import Optional


class RateLimiter:
    """API 限流器，确保请求之间有固定时间间隔。

    使用方法:
        limiter = RateLimiter(delay=0.6)
        limiter.wait()  # 等待到可以发送下一个请求
    """

    def __init__(self, delay: float = 0.6):
        """初始化限流器。

        Args:
            delay: 两次请求之间的最小间隔（秒），默认0.6秒
        """
        self.delay = delay
        self.last_call: Optional[float] = None

    def wait(self) -> None:
        """等待到可以发送下一个请求。

        如果距离上次调用不足 delay 秒，则等待剩余时间。
        """
        if self.last_call is not None:
            elapsed = time.time() - self.last_call
            if elapsed < self.delay:
                wait_time = self.delay - elapsed
                time.sleep(wait_time)

        self.last_call = time.time()

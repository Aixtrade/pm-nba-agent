"""Redis 客户端封装"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Optional

import redis.asyncio as redis
from loguru import logger


class RedisClient:
    """异步 Redis 客户端封装"""

    def __init__(self, url: Optional[str] = None):
        self._url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """建立连接"""
        if self._pool is not None:
            return

        self._pool = redis.ConnectionPool.from_url(
            self._url,
            decode_responses=True,
            max_connections=10,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        # 测试连接
        await self._client.ping()
        logger.info("Redis 已连接: {}", self._url.split("@")[-1])

    async def close(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.aclose()
            self._pool = None
        logger.info("Redis 连接已关闭")

    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._client is None:
            raise RuntimeError("Redis 未连接，请先调用 connect()")
        return self._client

    # ========== 基础操作 ==========

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
    ) -> None:
        """设置值"""
        await self.client.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        """删除键"""
        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return await self.client.exists(key) > 0

    # ========== Set 操作 ==========

    async def sadd(self, key: str, *values: str) -> int:
        """添加到集合"""
        return await self.client.sadd(key, *values)

    async def srem(self, key: str, *values: str) -> int:
        """从集合移除"""
        return await self.client.srem(key, *values)

    async def smembers(self, key: str) -> set[str]:
        """获取集合所有成员"""
        return await self.client.smembers(key)

    # ========== Pub/Sub 操作 ==========

    async def publish(self, channel: str, message: str) -> int:
        """发布消息"""
        return await self.client.publish(channel, message)

    async def subscribe(
        self,
        *channels: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """订阅 Channel（异步生成器）"""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.aclose()

    async def psubscribe(
        self,
        *patterns: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """模式订阅 Channel（异步生成器）"""
        pubsub = self.client.pubsub()
        await pubsub.psubscribe(*patterns)

        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    yield message
        finally:
            await pubsub.punsubscribe(*patterns)
            await pubsub.aclose()


# 全局单例
_redis_client: Optional[RedisClient] = None


async def get_redis() -> RedisClient:
    """获取全局 Redis 客户端"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


async def close_redis() -> None:
    """关闭全局 Redis 客户端"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

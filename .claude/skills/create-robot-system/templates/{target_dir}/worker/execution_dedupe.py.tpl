"""执行幂等去重。"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from {package_name}.shared import Channels, RedisClient


class ExecutionDedupe:
    """基于 Redis 的幂等执行去重器。

    使用 Redis SET NX + TTL 实现。
    同一个 (stage, payload) 组合在 TTL 内只会被执行一次。
    """

    def __init__(self, redis: RedisClient, task_id: str, ttl_seconds: int | None = None):
        self._redis = redis
        self._task_id = task_id
        self._ttl = ttl_seconds or int(os.getenv("EXECUTION_DEDUPE_TTL_SECONDS", "300"))

    def key_for(self, stage: str, payload: dict[str, Any]) -> str:
        """生成去重键。"""
        raw = _stable_json(payload)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{Channels.PREFIX}:task:{self._task_id}:execution_dedupe:{stage}:{digest}"

    async def acquire(self, dedupe_key: str, context: dict[str, Any] | None = None) -> bool:
        """尝试获取执行权（成功=True，重复=False）。"""
        context_value = _stable_json(context or {})
        result = await self._redis.client.set(
            dedupe_key,
            context_value,
            ex=self._ttl,
            nx=True,
        )
        return bool(result)


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

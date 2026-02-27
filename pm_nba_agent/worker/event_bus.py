"""事件发布器 — 封装 Redis publish + 快照缓存 + 任务状态持久化"""

import json
from typing import Any

from pm_nba_agent.shared import Channels, RedisClient, TaskState, TaskStatus

from .sse_utils import format_sse_event


SNAPSHOT_EVENTS = {
    "polymarket_info",
    "polymarket_book",
    "scoreboard",
    "auto_buy_state",
    "auto_trade_state",
    "auto_sell_state",
    "position_state",
}


class EventPublisher:
    """统一事件发布：Redis Pub/Sub + 快照缓存 + 任务状态持久化。"""

    def __init__(self, task_id: str, redis: RedisClient) -> None:
        self.task_id = task_id
        self.redis = redis

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = format_sse_event(event_type, payload)
        await self.publish_raw(event)

    async def publish_raw(self, event: str) -> None:
        await self._cache_snapshot(event)
        channel = Channels.task_events(self.task_id)
        await self.redis.publish(channel, event)

    async def save_status(self, status: TaskStatus) -> None:
        key = Channels.task_status(self.task_id)
        await self.redis.set(key, status.to_json(), ex=86400)

    async def load_or_create_status(self) -> TaskStatus:
        key = Channels.task_status(self.task_id)
        data = await self.redis.get(key)
        if not data:
            return TaskStatus.create(self.task_id)
        try:
            return TaskStatus.from_json(data)
        except Exception:
            return TaskStatus.create(self.task_id)

    async def publish_status(self, status: TaskStatus) -> None:
        payload = json.dumps(status.to_dict(), ensure_ascii=False)
        await self.publish_raw(f"event: task_status\ndata: {payload}\n\n")

    async def _cache_snapshot(self, event: str) -> None:
        event_type = None
        for line in event.splitlines():
            if line.startswith("event:"):
                event_type = line[6:].strip()

        if not event_type or event_type not in SNAPSHOT_EVENTS:
            return

        snapshot_key = Channels.task_snapshot(self.task_id, event_type)
        await self.redis.set(snapshot_key, event, ex=86400)

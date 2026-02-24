"""SSE 实时流路由（任务订阅模式）"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from redis.exceptions import ConnectionError as RedisConnectionError

from ..services.auth import require_auth
from ...shared import Channels, RedisClient, TaskState, TaskStatus


router = APIRouter(prefix="/api/v1/live", tags=["live"])

ACTIVE_TASK_STATES = {
    TaskState.PENDING,
    TaskState.RUNNING,
    TaskState.CANCELLING,
}

USER_STREAM_SYNC_INTERVAL_SECONDS = 2.0
USER_STREAM_HEARTBEAT_SECONDS = 15.0


def require_redis(request: Request) -> RedisClient:
    """获取 Redis 客户端"""
    redis: RedisClient | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="任务模式不可用，请配置 REDIS_URL",
        )
    return redis


def normalize_sse_message(message: str) -> str:
    """兼容历史错误格式的 SSE 消息（字面量 \\n）"""
    if "\\n" in message and "\n" not in message and message.startswith("event: "):
        return message.replace("\\n", "\n")
    return message


def parse_sse_event(event: str) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """解析 SSE 事件字符串，返回 (event_type, payload)"""
    event_type: Optional[str] = None
    payload_text: Optional[str] = None

    for line in event.splitlines():
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:") and payload_text is None:
            payload_text = line[5:].strip()

    if not event_type:
        return None, None
    if not payload_text:
        return event_type, None

    try:
        parsed = json.loads(payload_text)
    except Exception:
        return event_type, None

    if not isinstance(parsed, dict):
        return event_type, None

    return event_type, parsed


def format_sse_event(event_type: str, payload: dict[str, Any]) -> str:
    """格式化 SSE 消息"""
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def now_iso() -> str:
    """当前 UTC 时间（ISO）"""
    return datetime.utcnow().isoformat() + "Z"


def to_task_execution_payload(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """标准化 task_execution 事件 payload"""
    return {
        "task_id": task_id,
        "source": str(payload.get("source", "unknown")),
        "success": bool(payload.get("success", False)),
        "orders": payload.get("orders") if isinstance(payload.get("orders"), list) else [],
        "error": payload.get("error"),
        "timestamp": str(payload.get("timestamp", now_iso())),
    }


async def load_user_active_statuses(
    redis: RedisClient,
    user_id: str,
) -> dict[str, TaskStatus]:
    """加载用户当前活跃任务状态"""
    task_ids = await redis.smembers(Channels.user_tasks(user_id))
    result: dict[str, TaskStatus] = {}

    for task_id in task_ids:
        data = await redis.get(Channels.task_status(task_id))
        if not data:
            continue
        try:
            status = TaskStatus.from_json(data)
        except Exception:
            continue
        if status.user_id and status.user_id != user_id:
            continue
        if status.state in ACTIVE_TASK_STATES:
            result[task_id] = status

    return result


async def sync_pubsub_task_channels(
    pubsub: Any,
    desired_task_ids: set[str],
    subscribed_task_ids: set[str],
) -> set[str]:
    """同步 PubSub 订阅的任务 Channel 集合"""
    to_subscribe = desired_task_ids - subscribed_task_ids
    to_unsubscribe = subscribed_task_ids - desired_task_ids

    if to_subscribe:
        channels = [Channels.task_events(task_id) for task_id in to_subscribe]
        await pubsub.subscribe(*channels)

    if to_unsubscribe:
        channels = [Channels.task_events(task_id) for task_id in to_unsubscribe]
        await pubsub.unsubscribe(*channels)

    return set(desired_task_ids)


@router.get("/subscribe/{task_id}")
async def subscribe_task(
    request: Request,
    task_id: str,
) -> StreamingResponse:
    """
    订阅任务事件流

    订阅后台任务的 SSE 事件流。客户端可以随时订阅/取消订阅，
    不影响后台任务的运行。

    **路径参数**:
    - `task_id`: 任务 ID（通过 `/api/v1/tasks/create` 获取）

    **事件类型**:
    - `polymarket_info`: Polymarket 市场信息
    - `polymarket_book`: Polymarket 订单簿消息
    - `scoreboard`: 比分板数据
    - `boxscore`: 详细统计数据
    - `analysis_chunk`: AI 分析流式输出
    - `strategy_signal`: 策略信号
    - `heartbeat`: 心跳保活
    - `error`: 错误事件
    - `game_end`: 比赛结束
    - `task_status`: 任务状态更新事件
    - `task_end`: 任务结束事件

    **示例请求**:
    ```bash
    curl -N http://localhost:8000/api/v1/live/subscribe/abc12345 \\
      -H "Authorization: Bearer <token>" \\
      -H "Accept: text/event-stream"
    ```
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    # 检查任务是否存在 + 归属校验
    status_key = Channels.task_status(task_id)
    data = await redis.get(status_key)
    if not data:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = TaskStatus.from_json(data)

    # 归属校验：user_id 不匹配时返回 404
    if status.user_id and status.user_id != user_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 如果任务已结束，返回最终状态
    if status.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
        async def final_event() -> AsyncGenerator[str, None]:
            yield f'event: task_end\ndata: {{"task_id": "{task_id}", "state": "{status.state.value}"}}\n\n'

        return StreamingResponse(
            final_event(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # 订阅任务事件 Channel
    channel = Channels.task_events(task_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        """事件生成器"""
        pubsub = None
        try:
            # 使用新的 pubsub 连接
            pubsub = redis.client.pubsub()
            await pubsub.subscribe(channel)

            # 发送连接成功事件
            yield f'event: subscribed\ndata: {{"task_id": "{task_id}"}}\n\n'
            yield f"event: task_status\ndata: {status.to_json()}\n\n"

            snapshot_events = [
                "polymarket_info",
                "scoreboard",
                "polymarket_book",
                "auto_buy_state",
                "auto_trade_state",
                "auto_sell_state",
                "position_state",
            ]
            for event_name in snapshot_events:
                snapshot_key = Channels.task_snapshot(task_id, event_name)
                snapshot_event = await redis.get(snapshot_key)
                if snapshot_event:
                    yield normalize_sse_message(snapshot_event)

            async for message in pubsub.listen():
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break

                if message["type"] != "message":
                    continue

                event_data = normalize_sse_message(message["data"])
                yield event_data

                # 如果是任务结束事件，退出循环
                if "event: task_end" in event_data or "event: game_end" in event_data:
                    break

        except RedisConnectionError as e:
            logger.error("Redis 连接错误 (task={}): {}", task_id, e)
            error_payload = json.dumps({
                "code": "REDIS_CONNECTION_ERROR",
                "message": "服务器繁忙，请稍后重试",
                "recoverable": True,
                "timestamp": "",
            })
            yield f"event: error\ndata: {error_payload}\n\n"

        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.aclose()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/subscribe/user/tasks")
async def subscribe_user_tasks(request: Request) -> StreamingResponse:
    """
    用户级任务总览聚合流（单连接）。

    聚合当前用户所有活跃任务（pending/running/cancelling）的关键事件：
    - task_status
    - task_end
    - task_position_state
    - task_execution
    - heartbeat
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    async def event_generator() -> AsyncGenerator[str, None]:
        pubsub = None
        subscribed_task_ids: set[str] = set()
        active_task_ids: set[str] = set()
        known_status: dict[str, str] = {}
        sent_position_snapshot: set[str] = set()
        loop = asyncio.get_running_loop()
        next_sync_at = 0.0
        next_heartbeat_at = 0.0

        try:
            pubsub = redis.client.pubsub()
            yield format_sse_event("subscribed", {"scope": "user_tasks", "timestamp": now_iso()})

            while True:
                if await request.is_disconnected():
                    break

                now = loop.time()

                if now >= next_sync_at:
                    active_statuses = await load_user_active_statuses(redis, user_id)
                    desired_task_ids = set(active_statuses.keys())
                    subscribed_task_ids = await sync_pubsub_task_channels(
                        pubsub,
                        desired_task_ids=desired_task_ids,
                        subscribed_task_ids=subscribed_task_ids,
                    )

                    # 发布活跃任务状态，帮助前端建立任务上下文
                    for task_id, status in active_statuses.items():
                        status_json = status.to_json()
                        if known_status.get(task_id) != status_json:
                            known_status[task_id] = status_json
                            yield format_sse_event("task_status", status.to_dict())

                        # 每个活跃任务在连接期间只回放一次持仓快照
                        if task_id not in sent_position_snapshot:
                            snapshot_key = Channels.task_snapshot(task_id, "position_state")
                            snapshot_event = await redis.get(snapshot_key)
                            if snapshot_event:
                                event_type, payload = parse_sse_event(normalize_sse_message(snapshot_event))
                                if event_type == "position_state" and isinstance(payload, dict):
                                    yield format_sse_event("task_position_state", {
                                        "task_id": task_id,
                                        **payload,
                                    })
                            sent_position_snapshot.add(task_id)

                    # 检测刚结束的任务并发 task_end
                    ended_task_ids = active_task_ids - desired_task_ids
                    for task_id in ended_task_ids:
                        status_data = await redis.get(Channels.task_status(task_id))
                        if not status_data:
                            continue
                        try:
                            status = TaskStatus.from_json(status_data)
                        except Exception:
                            continue
                        if status.user_id and status.user_id != user_id:
                            continue
                        if status.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
                            yield format_sse_event("task_end", {
                                "task_id": task_id,
                                "state": status.state.value,
                            })

                    active_task_ids = desired_task_ids
                    known_status = {task_id: text for task_id, text in known_status.items() if task_id in active_task_ids}
                    sent_position_snapshot = {task_id for task_id in sent_position_snapshot if task_id in active_task_ids}
                    next_sync_at = now + USER_STREAM_SYNC_INTERVAL_SECONDS

                    # 无活跃任务时主动结束 SSE 连接（由前端按需重连）
                    if not active_task_ids:
                        yield format_sse_event("idle", {
                            "reason": "no_active_tasks",
                            "timestamp": now_iso(),
                        })
                        break

                if now >= next_heartbeat_at:
                    yield format_sse_event("heartbeat", {"timestamp": now_iso()})
                    next_heartbeat_at = now + USER_STREAM_HEARTBEAT_SECONDS

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message or message.get("type") != "message":
                    continue

                channel = str(message.get("channel", ""))
                task_id = Channels.parse_task_id(channel)
                if not task_id:
                    continue

                event_data = normalize_sse_message(str(message.get("data", "")))
                event_type, payload = parse_sse_event(event_data)
                if not event_type or not isinstance(payload, dict):
                    continue

                if event_type == "task_status":
                    yield format_sse_event("task_status", payload)
                    continue

                if event_type == "task_end":
                    yield format_sse_event("task_end", {
                        "task_id": task_id,
                        "state": str(payload.get("state", "")),
                    })
                    continue

                if event_type == "position_state":
                    yield format_sse_event("task_position_state", {
                        "task_id": task_id,
                        **payload,
                    })
                    continue

                if event_type in ("auto_trade_execution", "auto_sell_execution"):
                    yield format_sse_event("task_execution", to_task_execution_payload(task_id, payload))
                    continue

                if event_type == "strategy_signal":
                    execution = payload.get("execution")
                    if isinstance(execution, dict) and execution.get("source") == "task_auto_buy":
                        yield format_sse_event("task_execution", to_task_execution_payload(task_id, execution))

        except RedisConnectionError as e:
            logger.error("Redis 连接错误 (user={}): {}", user_id, e)
            error_payload = {
                "code": "REDIS_CONNECTION_ERROR",
                "message": "服务器繁忙，请稍后重试",
                "recoverable": True,
                "timestamp": now_iso(),
            }
            yield format_sse_event("error", error_payload)
        finally:
            if pubsub:
                try:
                    if subscribed_task_ids:
                        await pubsub.unsubscribe(*[Channels.task_events(task_id) for task_id in subscribed_task_ids])
                    await pubsub.aclose()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

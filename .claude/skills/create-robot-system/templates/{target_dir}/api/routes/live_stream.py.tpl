"""SSE Bridge — 将 Redis Streams 桥接为 Server-Sent Events。"""

from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from {package_name}.shared import Channels, RedisClient, TaskState, TaskStatus


router = APIRouter(prefix="/api/v1/live", tags=["live"])


@router.get("/subscribe/{task_id}")
async def subscribe_task(
    request: Request,
    task_id: str,
) -> StreamingResponse:
    """订阅后台任务 SSE 事件流。"""
    redis: RedisClient | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status_code=503, detail="任务模式不可用，请配置 REDIS_URL")

    status_key = Channels.task_status(task_id)
    data = await redis.get(status_key)
    if not data:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = TaskStatus.from_json(data)

    # 已终结的任务直接返回最终状态
    if status.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):

        async def final_event() -> AsyncGenerator[str, None]:
            payload = {
                "task_id": task_id,
                "state": status.state.value,
            }
            yield _format_sse_event("task_end", payload)

        return StreamingResponse(
            final_event(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    generator = _subscribe_task_via_streams(request, redis, task_id, status)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _subscribe_task_via_streams(
    request: Request,
    redis: RedisClient,
    task_id: str,
    status: TaskStatus,
) -> AsyncGenerator[str, None]:
    """Streams → SSE 桥接（支持 Last-Event-ID 断点续传）。"""
    # 支持 history=1 参数回放历史
    default_cursor = "0" if request.query_params.get("history") == "1" else "$"
    streams = {
        Channels.task_stream(task_id, stream_name): default_cursor
        for stream_name in Channels.ALL_STREAMS
    }

    # Last-Event-ID 断点续传
    stream_hint, last_msg_id = _parse_last_event_id(request.headers.get("last-event-id", ""))
    if stream_hint and last_msg_id:
        stream_key = Channels.task_stream(task_id, stream_hint)
        if stream_key in streams:
            streams[stream_key] = last_msg_id

    # 发送初始状态
    yield _format_sse_event("subscribed", {"task_id": task_id, "source": "streams"})
    yield f"event: task_status\ndata: {status.to_json()}\n\n"

    while True:
        if await request.is_disconnected():
            break

        try:
            results = await redis.xread(streams=streams, count=100, block=1000)
        except Exception as exc:
            logger.error("Streams xread 异常 task={}: {}", task_id, exc)
            error_payload = json.dumps(
                {
                    "code": "STREAM_READ_ERROR",
                    "message": str(exc),
                    "recoverable": True,
                },
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {error_payload}\n\n"
            continue

        if not results:
            # 心跳
            yield _format_sse_event("heartbeat", {"ts": _now_iso()})
            continue

        for stream_key, messages in results:
            stream_name = _parse_stream_name(task_id, stream_key)
            if messages:
                # 游标推进到本批次末尾
                streams[stream_key] = messages[-1][0]

            for msg_id, fields in messages:
                event_type, payload = _signal_to_sse(fields)
                if not event_type:
                    continue

                # event ID 格式: "stream_name|msg_id"
                event_id = f"{stream_name}|{msg_id}"
                yield _format_sse_event(event_type, payload, event_id=event_id)

                if fields.get("type") in {"task_end"}:
                    final_state = str(payload.get("state") or "completed")
                    yield _format_sse_event("task_end", {"task_id": task_id, "state": final_state})
                    return


def _signal_to_sse(fields: dict[str, str]) -> tuple[str | None, dict]:
    """将 Signal fields 转换为 SSE 事件。

    # 🔧 自定义点: 添加业务特定的信号类型映射
    """
    signal_type = str(fields.get("type", ""))
    raw_data = fields.get("data", "{}")

    type_map = {
        # 🔧 自定义点: 根据业务添加 signal_type → sse_event_type 映射
        "data_update": "data_update",
        "process_result": "process_result",
        "task_status": "task_status",
        "task_end": "task_end",
        "robot_status": "robot_status",
        "robot_start": "robot_status",
        "robot_stop": "robot_status",
        "robot_error": "robot_status",
        "heartbeat": "heartbeat",
        "error": "error",
    }
    event_type = type_map.get(signal_type)
    if not event_type:
        return None, {}

    try:
        payload = json.loads(raw_data)
        if not isinstance(payload, dict):
            payload = {"value": payload}
    except Exception:
        payload = {}

    # robot_start/stop/error 统一为 robot_status 事件
    if signal_type in {"robot_start", "robot_stop", "robot_error"}:
        robot_type = str(payload.get("robot_type", "") or "")
        state = "running" if signal_type == "robot_start" else "stopped"
        if signal_type == "robot_error":
            state = "error"
        payload = {
            "robot_type": robot_type,
            "state": state,
            "last_error": payload.get("error"),
            "stage": payload.get("stage"),
            "timestamp": payload.get("timestamp") or fields.get("timestamp"),
        }

    return event_type, payload


def _format_sse_event(event_type: str, payload: dict, event_id: str | None = None) -> str:
    """格式化 SSE 事件字符串。"""
    event_id_prefix = f"id: {event_id}\n" if event_id else ""
    return event_id_prefix + f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _parse_stream_name(task_id: str, stream_key: str) -> str:
    """从 Stream Key 解析 stream 名。"""
    prefix = f"{Channels.PREFIX}:task:{task_id}:stream:"
    if stream_key.startswith(prefix):
        return stream_key[len(prefix):]
    return stream_key


def _parse_last_event_id(value: str) -> tuple[str | None, str | None]:
    """解析 Last-Event-ID 头。格式: stream_name|msg_id"""
    if not value or "|" not in value:
        return None, None
    stream_name, msg_id = value.split("|", 1)
    stream_name = stream_name.strip()
    msg_id = msg_id.strip()
    if not stream_name or not msg_id:
        return None, None
    return stream_name, msg_id


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

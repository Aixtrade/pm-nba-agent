"""SSE Bridge — 从 Redis Streams 读取事件并转发为 SSE。

支持 Last-Event-ID 断点续传。
SSE 事件类型名与 v1 完全一致（前端零修改）。
"""

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger

from ..services.auth import require_auth
from ...robots.base import Signal
from ...shared import Channels, RedisClient, TaskStatus
from ...shared.channels import ALL_STREAMS, StreamName

router = APIRouter(prefix="/api/v2/live", tags=["live-v2"])

# 信号类型到 SSE 事件类型的映射
SIGNAL_TO_SSE_EVENT: dict[str, str] = {
    "scoreboard": "scoreboard",
    "boxscore": "boxscore",
    "game_end": "game_end",
    "polymarket_info": "polymarket_info",
    "polymarket_book": "polymarket_book",
    "position_state": "position_state",
    "strategy_signal": "strategy_signal",
    "trade_execution": "auto_trade_execution",
    "analysis_chunk": "analysis_chunk",
    "task_status": "task_status",
    "task_end": "task_end",
    "robot_start": "robot_status",
    "robot_stop": "robot_status",
    "robot_error": "robot_status",
    "robot_status": "robot_status",
    "heartbeat": "heartbeat",
}


def require_redis(request: Request) -> RedisClient:
    """获取 Redis 客户端。"""
    redis: RedisClient | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis 不可用")
    return redis


@router.get("/subscribe/{task_id}")
async def subscribe_task_v2(
    task_id: str,
    request: Request,
    history: int = 0,
):
    """订阅任务 SSE 流（v2：基于 Redis Streams）。

    Args:
        task_id: 任务 ID
        history: 是否回放历史消息（1=是，0=否）

    Headers:
        Last-Event-ID: 断点续传的最后事件 ID（格式: stream_name:msg_id）
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    # 验证任务存在且属于当前用户
    status_key = Channels.task_status(task_id)
    status_data = await redis.get(status_key)
    if not status_data:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        status = TaskStatus.from_json(status_data)
    except Exception as exc:
        logger.warning("任务状态解析失败 task={}: {}", task_id, exc)
        raise HTTPException(status_code=500, detail="任务状态异常")

    if status.user_id and status.user_id != user_id:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 解析 Last-Event-ID
    last_event_id = request.headers.get("Last-Event-ID")
    last_ids = _parse_last_event_id(task_id, last_event_id)

    return StreamingResponse(
        _stream_events(redis, task_id, last_ids, history=bool(history)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_events(
    redis: RedisClient,
    task_id: str,
    last_ids: dict[str, str],
    *,
    history: bool = False,
) -> AsyncGenerator[str, None]:
    """从 Redis Streams 读取并生成 SSE 事件。"""
    # 构建要订阅的 stream keys
    stream_keys = {
        Channels.task_stream(task_id, stream_name): last_ids.get(stream_name, "0" if history else "$")
        for stream_name in ALL_STREAMS
    }

    # 发送 subscribed 事件
    yield _format_sse("subscribed", {"task_id": task_id, "mode": "streams_v2"})

    # 先回放关键 snapshot（新连接时不必等待下一条增量）
    info_key = Channels.task_snapshot(task_id, "polymarket_info")
    book_key = Channels.task_snapshot(task_id, "polymarket_book")
    info_sent = False
    book_sent = False
    try:
        info_raw = await redis.get(info_key)
        if info_raw:
            info_data = json.loads(info_raw)
            if isinstance(info_data, dict):
                yield _format_sse("polymarket_info", info_data)
                info_sent = True
    except Exception as exc:
        logger.warning("SSE Bridge 读取 polymarket_info snapshot 失败: {}", exc)

    try:
        book_raw = await redis.get(book_key)
        if book_raw:
            book_data = json.loads(book_raw)
            if isinstance(book_data, dict):
                yield _format_sse("polymarket_book", book_data)
                book_sent = True
    except Exception as exc:
        logger.warning("SSE Bridge 读取 polymarket_book snapshot 失败: {}", exc)

    heartbeat_counter = 0
    try:
        while True:
            try:
                results = await redis.xread(
                    streams=stream_keys,
                    count=100,
                    block=2000,
                )
            except Exception as exc:
                logger.warning("SSE Bridge xread 异常: {}", exc)
                await asyncio.sleep(1.0)
                continue

            # BookBot 可能还在 setup（解析 URL），snapshot 尚未写入；
            # 每次循环检查一次，直到成功推送给前端
            if not info_sent:
                try:
                    info_raw = await redis.get(info_key)
                    if info_raw:
                        info_data = json.loads(info_raw)
                        if isinstance(info_data, dict):
                            yield _format_sse("polymarket_info", info_data)
                            info_sent = True
                except Exception:
                    pass

            if not book_sent:
                try:
                    book_raw = await redis.get(book_key)
                    if book_raw:
                        book_data = json.loads(book_raw)
                        if isinstance(book_data, dict):
                            yield _format_sse("polymarket_book", book_data)
                            book_sent = True
                except Exception:
                    pass

            if results:
                for stream_key, messages in results:
                    stream_name = _extract_stream_name(task_id, stream_key)
                    for msg_id, fields in messages:
                        stream_keys[stream_key] = msg_id
                        signal = Signal.from_fields(msg_id, fields)

                        sse_event_type = SIGNAL_TO_SSE_EVENT.get(signal.type, signal.type)
                        if signal.type == "trade_execution":
                            if signal.source == "profit_sell":
                                sse_event_type = "auto_sell_execution"
                            else:
                                sse_event_type = "auto_trade_execution"
                        event_id = f"{stream_name}:{msg_id}"

                        yield _format_sse(
                            sse_event_type,
                            signal.data,
                            event_id=event_id,
                        )

                        # 检查 task_end
                        if signal.type == "task_end":
                            return
                heartbeat_counter = 0
            else:
                heartbeat_counter += 1
                if heartbeat_counter >= 5:  # 每 10 秒发一次心跳
                    yield _format_sse("heartbeat", {"timestamp": _now_iso()})
                    heartbeat_counter = 0

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error("SSE Bridge 异常: {}", exc)
        yield _format_sse("error", {"code": "STREAM_ERROR", "message": str(exc)})


def _format_sse(
    event_type: str,
    data: dict[str, Any],
    *,
    event_id: str | None = None,
) -> str:
    """格式化为 SSE 字符串。"""
    parts = []
    if event_id:
        parts.append(f"id: {event_id}")
    parts.append(f"event: {event_type}")
    parts.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)


def _extract_stream_name(task_id: str, stream_key: str) -> str:
    """从 stream key 提取 stream name。"""
    prefix = f"{Channels.PREFIX}:task:{task_id}:stream:"
    if stream_key.startswith(prefix):
        return stream_key[len(prefix):]
    return stream_key


def _parse_last_event_id(
    task_id: str,
    last_event_id: str | None,
) -> dict[str, str]:
    """解析 Last-Event-ID 为 stream_name -> msg_id 映射。"""
    if not last_event_id:
        return {}

    result: dict[str, str] = {}
    # 格式: stream_name:msg_id (如 "nba_data:1234567890-0")
    parts = last_event_id.split(":", 1)
    if len(parts) == 2:
        stream_name, msg_id = parts
        if stream_name in [s.value for s in StreamName]:
            result[stream_name] = msg_id

    return result


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"

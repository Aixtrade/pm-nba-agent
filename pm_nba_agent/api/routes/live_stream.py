"""SSE 实时流路由"""

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ..models.requests import LiveStreamRequest
from ..services.data_fetcher import DataFetcher
from ..services.game_stream import GameStreamService
from ..services.auth import get_auth_config, is_token_valid
from ...agent import GameAnalyzer
from ...shared import Channels, RedisClient, TaskState, TaskStatus


router = APIRouter(prefix="/api/v1/live", tags=["live"])


def require_auth(request: Request) -> None:
    passphrase, salt = get_auth_config()

    if not passphrase:
        raise HTTPException(status_code=500, detail="Auth 配置缺失")

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少访问令牌")

    provided = auth_header.removeprefix("Bearer ").strip()
    if not is_token_valid(provided, passphrase, salt):
        raise HTTPException(status_code=401, detail="访问令牌无效")


@router.post("/stream")
async def stream_game_data(
    request: Request,
    body: LiveStreamRequest
) -> StreamingResponse:
    """
    SSE 实时比赛数据流

    通过 POST 请求建立 SSE 连接，实时推送比赛数据。

    **请求体参数**:
    - `url`: Polymarket 事件 URL
    - `poll_interval`: 轮询间隔（5-60秒，默认10秒）
    - `include_scoreboard`: 是否包含比分板（默认 true）
    - `include_boxscore`: 是否包含详细统计（默认 true）
    - `include_playbyplay`: 是否获取逐回合（仅用于分析上下文，默认 true）
    - `playbyplay_limit`: 首次逐回合数据条数（1-100，默认20）
    - `enable_analysis`: 是否启用 AI 分析（默认 true）
    - `analysis_interval`: AI 分析间隔（10-120秒，默认30秒）

    **事件类型**:
    - `polymarket_info`: Polymarket 市场信息
    - `polymarket_book`: Polymarket 订单簿消息
    - `scoreboard`: 比分板数据
    - `boxscore`: 详细统计数据
    - `analysis_chunk`: AI 分析流式输出
    - `heartbeat`: 心跳保活
    - `error`: 错误事件
    - `game_end`: 比赛结束

    **示例请求**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/live/stream \\
      -H "Content-Type: application/json" \\
      -H "Accept: text/event-stream" \\
      -d '{"url":"https://polymarket.com/event/nba-por-was-2026-01-27"}'
    ```
    """
    require_auth(request)

    # 获取全局资源
    fetcher: DataFetcher = request.app.state.fetcher
    analyzer: GameAnalyzer = request.app.state.analyzer

    # 创建流服务
    stream_service = GameStreamService(fetcher, analyzer)

    async def event_generator():
        async for event in stream_service.create_stream(body):
            # 检查客户端是否断开
            if await request.is_disconnected():
                break
            yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )


def require_redis(request: Request) -> RedisClient:
    """获取 Redis 客户端"""
    redis: RedisClient | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="任务模式不可用，请配置 REDIS_URL",
        )
    return redis


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
    与 `/api/v1/live/stream` 相同，额外包含：
    - `task_status`: 任务状态更新事件
    - `task_end`: 任务结束事件

    **示例请求**:
    ```bash
    curl -N http://localhost:8000/api/v1/live/subscribe/abc12345 \\
      -H "Authorization: Bearer <token>" \\
      -H "Accept: text/event-stream"
    ```
    """
    require_auth(request)
    redis = require_redis(request)

    # 检查任务是否存在
    status_key = Channels.task_status(task_id)
    data = await redis.get(status_key)
    if not data:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = TaskStatus.from_json(data)

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
        # 使用新的 pubsub 连接
        pubsub = redis.client.pubsub()
        await pubsub.subscribe(channel)

        try:
            # 发送连接成功事件
            yield f'event: subscribed\ndata: {{"task_id": "{task_id}"}}\n\n'
            yield f"event: task_status\ndata: {status.to_json()}\n\n"

            snapshot_events = [
                "polymarket_info",
                "scoreboard",
                "polymarket_book",
                "auto_buy_state",
            ]
            for event_name in snapshot_events:
                snapshot_key = Channels.task_snapshot(task_id, event_name)
                snapshot_event = await redis.get(snapshot_key)
                if snapshot_event:
                    yield snapshot_event

            async for message in pubsub.listen():
                # 检查客户端是否断开
                if await request.is_disconnected():
                    break

                if message["type"] != "message":
                    continue

                event_data = message["data"]
                yield event_data

                # 如果是任务结束事件，退出循环
                if "event: task_end" in event_data or "event: game_end" in event_data:
                    break

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

"""SSE 实时流路由"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ..models.requests import LiveStreamRequest
from ..services.data_fetcher import DataFetcher
from ..services.game_stream import GameStreamService


router = APIRouter(prefix="/api/v1/live", tags=["live"])


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
    - `include_playbyplay`: 是否包含逐回合（默认 true）
    - `playbyplay_limit`: 首次逐回合数据条数（1-100，默认20）

    **事件类型**:
    - `scoreboard`: 比分板数据
    - `boxscore`: 详细统计数据
    - `playbyplay`: 逐回合数据（增量推送）
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
    # 获取全局 fetcher
    fetcher: DataFetcher = request.app.state.fetcher

    # 创建流服务
    stream_service = GameStreamService(fetcher)

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

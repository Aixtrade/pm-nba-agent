"""SSE 实时流路由"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ..models.requests import LiveStreamRequest
from ..services.data_fetcher import DataFetcher
from ..services.game_stream import GameStreamService
from ..services.auth import get_auth_config, is_token_valid
from ...agent import GameAnalyzer


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
    - `include_playbyplay`: 是否包含逐回合（默认 true）
    - `playbyplay_limit`: 首次逐回合数据条数（1-100，默认20）
    - `enable_analysis`: 是否启用 AI 分析（默认 true）
    - `analysis_interval`: AI 分析间隔（10-120秒，默认30秒）

    **事件类型**:
    - `scoreboard`: 比分板数据
    - `boxscore`: 详细统计数据
    - `playbyplay`: 逐回合数据（增量推送）
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

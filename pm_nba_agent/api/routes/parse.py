"""URL 解析路由"""

from fastapi import APIRouter, HTTPException

from ..models.requests import ParsePolymarketRequest
from ...parsers import parse_polymarket_url


router = APIRouter(prefix="/api/v1/parse", tags=["parse"])


@router.post("/polymarket")
async def parse_polymarket(body: ParsePolymarketRequest) -> dict:
    """
    解析 Polymarket URL

    **请求体参数**:
    - `url`: Polymarket 事件 URL

    **返回字段**:
    - `event`: 解析出的比赛信息
    """
    event_info = parse_polymarket_url(body.url)
    if not event_info:
        raise HTTPException(status_code=400, detail="URL 解析失败")

    display_name = (
        f"{event_info.team1_abbr} vs {event_info.team2_abbr} - "
        f"{event_info.game_date}"
    )

    return {
        "ok": True,
        "event": {
            "team1_abbr": event_info.team1_abbr,
            "team2_abbr": event_info.team2_abbr,
            "game_date": event_info.game_date,
            "url": event_info.url,
            "display_name": display_name,
        },
    }

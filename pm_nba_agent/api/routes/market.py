"""Polymarket 市场信息路由"""

from fastapi import APIRouter, HTTPException, Request

from ..models.requests import PolymarketMarketConstraintsResponse
from ..services.auth import require_auth
from ...polymarket.market import get_market_constraints


router = APIRouter(prefix="/api/v1/polymarket", tags=["polymarket"])


@router.get("/market/{token_id}", response_model=PolymarketMarketConstraintsResponse)
async def get_market_constraints_route(
    request: Request,
    token_id: str,
) -> PolymarketMarketConstraintsResponse:
    """获取 Polymarket 市场限制信息"""
    require_auth(request)

    try:
        data = await get_market_constraints(token_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取市场限制失败: {exc}") from exc

    return PolymarketMarketConstraintsResponse(**data)

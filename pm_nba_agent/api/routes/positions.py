"""Polymarket 持仓查询路由"""

from fastapi import APIRouter, HTTPException, Request

from ..models.requests import (
    PolymarketMarketPositionsRequest,
    PolymarketMarketPositionsResponse,
    PolymarketPositionSide,
)
from ..services.auth import require_auth
from ...polymarket.config import POLYMARKET_PROXY_ADDRESS
from ...polymarket.positions import get_current_positions


router = APIRouter(prefix="/api/v1/polymarket", tags=["polymarket"])


def _build_position_sides(
    positions: list[dict],
    outcomes: list[str] | None,
) -> list[PolymarketPositionSide]:
    sizes: dict[str, float] = {}
    assets: dict[str, str | None] = {}
    initial_values: dict[str, float] = {}
    avg_prices: dict[str, float | None] = {}
    cur_prices: dict[str, float | None] = {}

    for position in positions:
        outcome = str(position.get("outcome") or "").strip()
        if outcome:
            size_value = position.get("size", 0)
            try:
                size = float(size_value)
            except (TypeError, ValueError):
                size = 0.0
            sizes[outcome] = sizes.get(outcome, 0.0) + size
            initial_value = position.get("initialValue", 0)
            try:
                cost = float(initial_value)
            except (TypeError, ValueError):
                cost = 0.0
            initial_values[outcome] = initial_values.get(outcome, 0.0) + cost
            asset = position.get("asset")
            if asset and outcome not in assets:
                assets[outcome] = str(asset)

            if outcome not in avg_prices:
                avg_price_value = position.get("avgPrice")
                if avg_price_value is not None:
                    try:
                        avg_prices[outcome] = float(avg_price_value)
                    except (TypeError, ValueError):
                        avg_prices[outcome] = None

            if outcome not in cur_prices:
                cur_price_value = position.get("curPrice")
                if cur_price_value is not None:
                    try:
                        cur_prices[outcome] = float(cur_price_value)
                    except (TypeError, ValueError):
                        cur_prices[outcome] = None

        opposite_outcome = str(position.get("oppositeOutcome") or "").strip()
        if opposite_outcome and opposite_outcome not in sizes:
            sizes[opposite_outcome] = 0.0
            initial_values[opposite_outcome] = 0.0
            opposite_asset = position.get("oppositeAsset")
            if opposite_asset and opposite_outcome not in assets:
                assets[opposite_outcome] = str(opposite_asset)

    if outcomes:
        for outcome in outcomes:
            if outcome not in sizes:
                sizes[outcome] = 0.0
            if outcome not in initial_values:
                initial_values[outcome] = 0.0

    ordered_outcomes = outcomes or list(sizes.keys())

    return [
        PolymarketPositionSide(
            outcome=outcome,
            size=sizes.get(outcome, 0.0),
            initial_value=initial_values.get(outcome, 0.0),
            asset=assets.get(outcome),
            avg_price=avg_prices.get(outcome),
            cur_price=cur_prices.get(outcome),
        )
        for outcome in ordered_outcomes
    ]


@router.post("/positions/market", response_model=PolymarketMarketPositionsResponse)
async def get_market_positions(
    request: Request,
    body: PolymarketMarketPositionsRequest,
) -> PolymarketMarketPositionsResponse:
    """查询指定市场双边持仓"""
    require_auth(request)

    try:
        positions = await get_current_positions(
            user_address=body.user_address,
            condition_ids=[body.condition_id],
            size_threshold=body.size_threshold,
            redeemable=body.redeemable,
            mergeable=body.mergeable,
            proxy_address=body.proxy_address,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取持仓失败: {exc}") from exc

    if positions is None:
        raise HTTPException(status_code=502, detail="持仓接口返回空结果")

    resolved_user = body.user_address or body.proxy_address or POLYMARKET_PROXY_ADDRESS or ""
    sides = _build_position_sides(positions, body.outcomes)

    return PolymarketMarketPositionsResponse(
        condition_id=body.condition_id,
        user_address=resolved_user,
        sides=sides,
    )

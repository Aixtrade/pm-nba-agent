"""Polymarket 下单路由"""

from fastapi import APIRouter, HTTPException, Request

from ..models.requests import (
    PolymarketOrderRequest,
    PolymarketOrderResponse,
    PolymarketBatchOrderRequest,
    PolymarketBatchOrderResponse,
)
from ..services.auth import get_auth_config, is_token_valid
from ...polymarket.orders import (
    create_polymarket_order,
    create_polymarket_orders_batch,
)


router = APIRouter(prefix="/api/v1/polymarket", tags=["polymarket"])


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


@router.post("/orders", response_model=PolymarketOrderResponse)
async def create_order(
    request: Request,
    body: PolymarketOrderRequest,
) -> PolymarketOrderResponse:
    """创建 Polymarket 订单"""
    require_auth(request)

    try:
        response = await create_polymarket_order(
            token_id=body.token_id,
            side=body.side,
            price=body.price,
            size=body.size,
            order_type=body.order_type,
            expiration=body.expiration,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建订单失败: {exc}") from exc

    return PolymarketOrderResponse(
        order_type=body.order_type,
        response=response,
    )


@router.post("/orders/batch", response_model=PolymarketBatchOrderResponse)
async def create_orders_batch(
    request: Request,
    body: PolymarketBatchOrderRequest,
) -> PolymarketBatchOrderResponse:
    """批量创建 Polymarket 订单"""
    require_auth(request)

    try:
        results = await create_polymarket_orders_batch(
            orders=[order.model_dump() for order in body.orders],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"创建批量订单失败: {exc}") from exc

    return PolymarketBatchOrderResponse(results=results)

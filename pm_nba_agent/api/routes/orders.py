"""Polymarket 下单路由"""

from fastapi import APIRouter, HTTPException, Request
from loguru import logger

from ..models.requests import (
    PolymarketOrderRequest,
    PolymarketOrderResponse,
    PolymarketBatchOrderRequest,
    PolymarketBatchOrderResponse,
)
from ..services.auth import require_auth
from ...polymarket.orders import (
    create_polymarket_order,
    create_polymarket_orders_batch,
)


router = APIRouter(prefix="/api/v1/polymarket", tags=["polymarket"])
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
            private_key=body.private_key,
            proxy_address=body.proxy_address,
        )
    except ValueError as exc:
        logger.warning("创建订单参数错误: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("创建订单失败: {}", exc)
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
        batch_private_key = body.orders[0].private_key if body.orders else None
        batch_proxy_address = body.orders[0].proxy_address if body.orders else None
        results = await create_polymarket_orders_batch(
            orders=[order.model_dump() for order in body.orders],
            private_key=batch_private_key,
            proxy_address=batch_proxy_address,
        )
    except ValueError as exc:
        logger.warning("创建批量订单参数错误: {}", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("创建批量订单失败: {}", exc)
        raise HTTPException(status_code=500, detail=f"创建批量订单失败: {exc}") from exc

    return PolymarketBatchOrderResponse(results=results)

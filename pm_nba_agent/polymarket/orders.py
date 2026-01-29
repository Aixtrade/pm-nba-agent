"""Polymarket 下单接口"""

from __future__ import annotations

from typing import Any, Optional, cast

from py_clob_client.clob_types import OrderArgs, PostOrdersArgs
from py_clob_client.order_builder.constants import BUY, SELL

from .auth import PolymarketAuthProvider


_AUTH_PROVIDER = PolymarketAuthProvider()
_SIDE_MAP = {
    "BUY": BUY,
    "SELL": SELL,
}


def _normalize_side(side: str) -> str:
    normalized = side.strip().upper()
    if normalized not in _SIDE_MAP:
        raise ValueError("side 仅支持 BUY 或 SELL")
    return normalized


def _normalize_order_type(order_type: str) -> str:
    normalized = order_type.strip().upper()
    if normalized not in {"GTC", "GTD"}:
        raise ValueError("order_type 仅支持 GTC 或 GTD")
    return normalized


async def create_polymarket_order(
    *,
    token_id: str,
    side: str,
    price: float,
    size: float,
    order_type: str = "GTC",
    expiration: Optional[str] = None,
    private_key: Optional[str] = None,
    proxy_address: Optional[str] = None,
) -> Any:
    normalized_side = _normalize_side(side)
    normalized_order_type = _normalize_order_type(order_type)

    if normalized_order_type == "GTD" and not expiration:
        raise ValueError("GTD 订单必须提供 expiration")

    client = await _AUTH_PROVIDER.get_clob_client(
        private_key=private_key,
        proxy_address=proxy_address,
        missing_key_message="POLYMARKET_PRIVATE_KEY 未配置",
    )

    order_kwargs: dict[str, Any] = {
        "price": price,
        "size": size,
        "side": _SIDE_MAP[normalized_side],
        "token_id": token_id,
    }
    if expiration:
        order_kwargs["expiration"] = expiration

    order_args = OrderArgs(**order_kwargs)
    signed_order = client.create_order(order_args)
    order_type_value = "GTC" if normalized_order_type == "GTC" else "GTD"
    return client.post_order(signed_order, cast(Any, order_type_value))


async def create_polymarket_orders_batch(
    orders: list[dict[str, Any]],
    *,
    private_key: Optional[str] = None,
    proxy_address: Optional[str] = None,
) -> Any:
    if not orders:
        raise ValueError("orders 不能为空")

    client = await _AUTH_PROVIDER.get_clob_client(
        private_key=private_key,
        proxy_address=proxy_address,
        missing_key_message="POLYMARKET_PRIVATE_KEY 未配置",
    )

    post_orders: list[PostOrdersArgs] = []
    for index, order in enumerate(orders, start=1):
        try:
            token_id = order["token_id"]
            side = _normalize_side(order["side"])
            order_type = _normalize_order_type(order.get("order_type", "GTC"))
            price = float(order["price"])
            size = float(order["size"])
            expiration = order.get("expiration")
        except KeyError as exc:
            raise ValueError(f"orders[{index}] 缺少字段 {exc}") from exc

        if order_type == "GTD" and not expiration:
            raise ValueError(f"orders[{index}] GTD 订单必须提供 expiration")

        order_kwargs: dict[str, Any] = {
            "price": price,
            "size": size,
            "side": _SIDE_MAP[side],
            "token_id": token_id,
        }
        if expiration:
            order_kwargs["expiration"] = expiration

        order_args = OrderArgs(**order_kwargs)
        signed_order = client.create_order(order_args)
        order_type_value = "GTC" if order_type == "GTC" else "GTD"
        post_orders.append(
            PostOrdersArgs(
                order=signed_order,
                orderType=cast(Any, order_type_value),
            )
        )

    return client.post_orders(post_orders)

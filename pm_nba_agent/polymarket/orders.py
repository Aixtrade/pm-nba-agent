"""Polymarket 下单接口"""

from __future__ import annotations

from typing import Any, Optional, cast

from loguru import logger
from py_clob_client.clob_types import OrderArgs, PostOrdersArgs
from py_clob_client.order_builder.constants import BUY, SELL

from .auth import PolymarketAuthProvider


_AUTH_PROVIDER = PolymarketAuthProvider()
_SIDE_MAP = {
    "BUY": BUY,
    "SELL": SELL,
}


def _format_clob_error(exc: Exception) -> str:
    details: list[str] = []
    details.append(f"type={type(exc).__name__}")

    for attr in ("message", "detail", "error", "reason"):
        value = getattr(exc, attr, None)
        if value:
            details.append(f"{attr}={value}")

    response = getattr(exc, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        if status_code is not None:
            details.append(f"status_code={status_code}")
        text = getattr(response, "text", None)
        if text:
            details.append(f"response_text={text}")
        json_payload = None
        if hasattr(response, "json"):
            try:
                json_payload = response.json()
            except Exception:
                json_payload = None
        if json_payload is not None:
            details.append(f"response_json={json_payload}")

    if exc.args:
        details.append(f"args={exc.args}")

    return "; ".join(details)


def _validate_basic_inputs(token_id: str, price: float, size: float) -> None:
    if not str(token_id).strip():
        raise ValueError("token_id 不能为空")
    if price <= 0:
        raise ValueError("price 必须大于 0")
    if size <= 0:
        raise ValueError("size 必须大于 0")


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
    _validate_basic_inputs(token_id, price, size)

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

    try:
        order_args = OrderArgs(**order_kwargs)
        signed_order = client.create_order(order_args)
        order_type_value = "GTC" if normalized_order_type == "GTC" else "GTD"
        result = client.post_order(signed_order, cast(Any, order_type_value))
        logger.info(
            "下单成功: token_id={}, side={}, price={}, size={}, order_type={}",
            token_id, normalized_side, price, size, normalized_order_type,
        )
        return result
    except Exception as exc:
        error_details = _format_clob_error(exc)
        logger.error(
            "下单失败: token_id={}, side={}, price={}, size={}, order_type={}, error={}, details={}",
            token_id, normalized_side, price, size, normalized_order_type, exc, error_details,
        )
        raise ValueError(
            "Polymarket 下单失败: "
            f"token_id={token_id}, side={normalized_side}, price={price}, size={size}, "
            f"order_type={normalized_order_type}, expiration={expiration}, error={exc}, "
            f"details={error_details}"
        ) from exc


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

        _validate_basic_inputs(token_id, price, size)

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

        try:
            order_args = OrderArgs(**order_kwargs)
            signed_order = client.create_order(order_args)
            order_type_value = "GTC" if order_type == "GTC" else "GTD"
            post_orders.append(
                PostOrdersArgs(
                    order=signed_order,
                    orderType=cast(Any, order_type_value),
                )
            )
        except Exception as exc:
            error_details = _format_clob_error(exc)
            logger.error(
                "订单签名失败: orders[{}] token_id={}, side={}, price={}, size={}, error={}, details={}",
                index, token_id, side, price, size, exc, error_details,
            )
            raise ValueError(
                "Polymarket 订单签名失败: "
                f"orders[{index}] token_id={token_id}, side={side}, price={price}, size={size}, "
                f"order_type={order_type}, expiration={expiration}, error={exc}, "
                f"details={error_details}"
            ) from exc

    try:
        result = client.post_orders(post_orders)
        logger.info("批量下单成功: count={}", len(post_orders))
        return result
    except Exception as exc:
        error_details = _format_clob_error(exc)
        logger.error(
            "批量下单失败: count={}, error={}, details={}",
            len(post_orders), exc, error_details,
        )
        raise ValueError(
            "Polymarket 批量下单失败: "
            f"count={len(post_orders)}, error={exc}, details={error_details}"
        ) from exc

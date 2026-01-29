"""Polymarket 市场查询"""

from __future__ import annotations

from typing import Any

from py_clob_client.client import ClobClient

from .config import POLYMARKET_CLOB_URL


def _get_public_client() -> ClobClient:
    return ClobClient(host=POLYMARKET_CLOB_URL)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def get_market_constraints(token_id: str) -> dict[str, Any]:
    token_id = str(token_id).strip()
    if not token_id:
        raise ValueError("token_id 不能为空")

    client = _get_public_client()
    try:
        orderbook = client.get_order_book(token_id)
    except Exception as exc:
        raise ValueError(f"获取订单簿失败: {exc}") from exc

    try:
        tick_size_value = orderbook.tick_size or client.get_tick_size(token_id)
    except Exception as exc:
        raise ValueError(f"获取 tick_size 失败: {exc}") from exc

    try:
        fee_rate_bps = client.get_fee_rate_bps(token_id)
    except Exception:
        fee_rate_bps = None

    tick_size_float = _to_float(tick_size_value)
    min_price = tick_size_float if tick_size_float is not None else None
    max_price = 1 - tick_size_float if tick_size_float is not None else None

    return {
        "token_id": token_id,
        "tick_size": tick_size_float,
        "min_order_size": _to_float(orderbook.min_order_size),
        "min_price": min_price,
        "max_price": max_price,
        "neg_risk": orderbook.neg_risk,
        "fee_rate_bps": fee_rate_bps,
        "last_trade_price": _to_float(orderbook.last_trade_price),
    }

"""Polymarket 持仓查询"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from .config import POLYMARKET_DATA_API_URL, POLYMARKET_PROXY_ADDRESS


logger = logging.getLogger(__name__)


def _resolve_user_address(
    user_address: Optional[str],
    proxy_address: Optional[str],
) -> Optional[str]:
    if user_address:
        return user_address
    if proxy_address:
        return proxy_address
    return POLYMARKET_PROXY_ADDRESS


def _join_list(values: Optional[list[Any]]) -> Optional[str]:
    if not values:
        return None
    return ",".join(str(value) for value in values)


async def get_current_positions(
    *,
    user_address: Optional[str] = None,
    condition_ids: Optional[list[str]] = None,
    event_ids: Optional[list[int]] = None,
    size_threshold: Optional[float] = None,
    redeemable: Optional[bool] = None,
    mergeable: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_direction: Optional[str] = None,
    title: Optional[str] = None,
    proxy_address: Optional[str] = None,
) -> Optional[list[dict[str, Any]]]:
    """查询用户当前持仓

    Args:
        user_address: 用户钱包地址（0x 开头）。为空时使用 proxy_address 或环境变量。
        condition_ids: condition_id 列表（对应 market 参数）。
        event_ids: eventId 列表，与 condition_ids 互斥。
        size_threshold: sizeThreshold 过滤值。
        redeemable: 是否仅返回可赎回持仓。
        mergeable: 是否仅返回可合并持仓。
        limit: 每次返回数量。
        offset: 分页偏移。
        sort_by: 排序字段。
        sort_direction: 排序方向。
        title: 标题过滤（前缀匹配）。
        proxy_address: 代理钱包地址（可覆盖环境变量）。

    Returns:
        持仓列表；失败时返回 None。
    """

    if condition_ids and event_ids:
        raise ValueError("condition_ids 与 event_ids 不能同时传入")

    resolved_user = _resolve_user_address(user_address, proxy_address)
    if not resolved_user:
        raise ValueError("user_address 不能为空")

    params: dict[str, Any] = {
        "user": resolved_user,
        "limit": limit,
        "offset": offset,
    }
    market_param = _join_list(condition_ids)
    if market_param:
        params["market"] = market_param
    event_param = _join_list(event_ids)
    if event_param:
        params["eventId"] = event_param
    if size_threshold is not None:
        params["sizeThreshold"] = size_threshold
    if redeemable is not None:
        params["redeemable"] = redeemable
    if mergeable is not None:
        params["mergeable"] = mergeable
    if sort_by:
        params["sortBy"] = sort_by
    if sort_direction:
        params["sortDirection"] = sort_direction
    if title:
        params["title"] = title

    url = f"{POLYMARKET_DATA_API_URL.rstrip('/')}/positions"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.debug("请求持仓: %s params=%s", url, params)
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logger.warning("持仓响应非列表: %s", type(data))
                return None
            return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP 错误: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            return None
        except httpx.RequestError as exc:
            url = str(getattr(exc.request, "url", ""))
            detail = f"{exc.__class__.__name__}: {exc!r}"
            logger.error("请求失败: %s %s", url, detail)
            print(f"Polymarket 请求失败: {url} {detail}")
            return None
        except Exception as exc:
            logger.error("获取持仓失败: %s", exc)
            return None

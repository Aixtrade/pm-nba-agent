"""Polymarket 事件和市场解析"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from .config import POLYMARKET_GAMMA_API_URL
from .models import EventInfo, TokenInfo, MarketInfo


logger = logging.getLogger(__name__)


class MarketResolver:
    """Polymarket 事件和市场解析工具

    用于从事件 URL 或 ID 解析市场信息，并通过 REST API 获取 Token 详情。
    """

    EVENT_URL_PATTERN = r"https://polymarket\.com/event/([a-z0-9\-]+)"

    @staticmethod
    def parse_event_url(url: str) -> Optional[str]:
        """从 URL 解析事件 ID

        支持的格式：
        - URL: https://polymarket.com/event/btc-updown-15m-1766464200
        - 直接 ID: btc-updown-15m-1766464200
        """
        match = re.search(MarketResolver.EVENT_URL_PATTERN, url)
        if match:
            return match.group(1)

        if re.match(r"^[a-z0-9\-]+$", url):
            return url

        return None

    @staticmethod
    async def get_market_by_slug(slug: str) -> Optional[dict]:
        """通过 slug 获取市场详情"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{POLYMARKET_GAMMA_API_URL}/markets/slug/{slug}"
                logger.debug("请求市场详情: %s", url)
                response = await client.get(url)
                if response.status_code == 404:
                    logger.warning("市场不存在: %s", slug)
                    return None
                response.raise_for_status()
                return response.json()
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
                logger.error("获取市场详情失败: %s", exc)
                return None

    @staticmethod
    async def get_event_by_slug(slug: str) -> Optional[dict]:
        """通过 slug 获取事件详情"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{POLYMARKET_GAMMA_API_URL}/events/slug/{slug}"
                logger.debug("请求事件详情: %s", url)
                response = await client.get(url)
                if response.status_code == 404:
                    logger.warning("事件不存在: %s", slug)
                    return None
                response.raise_for_status()
                return response.json()
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
                logger.error("获取事件详情失败: %s", exc)
                return None

    @staticmethod
    def _parse_list_field(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                return []
        return []

    @staticmethod
    def _normalize_outcome(outcome_raw: str) -> Optional[str]:
        if not outcome_raw:
            return None
        outcome_str = outcome_raw.strip()
        return outcome_str or None

    @staticmethod
    def _extract_market_info(
        market_data: Optional[dict],
        slug: str,
    ) -> tuple[Optional[str], list[TokenInfo], Optional[str], Optional[MarketInfo]]:
        if not market_data:
            return None, [], None, None

        condition_id = market_data.get("conditionId") or market_data.get("condition_id")
        outcomes = MarketResolver._parse_list_field(market_data.get("outcomes"))
        token_ids = MarketResolver._parse_list_field(
            market_data.get("clobTokenIds") or market_data.get("clob_token_ids")
        )
        question = market_data.get("question") or market_data.get("title")
        description = market_data.get("description") or market_data.get("details")
        market_slug = market_data.get("slug") or slug
        market_id = (
            market_data.get("id")
            or market_data.get("marketId")
            or market_data.get("market_id")
        )

        tokens: list[TokenInfo] = []
        for idx, token_id in enumerate(token_ids):
            outcome_raw = outcomes[idx] if idx < len(outcomes) else ""
            outcome = MarketResolver._normalize_outcome(outcome_raw)
            if not outcome:
                continue
            tokens.append(
                TokenInfo(
                    token_id=token_id,
                    outcome=outcome,
                    condition_id=condition_id or "",
                    market_slug=market_slug,
                )
            )

        title = question or market_data.get("title")
        market_info = MarketInfo(
            slug=market_slug,
            question=question,
            description=description,
            condition_id=condition_id,
            outcomes=outcomes,
            clob_token_ids=token_ids,
            market_id=market_id,
            raw_data=market_data,
        )
        logger.info(
            "解析市场 %s，condition_id=%s，Tokens: %s",
            slug,
            condition_id,
            len(tokens),
        )
        return condition_id, tokens, title, market_info

    @staticmethod
    async def get_market_info(
        slug: str,
    ) -> tuple[Optional[str], list[TokenInfo], Optional[str], Optional[MarketInfo]]:
        """通过 slug 获取 condition_id 与 Token 信息"""
        market_data = await MarketResolver.get_market_by_slug(slug)
        return MarketResolver._extract_market_info(market_data, slug)

    @staticmethod
    def _select_market_from_event(event_data: Any) -> Optional[dict]:
        if isinstance(event_data, dict):
            markets = event_data.get("markets")
            if isinstance(markets, list) and markets:
                return markets[0]
            market = event_data.get("market")
            if isinstance(market, dict):
                return market
        if isinstance(event_data, list) and event_data:
            if isinstance(event_data[0], dict):
                return event_data[0]
        return None

    @staticmethod
    def extract_event_metadata(event_id: str) -> tuple[str, str]:
        """从事件 ID 提取元信息"""
        parts = event_id.split("-")

        asset = "UNKNOWN"
        interval = "15m"

        if len(parts) >= 3:
            asset = parts[0].upper()
            interval = parts[2]

        return asset, interval

    @staticmethod
    async def resolve_event(event_url_or_id: str) -> Optional[EventInfo]:
        """完整解析事件信息"""
        event_id = MarketResolver.parse_event_url(event_url_or_id)
        if not event_id:
            logger.error("无法解析事件标识: %s", event_url_or_id)
            return None

        asset, interval = MarketResolver.extract_event_metadata(event_id)

        market_data = await MarketResolver.get_market_by_slug(event_id)
        event_data: Optional[dict] = None
        if not market_data:
            event_data = await MarketResolver.get_event_by_slug(event_id)
            market_data = MarketResolver._select_market_from_event(event_data)

        condition_id, tokens, title, market_info = MarketResolver._extract_market_info(
            market_data,
            event_id,
        )
        if not condition_id:
            logger.warning("无法获取事件 condition_id: %s", event_id)

        return EventInfo(
            event_id=event_id,
            title=title or f"{asset} {interval} UP/DOWN",
            interval=interval,
            asset=asset,
            tokens=tokens,
            condition_id=condition_id,
            market_info=market_info,
            event_data=event_data,
        )

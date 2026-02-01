"""Polymarket 订单簿订阅流"""

from __future__ import annotations

import asyncio
from loguru import logger
import os
from typing import Any, Optional

from .auth import PolymarketAuthProvider
from .ws_client import PolymarketWebSocketClient
from .config import (
    POLYMARKET_WS_API_KEY,
    POLYMARKET_WS_API_SECRET,
    POLYMARKET_WS_API_PASSPHRASE,
)


class PolymarketBookStream:
    """Polymarket 订单簿消息订阅"""

    def __init__(self, auth_provider: Optional[PolymarketAuthProvider] = None) -> None:
        self._auth_provider = auth_provider or PolymarketAuthProvider()
        self._client: Optional[PolymarketWebSocketClient] = None
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._is_ready = False

    @property
    def queue(self) -> asyncio.Queue[Any]:
        return self._queue

    async def start(self, asset_ids: list[str]) -> bool:
        if not asset_ids:
            logger.info("无可订阅的 Token ID，跳过 WebSocket 连接")
            return False

        if self._client and self._is_ready:
            await self._client.subscribe(
                asset_ids=asset_ids,
                subscribe_type=PolymarketWebSocketClient.SUBSCRIBE_TYPE_BOOK,
            )
            return True

        api_key, api_secret, api_passphrase = await self._resolve_ws_creds()
        self._client = PolymarketWebSocketClient(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            on_message=self._handle_message,
            on_error=self._handle_error,
            on_close=self._handle_close,
        )

        connected = await self._client.connect()
        if not connected:
            return False

        self._is_ready = True
        return await self._client.subscribe(
            asset_ids=asset_ids,
            subscribe_type=PolymarketWebSocketClient.SUBSCRIBE_TYPE_BOOK,
        )

    async def close(self) -> None:
        if not self._client:
            return
        await self._client.close()
        self._client = None
        self._is_ready = False

    async def _resolve_ws_creds(self) -> tuple[str, str, str]:
        api_key = os.getenv("POLYMARKET_WS_API_KEY") or POLYMARKET_WS_API_KEY
        api_secret = (
            os.getenv("POLYMARKET_WS_API_SECRET") or POLYMARKET_WS_API_SECRET
        )
        api_passphrase = (
            os.getenv("POLYMARKET_WS_API_PASSPHRASE") or POLYMARKET_WS_API_PASSPHRASE
        )
        if api_key and api_secret and api_passphrase:
            return (
                api_key,
                api_secret,
                api_passphrase,
            )

        try:
            api_creds = await self._auth_provider.get_api_creds(
                missing_key_message="缺少 Polymarket 私钥，无法生成 WebSocket 订阅凭证",
            )
        except Exception as exc:
            logger.warning("无法获取 Polymarket API 凭证，将尝试匿名订阅: {}", exc)
            return "", "", ""

        def _get_creds_value(creds: Any, *keys: str) -> str:
            if isinstance(creds, dict):
                for key in keys:
                    value = creds.get(key)
                    if value:
                        return str(value)
                return ""

            for key in keys:
                value = getattr(creds, key, None)
                if value:
                    return str(value)
            return ""

        api_key = _get_creds_value(api_creds, "apiKey", "api_key", "key")
        api_secret = _get_creds_value(api_creds, "apiSecret", "api_secret", "secret")
        api_passphrase = _get_creds_value(
            api_creds,
            "apiPassphrase",
            "api_passphrase",
            "passphrase",
        )

        return api_key, api_secret, api_passphrase

    async def _handle_message(self, message: Any) -> None:
        if isinstance(message, dict):
            event_type = str(message.get("event_type", "")).lower()
            if event_type and event_type not in {"book", "price_change"}:
                logger.debug("忽略非 book/price_change 消息: {}", event_type)
                return
        await self._queue.put(message)

    def _handle_error(self, error: Exception) -> None:
        logger.error("Polymarket WebSocket 错误: {}", error)

    def _handle_close(self) -> None:
        logger.info("Polymarket WebSocket 连接已关闭")

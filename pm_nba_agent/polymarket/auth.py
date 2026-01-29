"""Polymarket 鉴权与客户端管理"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from py_clob_client.client import ClobClient

from .config import (
    POLYMARKET_PRIVATE_KEY,
    POLYMARKET_PROXY_ADDRESS,
    POLYMARKET_CLOB_URL,
    POLYMARKET_CHAIN_ID,
    POLYMARKET_SIGNATURE_TYPE,
)


class PolymarketAuthProvider:
    """Lazily derives API credentials and returns a configured CLOB client."""

    def __init__(self, clob_client: Optional[ClobClient] = None) -> None:
        self._clob_client = clob_client
        self._api_creds: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._current_private_key: Optional[str] = None
        self._current_proxy_address: Optional[str] = None

    def _resolve_private_key(
        self,
        private_key: Optional[str],
        missing_key_message: Optional[str],
    ) -> str:
        if private_key:
            return private_key

        private_key = os.getenv("POLYMARKET_PRIVATE_KEY") or POLYMARKET_PRIVATE_KEY
        if not private_key:
            raise ValueError(
                missing_key_message
                or "POLYMARKET_PRIVATE_KEY is not configured"
            )
        return private_key

    @staticmethod
    def _resolve_proxy_address(proxy_address: Optional[str]) -> Optional[str]:
        if proxy_address:
            return proxy_address
        return os.getenv("POLYMARKET_PROXY_ADDRESS") or POLYMARKET_PROXY_ADDRESS

    @staticmethod
    def _build_clob_client(
        private_key: str,
        proxy_address: Optional[str],
    ) -> ClobClient:
        clob_url = os.getenv("POLYMARKET_CLOB_URL") or POLYMARKET_CLOB_URL
        chain_id = int(os.getenv("POLYMARKET_CHAIN_ID") or POLYMARKET_CHAIN_ID)
        signature_type: Any = (
            os.getenv("POLYMARKET_SIGNATURE_TYPE") or POLYMARKET_SIGNATURE_TYPE
        )
        funder = proxy_address or ""
        return ClobClient(
            host=clob_url,
            key=private_key,
            chain_id=chain_id,
            signature_type=signature_type,
            funder=funder,
        )

    async def get_api_creds(
        self,
        private_key: Optional[str] = None,
        proxy_address: Optional[str] = None,
        missing_key_message: Optional[str] = None,
    ) -> Any:
        resolved_key = self._resolve_private_key(private_key, missing_key_message)
        resolved_proxy = self._resolve_proxy_address(proxy_address)

        if (
            self._api_creds is not None
            and resolved_key == self._current_private_key
            and resolved_proxy == self._current_proxy_address
        ):
            return self._api_creds

        async with self._lock:
            if (
                self._api_creds is not None
                and resolved_key == self._current_private_key
                and resolved_proxy == self._current_proxy_address
            ):
                return self._api_creds

            if (
                self._clob_client is None
                or resolved_key != self._current_private_key
                or resolved_proxy != self._current_proxy_address
            ):
                self._clob_client = self._build_clob_client(
                    resolved_key,
                    resolved_proxy,
                )

            try:
                api_creds = self._clob_client.create_or_derive_api_creds()
                self._clob_client.set_api_creds(api_creds)
            except Exception as exc:
                raise ValueError(
                    f"Failed to derive Polymarket API credentials: {exc}"
                ) from exc

            self._api_creds = api_creds
            self._current_private_key = resolved_key
            self._current_proxy_address = resolved_proxy
            return api_creds

    async def get_clob_client(
        self,
        private_key: Optional[str] = None,
        proxy_address: Optional[str] = None,
        missing_key_message: Optional[str] = None,
    ) -> ClobClient:
        await self.get_api_creds(
            private_key=private_key,
            proxy_address=proxy_address,
            missing_key_message=missing_key_message,
        )
        if self._clob_client is None:
            raise RuntimeError("ClobClient initialization failed")
        return self._clob_client

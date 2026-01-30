"""Polymarket 配置"""

from __future__ import annotations

import os


POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
POLYMARKET_PROXY_ADDRESS = os.getenv("POLYMARKET_PROXY_ADDRESS")
POLYMARKET_CLOB_URL = os.getenv("POLYMARKET_CLOB_URL", "https://clob.polymarket.com")
POLYMARKET_CHAIN_ID = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
POLYMARKET_SIGNATURE_TYPE = os.getenv("POLYMARKET_SIGNATURE_TYPE", "EOA")
POLYMARKET_GAMMA_API_URL = os.getenv(
    "POLYMARKET_GAMMA_API_URL",
    "https://gamma-api.polymarket.com",
)
POLYMARKET_DATA_API_URL = os.getenv(
    "POLYMARKET_DATA_API_URL",
    "https://data-api.polymarket.com",
)
POLYMARKET_WSS_URL = os.getenv(
    "POLYMARKET_WSS_URL",
    "wss://ws-subscriptions-clob.polymarket.com",
)
POLYMARKET_WS_API_KEY = os.getenv("POLYMARKET_WS_API_KEY")
POLYMARKET_WS_API_SECRET = os.getenv("POLYMARKET_WS_API_SECRET")
POLYMARKET_WS_API_PASSPHRASE = os.getenv("POLYMARKET_WS_API_PASSPHRASE")

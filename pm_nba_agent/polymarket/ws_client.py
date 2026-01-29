"""Polymarket WebSocket 客户端"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import threading
from importlib import import_module
from typing import Any, Callable, Optional

WebSocketApp = Any

from .config import POLYMARKET_WSS_URL


logger = logging.getLogger(__name__)


class PolymarketWebSocketClient:
    """Polymarket WebSocket 客户端封装

    提供连接管理、订阅管理、心跳保活功能。
    使用 websocket-client 库的 WebSocketApp 实现。
    """

    MARKET_CHANNEL = "market"
    SUBSCRIBE_TYPE_BOOK = "book"
    HEARTBEAT_INTERVAL = 10
    RECONNECT_BASE_DELAY = 1
    RECONNECT_MAX_DELAY = 30
    MAX_RECONNECT_ATTEMPTS = None

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_passphrase: str,
        wss_url: Optional[str] = None,
        channel: str = MARKET_CHANNEL,
        on_message: Optional[Callable[[Any], Any]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = api_passphrase
        normalized_channel = channel.lower().strip()
        if normalized_channel != self.MARKET_CHANNEL:
            logger.warning("仅支持 market channel，已忽略 channel=%s", normalized_channel)
            normalized_channel = self.MARKET_CHANNEL
        self.channel = normalized_channel

        base_url = (wss_url or POLYMARKET_WSS_URL).rstrip("/")
        self.wss_url = f"{base_url}/ws/{self.channel}"

        self.on_message_callback = on_message
        self.on_error_callback = on_error
        self.on_close_callback = on_close

        self.ws: Optional[WebSocketApp] = None
        self.is_connected = False
        self._subscribed_assets: list[str] = []
        self._subscribe_type = self.SUBSCRIBE_TYPE_BOOK
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_heartbeat = threading.Event()
        self._ws_thread: Optional[threading.Thread] = None
        self._connection_ready = threading.Event()
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._has_initialized_subscription = False
        self._stop_reconnect = threading.Event()
        self._reconnect_attempts = 0

    async def connect(self) -> bool:
        try:
            self._event_loop = asyncio.get_event_loop()
            self.ws = self._create_ws_app()

            logger.info("正在连接 Polymarket WebSocket: %s", self.wss_url)

            self._connection_ready.clear()
            self._stop_reconnect.clear()
            self._ws_thread = threading.Thread(
                target=self._run_forever,
                daemon=True,
            )
            self._ws_thread.start()

            await self._event_loop.run_in_executor(
                None,
                lambda: self._connection_ready.wait(timeout=10),
            )

            if not self.is_connected:
                logger.error("WebSocket 连接超时")
                return False

            return True

        except Exception as exc:
            logger.error("创建 WebSocket 连接失败: %s", exc)
            if self.on_error_callback:
                self.on_error_callback(exc)
            return False

    def _run_forever(self) -> None:
        while not self._stop_reconnect.is_set():
            if not self.ws:
                self.ws = self._create_ws_app()

            try:
                ws = self.ws
                if ws is None:
                    continue
                ws.run_forever()
            except Exception as exc:
                logger.error("WebSocket 运行异常: %s", exc)

            self.is_connected = False
            self._stop_heartbeat.set()

            if self._stop_reconnect.is_set():
                break

            self._reconnect_attempts += 1
            if (
                self.MAX_RECONNECT_ATTEMPTS is not None
                and self._reconnect_attempts > self.MAX_RECONNECT_ATTEMPTS
            ):
                logger.error("WebSocket 重连次数已达上限，停止重连")
                break

            delay = min(
                self.RECONNECT_MAX_DELAY,
                self.RECONNECT_BASE_DELAY * (2 ** (self._reconnect_attempts - 1)),
            )
            logger.warning(
                "WebSocket 连接断开，%ss 后重试 (第 %s 次)",
                delay,
                self._reconnect_attempts,
            )

            self._connection_ready.clear()
            self._has_initialized_subscription = False

            if self._stop_reconnect.wait(timeout=delay):
                break

            self.ws = self._create_ws_app()

    def _create_ws_app(self) -> WebSocketApp:
        ws_module = import_module("websocket")
        ws_app_cls = getattr(ws_module, "WebSocketApp")
        return ws_app_cls(
            self.wss_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

    async def subscribe(
        self,
        markets: Optional[list[str]] = None,
        asset_ids: Optional[list[str]] = None,
        subscribe_type: str = SUBSCRIBE_TYPE_BOOK,
    ) -> bool:
        try:
            if self.channel != self.MARKET_CHANNEL:
                logger.error("仅支持 market channel，user channel 已禁用")
                return False

            if not asset_ids:
                logger.error("market channel 需要 asset_ids")
                return False
            if markets:
                logger.debug("market channel 忽略 markets 参数")

            self._subscribe_type = subscribe_type

            merged_assets = self._subscribed_assets + asset_ids
            self._subscribed_assets = list(dict.fromkeys(merged_assets))

            if self.is_connected and self.ws:
                if not self._has_initialized_subscription:
                    subscribe_msg = {
                        "type": self.MARKET_CHANNEL,
                        "asset_ids": self._subscribed_assets,
                        "assets_ids": self._subscribed_assets,
                        "subscribe_type": subscribe_type,
                    }

                    self._has_initialized_subscription = True
                    logger.info(
                        "已发送初始订阅: %s 个 Token (类型: %s)",
                        len(self._subscribed_assets),
                        subscribe_type,
                    )
                else:
                    subscribe_msg = {
                        "operation": "subscribe",
                        "asset_ids": asset_ids,
                        "assets_ids": asset_ids,
                        "subscribe_type": subscribe_type,
                    }

                    logger.info(
                        "已订阅 %s 个 Token (类型: %s)",
                        len(asset_ids),
                        subscribe_type,
                    )

                logger.debug("订阅消息: %s", json.dumps(subscribe_msg))
                self.ws.send(json.dumps(subscribe_msg))
            else:
                logger.info(
                    "已添加 %s 个 Token 到订阅列表，连接时将自动订阅 (类型: %s)",
                    len(asset_ids),
                    subscribe_type,
                )
            logger.debug("Token IDs: %s", asset_ids)

            return True

        except Exception as exc:
            logger.error("订阅失败: %s", exc)
            if self.on_error_callback:
                self.on_error_callback(exc)
            return False

    async def unsubscribe(
        self,
        markets: Optional[list[str]] = None,
        asset_ids: Optional[list[str]] = None,
    ) -> bool:
        if not self.is_connected or not self.ws:
            self._apply_unsubscribe_locally(markets=markets, asset_ids=asset_ids)
            logger.warning("WebSocket 未连接，已更新本地订阅")
            return False

        try:
            if self.channel != self.MARKET_CHANNEL:
                logger.error("仅支持 market channel，user channel 已禁用")
                return False

            target_assets = asset_ids or self._subscribed_assets
            unsubscribe_msg: dict[str, Any] = {"operation": "unsubscribe"}
            if target_assets:
                unsubscribe_msg["asset_ids"] = target_assets
                unsubscribe_msg["assets_ids"] = target_assets
            self.ws.send(json.dumps(unsubscribe_msg))

            if asset_ids:
                self._subscribed_assets = [
                    asset for asset in self._subscribed_assets if asset not in asset_ids
                ]
            else:
                self._subscribed_assets = []

            logger.info("已取消订阅: %s", asset_ids or "all")
            return True

        except Exception as exc:
            logger.error("取消订阅失败: %s", exc)
            return False

    async def close(self) -> None:
        self.is_connected = False
        self._stop_reconnect.set()
        self._connection_ready.set()
        self._stop_heartbeat.set()

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._stop_heartbeat.set()
            self._heartbeat_thread.join(timeout=2)

        if self.ws:
            try:
                self.ws.close()
            except Exception as exc:
                logger.debug("关闭 WebSocket 时出错: %s", exc)

        if self._ws_thread and self._ws_thread.is_alive():
            self._ws_thread.join(timeout=2)

        self.ws = None
        self._subscribed_assets = []
        self._has_initialized_subscription = False

        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception as exc:
                logger.error("关闭回调执行失败: %s", exc)

        logger.info("Polymarket WebSocket 已关闭")

    def _on_open(self, ws: WebSocketApp) -> None:
        self.is_connected = True
        self._reconnect_attempts = 0
        logger.info("Polymarket WebSocket 连接成功")

        self._connection_ready.set()

        try:
            if self.channel != self.MARKET_CHANNEL:
                logger.error("仅支持 market channel，user channel 已禁用")
                return

            if self._subscribed_assets:
                subscribe_msg = {
                    "type": self.MARKET_CHANNEL,
                    "asset_ids": self._subscribed_assets,
                    "assets_ids": self._subscribed_assets,
                    "subscribe_type": self._subscribe_type,
                }

                ws.send(json.dumps(subscribe_msg))
                self._has_initialized_subscription = True
                logger.info(
                    "已发送初始订阅: %s 个 Token (类型: %s)",
                    len(self._subscribed_assets),
                    self._subscribe_type,
                )

            if not self._heartbeat_thread or not self._heartbeat_thread.is_alive():
                self._stop_heartbeat.clear()
                self._heartbeat_thread = threading.Thread(
                    target=self._heartbeat_loop,
                    args=(ws,),
                    daemon=True,
                )
                self._heartbeat_thread.start()

        except Exception as exc:
            logger.error("发送初始订阅失败: %s", exc)
            if self.on_error_callback:
                self.on_error_callback(exc)

    def _on_message(self, _ws: WebSocketApp, message: Any) -> None:
        try:
            if isinstance(message, (bytes, bytearray)):
                message = message.decode("utf-8", errors="ignore")

            if not isinstance(message, str):
                logger.debug("忽略非文本消息: %s", type(message))
                return

            cleaned = message.strip()
            if not cleaned:
                logger.debug("忽略空消息")
                return

            if not (cleaned.startswith("{") or cleaned.startswith("[")):
                data = {"raw": cleaned}
            else:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    data = {"raw": cleaned}

            if self.on_message_callback:
                try:
                    if inspect.iscoroutinefunction(self.on_message_callback):
                        if self._event_loop and self._event_loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                self.on_message_callback(data),
                                self._event_loop,
                            )
                        else:
                            logger.warning("事件循环不可用，无法调用异步回调")
                    else:
                        self.on_message_callback(data)
                except Exception as exc:
                    logger.error("消息回调处理失败: %s", exc)

        except Exception as exc:
            logger.error("处理消息时出错: %s", exc)

    def _on_error(self, _ws: WebSocketApp, error: Exception) -> None:
        logger.error("WebSocket 错误: %s", error)
        if self.on_error_callback:
            try:
                self.on_error_callback(error)
            except Exception as exc:
                logger.error("错误回调执行失败: %s", exc)

    def _on_close(
        self,
        _ws: WebSocketApp,
        close_status_code: Optional[int],
        close_msg: Optional[str],
    ) -> None:
        self.is_connected = False
        self._has_initialized_subscription = False
        self._connection_ready.clear()
        logger.info(
            "Polymarket WebSocket 连接关闭 (状态码: %s, 消息: %s)",
            close_status_code,
            close_msg,
        )

        self._stop_heartbeat.set()

        if self.on_close_callback:
            try:
                self.on_close_callback()
            except Exception as exc:
                logger.error("关闭回调执行失败: %s", exc)

    def _heartbeat_loop(self, ws: WebSocketApp) -> None:
        self._stop_heartbeat.wait(timeout=self.HEARTBEAT_INTERVAL)

        while not self._stop_heartbeat.is_set() and self.is_connected:
            try:
                ws.send("PING")
                logger.debug("心跳发送成功")
            except Exception as exc:
                logger.error("心跳发送失败: %s", exc)
                break

            self._stop_heartbeat.wait(timeout=self.HEARTBEAT_INTERVAL)

    def get_subscribed_tokens(self) -> list[str]:
        return self._subscribed_assets.copy()

    def is_subscribed(self, token_id: str) -> bool:
        return token_id in self._subscribed_assets

    def _apply_unsubscribe_locally(
        self,
        markets: Optional[list[str]] = None,
        asset_ids: Optional[list[str]] = None,
    ) -> None:
        if self.channel != self.MARKET_CHANNEL:
            return
        if asset_ids:
            self._subscribed_assets = [
                asset for asset in self._subscribed_assets if asset not in asset_ids
            ]
        else:
            self._subscribed_assets = []

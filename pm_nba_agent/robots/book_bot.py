"""BookBot — WebSocket 订阅 Polymarket 订单簿。"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.polymarket.book_stream import PolymarketBookStream
from pm_nba_agent.polymarket.resolver import MarketResolver
from pm_nba_agent.polymarket.models import EventInfo
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot
from .composer import register_robot


@register_robot("book")
class BookBot(BaseRobot):
    """WebSocket 订阅 Polymarket 订单簿，发出 book 更新信号。

    发出信号：polymarket_info, polymarket_book
    """

    input_streams = []
    output_streams = [StreamName.BOOK]

    @property
    def robot_type(self) -> str:
        return "book"

    async def setup(self) -> None:
        self._book_stream: Optional[PolymarketBookStream] = None
        self._consume_task: Optional[asyncio.Task] = None
        self._event_info: Optional[EventInfo] = None
        self._book_stream_maxlen = max(1, int(self.config.get("book_stream_maxlen", 1)))
        self._book_stream_exact_trim = bool(self.config.get("book_stream_exact_trim", True))
        self._drop_stale_updates = bool(self.config.get("book_drop_stale_updates", True))
        self._max_stale_drain = max(0, int(self.config.get("book_max_stale_drain", 0)))

        url = self.config.get("url", "")
        if not url:
            raise ValueError("BookBot: 缺少 url 配置")

        # 解析 Polymarket URL
        self._event_info = await MarketResolver.resolve_event(url)
        if not self._event_info:
            raise ValueError(f"BookBot: 无法解析事件: {url}")

        # 将 polymarket_info 写入 snapshot key（一写多读）
        await self.save_snapshot("polymarket_info", self._event_info.to_dict())

        # 收集 asset_ids
        asset_ids = _collect_asset_ids(self._event_info)
        if not asset_ids:
            raise ValueError("BookBot: 无法获取 token_ids")

        # 启动 WebSocket 订阅
        self._book_stream = PolymarketBookStream()
        started = await self._book_stream.start(asset_ids)
        if not started:
            raise RuntimeError("BookBot: WebSocket 连接失败")

        logger.info("BookBot: WebSocket 已连接, asset_ids={}", asset_ids)

        # 启动消费 queue 的任务
        self._consume_task = asyncio.create_task(self._consume_loop())

    async def teardown(self) -> None:
        if self._consume_task:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
        if self._book_stream:
            try:
                await self._book_stream.close()
            except Exception as exc:
                logger.warning("BookBot: 关闭 WebSocket 异常: {}", exc)

    def get_runtime_metrics(self) -> dict[str, Any]:
        info = {}
        if self._event_info:
            info["event_id"] = self._event_info.event_id
            info["condition_id"] = self._event_info.condition_id
        return info

    async def _consume_loop(self) -> None:
        """从 WebSocket queue 消费订单簿消息并发出信号。"""
        if not self._book_stream:
            return

        queue = self._book_stream.queue
        try:
            while not self._cancelled:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                if self._drop_stale_updates:
                    message = self._take_latest_message(queue, message)

                if not isinstance(message, dict) or not _is_book_payload(message):
                    continue

                # 标准化字段名: buys->bids, sells->asks
                payload = _normalize_book_message(message)
                await self._emit_book_event(SignalType.POLYMARKET_BOOK, payload)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("BookBot: consume_loop 异常: {}", exc)

    async def _emit_book_event(self, signal_type: SignalType, payload: dict[str, Any]) -> None:
        """发送 polymarket_book 到 BOOK stream，按配置裁剪历史长度。"""
        # 与 v1 行为保持一致：缓存最近一条订单簿，供新订阅者立即回放
        await self.save_snapshot("polymarket_book", payload)
        await self.emit(
            StreamName.BOOK,
            signal_type,
            payload,
            maxlen=self._book_stream_maxlen,
            approximate=not self._book_stream_exact_trim,
        )

    def _take_latest_message(self, queue: asyncio.Queue[Any], message: Any) -> Any:
        """在高频场景下仅保留较新的消息，降低排队延迟。"""
        latest = message
        latest_book = message if isinstance(message, dict) and _is_book_payload(message) else None
        backlog = queue.qsize()
        if backlog <= 0:
            return latest_book if latest_book is not None else latest

        # 使用 qsize 快照，避免生产者持续写入导致长时间占用事件循环。
        to_drain = backlog if self._max_stale_drain == 0 else min(backlog, self._max_stale_drain)
        for _ in range(to_drain):
            try:
                latest = queue.get_nowait()
                if isinstance(latest, dict) and _is_book_payload(latest):
                    latest_book = latest
            except asyncio.QueueEmpty:
                break
        return latest_book if latest_book is not None else latest


def _collect_asset_ids(event_info: EventInfo) -> list[str]:
    """从事件信息收集 asset_ids。"""
    token_ids = [token.token_id for token in event_info.tokens if token.token_id]
    if token_ids:
        return list(dict.fromkeys(token_ids))
    if event_info.market_info:
        return [
            token_id
            for token_id in event_info.market_info.clob_token_ids
            if token_id
        ]
    return []


def _normalize_book_message(message: dict[str, Any]) -> dict[str, Any]:
    """标准化订单簿消息字段名。"""
    payload = dict(message)

    # 顶层标准化
    if "buys" in payload and "bids" not in payload:
        payload["bids"] = payload.pop("buys")
    if "sells" in payload and "asks" not in payload:
        payload["asks"] = payload.pop("sells")

    # price_changes 内的标准化
    price_changes = payload.get("price_changes")
    if isinstance(price_changes, list):
        normalized_changes = []
        for change in price_changes:
            if isinstance(change, dict):
                c = dict(change)
                if "buys" in c and "bids" not in c:
                    c["bids"] = c.pop("buys")
                if "sells" in c and "asks" not in c:
                    c["asks"] = c.pop("sells")
                normalized_changes.append(c)
            else:
                normalized_changes.append(change)
        payload["price_changes"] = normalized_changes

    return payload


def _is_book_payload(payload: dict[str, Any]) -> bool:
    """判断消息是否为订单簿更新。"""
    event_type = str(payload.get("event_type", "")).strip().lower()
    if event_type:
        return event_type in {"book", "price_change"}

    if "price_changes" in payload:
        price_changes = payload.get("price_changes")
        return isinstance(price_changes, list) and len(price_changes) > 0

    has_asset = any(
        payload.get(key)
        for key in ("asset_id", "assetId", "token_id", "tokenId")
    )
    has_levels = any(
        isinstance(payload.get(key), list)
        for key in ("bids", "asks", "buys", "sells")
    )
    return bool(has_asset and has_levels)

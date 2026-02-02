"""比赛数据流服务"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Optional

from loguru import logger

from ..models.requests import LiveStreamRequest
from ..models.events import (
    ScoreboardEvent,
    BoxscoreEvent,
    HeartbeatEvent,
    PolymarketInfoEvent,
    PolymarketBookEvent,
    ErrorEvent,
    GameEndEvent,
    AnalysisChunkEvent,
    StrategySignalEvent,
)
from .data_fetcher import DataFetcher
from ...agent import GameAnalyzer, GameContext
from ...nba.team_resolver import get_team_info
from ...parsers.polymarket_parser import PolymarketEventInfo
from ...polymarket.resolver import MarketResolver
from ...polymarket.book_stream import PolymarketBookStream
from ...polymarket.models import (
    EventInfo,
    MarketSnapshot,
    SideData,
    OrderLevel,
    OrderBookContext,
    PositionContext,
)
from ...polymarket.strategies import StrategyRegistry
from ...models.game_data import GameData

@dataclass
class StrategyState:
    """策略执行状态（仅用于信号生成，不执行下单）"""
    strategy_id: str = "merge_long"
    yes_token_id: str = ""
    no_token_id: str = ""
    position: PositionContext = None  # type: ignore
    strategy_params: dict[str, Any] = field(default_factory=dict)
    # 订单簿缓存
    yes_bids: list[OrderLevel] = None  # type: ignore
    yes_asks: list[OrderLevel] = None  # type: ignore
    no_bids: list[OrderLevel] = None  # type: ignore
    no_asks: list[OrderLevel] = None  # type: ignore
    yes_price: float = 0.0
    no_price: float = 0.0

    def __post_init__(self):
        if self.position is None:
            self.position = PositionContext()
        if self.strategy_params is None:
            self.strategy_params = {}
        if self.yes_bids is None:
            self.yes_bids = []
        if self.yes_asks is None:
            self.yes_asks = []
        if self.no_bids is None:
            self.no_bids = []
        if self.no_asks is None:
            self.no_asks = []

    def update_book(self, message: dict[str, Any]) -> None:
        """更新订单簿缓存"""
        event_type = str(message.get("event_type", "")).lower()

        if event_type == "price_change":
            price_changes = message.get("price_changes") or []
            if not isinstance(price_changes, list):
                return

            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                change_asset_id = change.get("asset_id")
                if not change_asset_id:
                    continue

                side = str(change.get("side", "")).upper()
                price = float(change.get("price", 0) or 0)
                size = float(change.get("size", 0) or 0)
                if price <= 0:
                    continue

                if change_asset_id == self.yes_token_id:
                    if side == "BUY":
                        self.yes_bids = self._apply_price_change(self.yes_bids, price, size)
                        self.yes_bids.sort(key=lambda level: level.price, reverse=True)
                    elif side == "SELL":
                        self.yes_asks = self._apply_price_change(self.yes_asks, price, size)
                        self.yes_asks.sort(key=lambda level: level.price)
                elif change_asset_id == self.no_token_id:
                    if side == "BUY":
                        self.no_bids = self._apply_price_change(self.no_bids, price, size)
                        self.no_bids.sort(key=lambda level: level.price, reverse=True)
                    elif side == "SELL":
                        self.no_asks = self._apply_price_change(self.no_asks, price, size)
                        self.no_asks.sort(key=lambda level: level.price)

            self._refresh_prices()
            return

        asset_id = message.get("asset_id")
        if not asset_id:
            return

        bids = message.get("bids") or message.get("buys") or []
        asks = message.get("asks") or message.get("sells") or []

        bid_levels = [OrderLevel.from_raw(b) for b in bids if isinstance(b, dict)]
        ask_levels = [OrderLevel.from_raw(a) for a in asks if isinstance(a, dict)]

        if asset_id == self.yes_token_id:
            if bid_levels:
                self.yes_bids = bid_levels
            if ask_levels:
                self.yes_asks = ask_levels
        elif asset_id == self.no_token_id:
            if bid_levels:
                self.no_bids = bid_levels
            if ask_levels:
                self.no_asks = ask_levels

        self._refresh_prices()

    def _refresh_prices(self) -> None:
        yes_price = self._mid_price(self.yes_bids, self.yes_asks)
        no_price = self._mid_price(self.no_bids, self.no_asks)

        if yes_price > 0:
            if self.yes_price and yes_price != self.yes_price:
                logger.debug(
                    "Polymarket 订单簿价格更新: YES {} {} -> {}",
                    self.yes_token_id,
                    self.yes_price,
                    yes_price,
                )
            self.yes_price = yes_price

        if no_price > 0:
            if self.no_price and no_price != self.no_price:
                logger.debug(
                    "Polymarket 订单簿价格更新: NO {} {} -> {}",
                    self.no_token_id,
                    self.no_price,
                    no_price,
                )
            self.no_price = no_price

    @staticmethod
    def _mid_price(bids: list[OrderLevel], asks: list[OrderLevel]) -> float:
        best_bid = max((level.price for level in bids), default=0.0)
        best_ask = min((level.price for level in asks), default=0.0)
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return best_bid or best_ask

    @staticmethod
    def _apply_price_change(
        levels: list[OrderLevel],
        price: float,
        size: float,
    ) -> list[OrderLevel]:
        level_map = {level.price: level.size for level in levels}
        if size <= 0:
            level_map.pop(price, None)
        else:
            level_map[price] = size
        return [OrderLevel(price=p, size=s) for p, s in level_map.items()]

    def build_snapshot(self) -> Optional[MarketSnapshot]:
        """构建市场快照"""
        if not self.yes_price and not self.no_price:
            return None

        yes_data = SideData(
            token_id=self.yes_token_id,
            price=self.yes_price,
            bids=self.yes_bids.copy(),
            asks=self.yes_asks.copy(),
        )
        no_data = SideData(
            token_id=self.no_token_id,
            price=self.no_price,
            bids=self.no_bids.copy(),
            asks=self.no_asks.copy(),
        )

        return MarketSnapshot(yes_data=yes_data, no_data=no_data)


@dataclass
class StreamState:
    """流状态"""
    game_id: str
    last_action_number: int = 0
    is_game_ended: bool = False
    strategy: Optional[StrategyState] = None


class GameStreamService:
    """比赛数据流服务"""

    def __init__(self, fetcher: DataFetcher, analyzer: Optional[GameAnalyzer] = None):
        self._fetcher = fetcher
        self._analyzer = analyzer

    async def create_stream(
        self,
        request: LiveStreamRequest
    ) -> AsyncGenerator[str, None]:
        """
        创建 SSE 数据流

        Args:
            request: 请求参数

        Yields:
            SSE 格式的事件字符串
        """
        # 1. 解析 URL
        url_result = await self._fetcher.parse_url(request.url)
        if not url_result.success:
            yield ErrorEvent.create(
                code="URL_PARSE_ERROR",
                message=url_result.error or "URL 解析失败",
                recoverable=False
            ).to_sse()
            return

        event_info = url_result.data
        if event_info is None:
            yield ErrorEvent.create(
                code="URL_PARSE_ERROR",
                message="URL 解析失败",
                recoverable=False
            ).to_sse()
            return
        if not isinstance(event_info, PolymarketEventInfo):
            yield ErrorEvent.create(
                code="URL_PARSE_ERROR",
                message="URL 解析失败",
                recoverable=False
            ).to_sse()
            return

        polymarket_book_stream: Optional[PolymarketBookStream] = None
        polymarket_book_queue: Optional[asyncio.Queue[dict[str, Any]]] = None
        strategy_state: Optional[StrategyState] = None
        event_queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        book_task: Optional[asyncio.Task[None]] = None

        async def _emit(event: str) -> None:
            await event_queue.put(event)

        async def _consume_polymarket_book_queue(
            queue: asyncio.Queue[dict[str, Any]],
            strategy: Optional[StrategyState],
        ) -> None:
            try:
                while True:
                    message = await queue.get()
                    for event in await _build_polymarket_events(message, strategy):
                        await event_queue.put(event)
            except asyncio.CancelledError:
                return

        async def _main_loop() -> None:
            nonlocal polymarket_book_stream, polymarket_book_queue, strategy_state, book_task

            try:
                try:
                    logger.info("Polymarket 解析开始: {}", request.url)
                    polymarket_event = await MarketResolver.resolve_event(request.url)
                    if polymarket_event:
                        logger.info(
                            "Polymarket 解析完成: "
                            "event_id={} "
                            "condition_id={} "
                            "tokens={} "
                            "has_market_info={} "
                            "has_event_data={}",
                            polymarket_event.event_id,
                            polymarket_event.condition_id,
                            len(polymarket_event.tokens),
                            polymarket_event.market_info is not None,
                            polymarket_event.event_data is not None,
                        )
                        await _emit(
                            PolymarketInfoEvent.create(
                                polymarket_event.to_dict()
                            ).to_sse()
                        )

                        asset_ids = _collect_polymarket_asset_ids(polymarket_event)
                        if asset_ids:
                            polymarket_book_stream = PolymarketBookStream()
                            started = await polymarket_book_stream.start(asset_ids)
                            if started:
                                polymarket_book_queue = polymarket_book_stream.queue
                                logger.info(
                                    "Polymarket WebSocket 已订阅 book: "
                                    "tokens={}",
                                    len(asset_ids),
                                )

                                # 初始化策略状态（仅用于信号生成）
                                strategy_state = _init_strategy_state(
                                    polymarket_event,
                                )
                                if strategy_state:
                                    logger.info(
                                        "策略已初始化: {}, YES={}..., NO={}...",
                                        strategy_state.strategy_id,
                                        strategy_state.yes_token_id[:8],
                                        strategy_state.no_token_id[:8],
                                    )
                                if book_task is None and polymarket_book_queue is not None:
                                    book_task = asyncio.create_task(
                                        _consume_polymarket_book_queue(
                                            polymarket_book_queue,
                                            strategy_state,
                                        )
                                    )
                            else:
                                logger.warning("Polymarket WebSocket 订阅失败")
                    else:
                        logger.warning("Polymarket 解析失败: 无返回结果")
                        await _emit(
                            ErrorEvent.create(
                                code="POLYMARKET_INFO_MISSING",
                                message="未获取到 Polymarket 市场信息",
                                recoverable=True,
                            ).to_sse()
                        )
                except Exception as exc:
                    logger.error("Polymarket 解析异常: {}", exc)
                    await _emit(
                        ErrorEvent.create(
                            code="POLYMARKET_INFO_ERROR",
                            message=str(exc),
                            recoverable=True,
                        ).to_sse()
                    )

                # 2. 查找比赛（未开赛时保持连接并提示）
                pending_notice_sent = False
                game_id: Optional[str] = None
                while game_id is None:
                    game_result = await self._fetcher.find_game(
                        event_info.team1_abbr,
                        event_info.team2_abbr,
                        event_info.game_date
                    )
                    if game_result.success:
                        game_id = game_result.data
                        break

                    if _is_future_or_today(event_info.game_date):
                        if request.include_scoreboard and not pending_notice_sent:
                            placeholder = _build_placeholder_scoreboard(event_info)
                            status_message = _build_status_message(placeholder.get("status", ""))
                            await _emit(
                                ScoreboardEvent.create(
                                    game_id=placeholder["game_id"],
                                    status=placeholder["status"],
                                    period=placeholder["period"],
                                    game_clock=placeholder["game_clock"],
                                    home_team=placeholder["home_team"],
                                    away_team=placeholder["away_team"],
                                    status_message=status_message,
                                ).to_sse()
                            )
                            pending_notice_sent = True

                        await _emit(HeartbeatEvent.create().to_sse())
                        await asyncio.sleep(request.poll_interval)
                        continue

                    await _emit(
                        ErrorEvent.create(
                            code="GAME_NOT_FOUND",
                            message=game_result.error or "比赛未找到",
                            recoverable=False
                        ).to_sse()
                    )
                    return
                if game_id is None:
                    return

                state = StreamState(game_id=game_id)

                # 创建比赛上下文
                context = GameContext(game_id=game_id)

                # 3. 进入轮询循环
                while not state.is_game_ended:
                    try:
                        # 获取并推送各类数据
                        async for event in self._fetch_and_emit(
                            request,
                            state,
                            context,
                        ):
                            await _emit(event)

                        if state.is_game_ended:
                            break

                        # 触发 AI 分析
                        if request.enable_analysis and self._analyzer is not None:
                            # 使用请求参数中的分析间隔
                            should_run = self._analyzer.is_enabled() and context.should_analyze(
                                normal_interval=request.analysis_interval,
                                event_interval=min(request.analysis_interval / 2, 15.0),
                            )
                            if should_run:
                                round_number = context.analysis_round + 1
                                async for chunk in self._analyzer.analyze_stream(context):
                                    await _emit(
                                        AnalysisChunkEvent.create(
                                            game_id=game_id,
                                            chunk=chunk,
                                            is_final=False,
                                            round_number=round_number,
                                        ).to_sse()
                                    )
                                # 发送分析结束标记
                                await _emit(
                                    AnalysisChunkEvent.create(
                                        game_id=game_id,
                                        chunk="",
                                        is_final=True,
                                        round_number=round_number,
                                    ).to_sse()
                                )

                        # 发送心跳
                        await _emit(HeartbeatEvent.create().to_sse())

                        # 等待下一次轮询
                        await asyncio.sleep(request.poll_interval)

                    except asyncio.CancelledError:
                        # 客户端断开连接
                        break
                    except Exception as e:
                        # 发送可恢复错误，继续轮询
                        await _emit(
                            ErrorEvent.create(
                                code="FETCH_ERROR",
                                message=str(e),
                                recoverable=True
                            ).to_sse()
                        )
                        await asyncio.sleep(request.poll_interval)
            finally:
                if book_task:
                    book_task.cancel()
                    try:
                        await book_task
                    except asyncio.CancelledError:
                        pass
                if polymarket_book_stream:
                    await polymarket_book_stream.close()
                await event_queue.put(None)

        main_task = asyncio.create_task(_main_loop())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                pass

    async def _fetch_and_emit(
        self,
        request: LiveStreamRequest,
        state: StreamState,
        context: GameContext,
    ) -> AsyncGenerator[str, None]:
        """获取数据并生成事件"""

        # 获取比分板数据
        if request.include_scoreboard:
            scoreboard_result = await self._fetcher.get_scoreboard(state.game_id)
            if scoreboard_result.success:
                summary = scoreboard_result.data
                if summary is None or not isinstance(summary, dict):
                    yield ErrorEvent.create(
                        code="SCOREBOARD_ERROR",
                        message="获取比分失败",
                        recoverable=True
                    ).to_sse()
                    return
                status_message = _build_status_message(summary.get("status", ""))
                scoreboard_data = {
                    'game_id': summary['game_id'],
                    'status': summary['status'],
                    'period': summary['period'],
                    'game_clock': summary['game_clock'],
                    'home_team': {
                        'name': summary['home_team']['name'],
                        'abbreviation': summary['home_team']['abbreviation'],
                        'score': summary['home_team']['score'],
                    },
                    'away_team': {
                        'name': summary['away_team']['name'],
                        'abbreviation': summary['away_team']['abbreviation'],
                        'score': summary['away_team']['score'],
                    },
                    'status_message': status_message,
                }

                # 更新上下文
                context.update_scoreboard(scoreboard_data)

                yield ScoreboardEvent.create(
                    game_id=summary['game_id'],
                    status=summary['status'],
                    period=summary['period'],
                    game_clock=summary['game_clock'],
                    home_team=scoreboard_data['home_team'],
                    away_team=scoreboard_data['away_team'],
                    status_message=status_message,
                ).to_sse()

                # 检测比赛结束
                if summary['status'] == 'Final':
                    state.is_game_ended = True
                    yield GameEndEvent.create(
                        game_id=state.game_id,
                        final_score_home=summary['home_team']['score'],
                        final_score_away=summary['away_team']['score'],
                        home_team_name=summary['home_team']['name'],
                        away_team_name=summary['away_team']['name'],
                    ).to_sse()
                    return
            else:
                yield ErrorEvent.create(
                    code="SCOREBOARD_ERROR",
                    message=scoreboard_result.error or "获取比分失败",
                    recoverable=True
                ).to_sse()

        # 获取详细统计数据
        if request.include_boxscore:
            boxscore_result = await self._fetcher.get_boxscore(state.game_id)
            if boxscore_result.success:
                game_data = boxscore_result.data
                if game_data is None or not isinstance(game_data, GameData):
                    yield ErrorEvent.create(
                        code="BOXSCORE_ERROR",
                        message="获取统计失败",
                        recoverable=True
                    ).to_sse()
                    return
                boxscore_dict = game_data.to_dict()

                # 更新上下文
                context.update_boxscore(boxscore_dict)

                yield BoxscoreEvent.create(boxscore_dict).to_sse()

                # 如果没有 scoreboard 数据，也检测比赛结束
                if not request.include_scoreboard:
                    if game_data.game_info.game_status_code == 3:
                        state.is_game_ended = True
                        yield GameEndEvent.create(
                            game_id=state.game_id,
                            final_score_home=game_data.home_team.score,
                            final_score_away=game_data.away_team.score,
                            home_team_name=game_data.home_team.name,
                            away_team_name=game_data.away_team.name,
                        ).to_sse()
                        return
            else:
                yield ErrorEvent.create(
                    code="BOXSCORE_ERROR",
                    message=boxscore_result.error or "获取统计失败",
                    recoverable=True
                ).to_sse()

        # 获取逐回合数据（增量），仅用于上下文分析，不推送给前端
        if request.include_playbyplay:
            if state.last_action_number == 0:
                # 首次获取，使用 limit
                pbp_result = await self._fetcher.get_playbyplay(
                    state.game_id,
                    request.playbyplay_limit
                )
            else:
                # 增量获取
                pbp_result = await self._fetcher.get_playbyplay_since(
                    state.game_id,
                    state.last_action_number
                )

            if pbp_result.success:
                actions = pbp_result.data
                if actions:
                    # 更新最后事件编号
                    state.last_action_number = max(
                        a['action_number'] for a in actions
                    )

                    # 更新上下文
                    context.update_playbyplay(actions)
            else:
                yield ErrorEvent.create(
                    code="PLAYBYPLAY_ERROR",
                    message=pbp_result.error or "获取逐回合数据失败",
                    recoverable=True
                ).to_sse()

        return


def _build_status_message(status: str) -> Optional[str]:
    if not status:
        return None

    normalized = status.lower()
    if "scheduled" in normalized or "pre" in normalized or "未开始" in status:
        return "比赛尚未开始，系统将保持连接并在开赛前开始推送实时数据。"

    return None


def _is_future_or_today(game_date: str) -> bool:
    try:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    except ValueError:
        return False

    return target_date >= datetime.utcnow().date()


def _build_placeholder_scoreboard(event_info: PolymarketEventInfo) -> dict:
    away_abbr = event_info.team1_abbr
    home_abbr = event_info.team2_abbr
    away_team = get_team_info(away_abbr)
    home_team = get_team_info(home_abbr)

    return {
        "game_id": f"pending-{away_abbr}-{home_abbr}-{event_info.game_date}",
        "status": "Scheduled",
        "period": 0,
        "game_clock": "",
        "home_team": {
            "name": home_team.full_name if home_team else home_abbr,
            "abbreviation": home_abbr,
            "score": 0,
        },
        "away_team": {
            "name": away_team.full_name if away_team else away_abbr,
            "abbreviation": away_abbr,
            "score": 0,
        },
    }


def _collect_polymarket_asset_ids(event_info: EventInfo) -> list[str]:
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


def _init_strategy_state(
    event_info: EventInfo,
    *,
    strategy_id: str = "merge_long",
    strategy_params: Optional[dict[str, Any]] = None,
) -> Optional[StrategyState]:
    """从事件信息初始化策略状态（仅用于信号生成）"""
    tokens = event_info.tokens
    if len(tokens) < 2:
        return None

    # 根据 outcome 识别 YES/NO token
    yes_token_id = ""
    no_token_id = ""

    for token in tokens:
        outcome = token.outcome.upper() if token.outcome else ""
        if outcome in ("YES", "UP"):
            yes_token_id = token.token_id
        elif outcome in ("NO", "DOWN"):
            no_token_id = token.token_id

    # 如果无法识别，按顺序使用前两个
    if not yes_token_id and len(tokens) >= 1:
        yes_token_id = tokens[0].token_id
    if not no_token_id and len(tokens) >= 2:
        no_token_id = tokens[1].token_id

    if not yes_token_id or not no_token_id:
        return None

    normalized_strategy_id = str(strategy_id or "merge_long").strip() or "merge_long"

    return StrategyState(
        strategy_id=normalized_strategy_id,
        yes_token_id=yes_token_id,
        no_token_id=no_token_id,
        strategy_params=strategy_params or {},
    )


async def _drain_polymarket_book_queue(
    queue: asyncio.Queue[dict[str, Any]],
    strategy_state: Optional[StrategyState] = None,
) -> AsyncGenerator[str, None]:
    """处理订单簿队列，执行策略并推送事件"""
    while True:
        try:
            message = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        for event in await _build_polymarket_events(message, strategy_state):
            yield event


async def _build_polymarket_events(
    message: Any,
    strategy_state: Optional[StrategyState] = None,
) -> list[str]:
    payload: dict[str, Any]
    if isinstance(message, dict):
        payload = message
    else:
        payload = {"raw": message}

    event_type = ""
    if isinstance(payload, dict):
        if "bids" not in payload and "buys" in payload:
            payload = {**payload, "bids": payload.get("buys")}
        if "asks" not in payload and "sells" in payload:
            payload = {**payload, "asks": payload.get("sells")}
        event_type = str(payload.get("event_type", "")).lower()

    snapshot: Optional[MarketSnapshot] = None
    if strategy_state and isinstance(payload, dict):
        strategy_state.update_book(payload)
        snapshot = strategy_state.build_snapshot()

        if event_type == "price_change":
            events: list[str] = []
            price_changes = payload.get("price_changes") or []
            if not isinstance(price_changes, list):
                price_changes = []

            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                change_asset_id = change.get("asset_id")
                if not change_asset_id:
                    continue

                if change_asset_id == strategy_state.yes_token_id:
                    bids = [
                        {"price": str(level.price), "size": str(level.size)}
                        for level in strategy_state.yes_bids
                    ]
                    asks = [
                        {"price": str(level.price), "size": str(level.size)}
                        for level in strategy_state.yes_asks
                    ]
                elif change_asset_id == strategy_state.no_token_id:
                    bids = [
                        {"price": str(level.price), "size": str(level.size)}
                        for level in strategy_state.no_bids
                    ]
                    asks = [
                        {"price": str(level.price), "size": str(level.size)}
                        for level in strategy_state.no_asks
                    ]
                else:
                    bids = []
                    asks = []

                price_payload = {
                    "event_type": "price_change",
                    "asset_id": change_asset_id,
                    "bids": bids,
                    "asks": asks,
                    "price_change": change,
                    "timestamp": payload.get("timestamp"),
                    "market": payload.get("market"),
                }
                events.append(PolymarketBookEvent.create(price_payload).to_sse())

            # price_change 事件也执行策略
            if events:
                signal_event = await _execute_strategy(message, strategy_state, snapshot=snapshot)
                if signal_event:
                    events.append(signal_event)
                return events

    events = [PolymarketBookEvent.create(payload).to_sse()]

    if strategy_state and isinstance(message, dict):
        signal_event = await _execute_strategy(message, strategy_state, snapshot=snapshot)
        if signal_event:
            events.append(signal_event)

    return events


async def _execute_strategy(
    message: dict[str, Any],
    strategy_state: StrategyState,
    snapshot: Optional[MarketSnapshot] = None,
) -> Optional[str]:
    """执行策略并返回信号事件（仅生成信号，不执行下单）"""
    if snapshot is None:
        # 更新订单簿
        strategy_state.update_book(message)

        # 构建快照
        snapshot = strategy_state.build_snapshot()
    if snapshot is None:
        return None

    # 获取策略
    strategy = StrategyRegistry.get(strategy_state.strategy_id)
    if strategy is None:
        return None

    # 构建上下文
    order_book = OrderBookContext.from_snapshot(snapshot)
    params = strategy_state.strategy_params or {}

    # 生成信号
    try:
        signal = strategy.generate_signal(
            snapshot=snapshot,
            order_book=order_book,
            position=strategy_state.position,
            params=params,
        )
    except Exception as exc:
        logger.warning("策略执行失败: {}", exc)
        return None

    if signal is None:
        return None

    # 构建市场数据
    market_data = {
        "yes_price": snapshot.yes_data.price,
        "no_price": snapshot.no_data.price,
        "price_sum": snapshot.price_sum,
        "yes_best_bid": snapshot.yes_data.best_bid,
        "yes_best_ask": snapshot.yes_data.best_ask,
        "no_best_bid": snapshot.no_data.best_bid,
        "no_best_ask": snapshot.no_data.best_ask,
    }

    # 构建持仓数据
    position_data = strategy_state.position.to_dict()

    # 仅生成信号，不执行下单
    return StrategySignalEvent.create(
        signal_type=signal.signal_type.value,
        reason=signal.reason,
        market=market_data,
        position=position_data,
        execution=None,
        strategy_id=strategy_state.strategy_id,
        yes_size=signal.yes_size,
        no_size=signal.no_size,
        yes_price=signal.yes_price,
        no_price=signal.no_price,
        metadata=signal.metadata,
    ).to_sse()

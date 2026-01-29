"""比赛数据流服务"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

from ..models.requests import LiveStreamRequest
from ..models.events import (
    SSEEvent,
    ScoreboardEvent,
    BoxscoreEvent,
    PlayByPlayEvent,
    HeartbeatEvent,
    ErrorEvent,
    GameEndEvent,
    AnalysisChunkEvent,
)
from .data_fetcher import DataFetcher
from ...agent import GameAnalyzer, GameContext
from ...nba.team_resolver import get_team_info
from ...parsers.polymarket_parser import PolymarketEventInfo
from ...models.game_data import GameData


@dataclass
class StreamState:
    """流状态"""
    game_id: str
    last_action_number: int = 0
    is_game_ended: bool = False


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
                    yield ScoreboardEvent.create(
                        game_id=placeholder["game_id"],
                        status=placeholder["status"],
                        period=placeholder["period"],
                        game_clock=placeholder["game_clock"],
                        home_team=placeholder["home_team"],
                        away_team=placeholder["away_team"],
                        status_message=status_message,
                    ).to_sse()
                    pending_notice_sent = True

                yield HeartbeatEvent.create().to_sse()
                await asyncio.sleep(request.poll_interval)
                continue

            yield ErrorEvent.create(
                code="GAME_NOT_FOUND",
                message=game_result.error or "比赛未找到",
                recoverable=False
            ).to_sse()
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
                async for event in self._fetch_and_emit(request, state, context):
                    yield event

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
                            yield AnalysisChunkEvent.create(
                                game_id=game_id,
                                chunk=chunk,
                                is_final=False,
                                round_number=round_number,
                            ).to_sse()
                        # 发送分析结束标记
                        yield AnalysisChunkEvent.create(
                            game_id=game_id,
                            chunk="",
                            is_final=True,
                            round_number=round_number,
                        ).to_sse()

                # 发送心跳
                yield HeartbeatEvent.create().to_sse()

                # 等待下一次轮询
                await asyncio.sleep(request.poll_interval)

            except asyncio.CancelledError:
                # 客户端断开连接
                break
            except Exception as e:
                # 发送可恢复错误，继续轮询
                yield ErrorEvent.create(
                    code="FETCH_ERROR",
                    message=str(e),
                    recoverable=True
                ).to_sse()
                await asyncio.sleep(request.poll_interval)

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

        # 获取逐回合数据（增量）
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

                    yield PlayByPlayEvent.create(
                        game_id=state.game_id,
                        actions=actions
                    ).to_sse()
            else:
                yield ErrorEvent.create(
                    code="PLAYBYPLAY_ERROR",
                    message=pbp_result.error or "获取逐回合数据失败",
                    recoverable=True
                ).to_sse()


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

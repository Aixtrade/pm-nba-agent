"""比赛数据流服务"""

import asyncio
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
)
from .data_fetcher import DataFetcher


@dataclass
class StreamState:
    """流状态"""
    game_id: str
    last_action_number: int = 0
    is_game_ended: bool = False


class GameStreamService:
    """比赛数据流服务"""

    def __init__(self, fetcher: DataFetcher):
        self._fetcher = fetcher

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

        # 2. 查找比赛
        game_result = await self._fetcher.find_game(
            event_info.team1_abbr,
            event_info.team2_abbr,
            event_info.game_date
        )
        if not game_result.success:
            yield ErrorEvent.create(
                code="GAME_NOT_FOUND",
                message=game_result.error or "比赛未找到",
                recoverable=False
            ).to_sse()
            return

        game_id = game_result.data
        state = StreamState(game_id=game_id)

        # 3. 进入轮询循环
        while not state.is_game_ended:
            try:
                # 获取并推送各类数据
                async for event in self._fetch_and_emit(request, state):
                    yield event

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
        state: StreamState
    ) -> AsyncGenerator[str, None]:
        """获取数据并生成事件"""

        # 获取比分板数据
        if request.include_scoreboard:
            scoreboard_result = await self._fetcher.get_scoreboard(state.game_id)
            if scoreboard_result.success:
                summary = scoreboard_result.data
                yield ScoreboardEvent.create(
                    game_id=summary['game_id'],
                    status=summary['status'],
                    period=summary['period'],
                    game_clock=summary['game_clock'],
                    home_team={
                        'name': summary['home_team']['name'],
                        'abbreviation': summary['home_team']['abbreviation'],
                        'score': summary['home_team']['score'],
                    },
                    away_team={
                        'name': summary['away_team']['name'],
                        'abbreviation': summary['away_team']['abbreviation'],
                        'score': summary['away_team']['score'],
                    },
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
                yield BoxscoreEvent.create(game_data.to_dict()).to_sse()

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

"""异步数据获取服务"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional, Any

from ...parsers.polymarket_parser import parse_polymarket_url, PolymarketEventInfo
from ...nba.game_finder import find_game_by_teams_and_date
from ...nba.live_stats import get_live_game_data, get_game_summary
from ...nba.playbyplay import get_playbyplay_data, get_playbyplay_since
from ...models.game_data import GameData


@dataclass
class FetchResult:
    """数据获取结果"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


class DataFetcher:
    """异步数据获取器，将同步 NBA API 调用转为异步"""

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    async def parse_url(self, url: str) -> FetchResult:
        """异步解析 Polymarket URL"""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self._executor,
                parse_polymarket_url,
                url
            )
            if result is None:
                return FetchResult(
                    success=False,
                    error="无法解析 URL，请检查格式是否正确"
                )
            return FetchResult(success=True, data=result)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def find_game(
        self,
        team1_abbr: str,
        team2_abbr: str,
        game_date: str
    ) -> FetchResult:
        """异步查找比赛 ID"""
        loop = asyncio.get_event_loop()
        try:
            game_id = await loop.run_in_executor(
                self._executor,
                find_game_by_teams_and_date,
                team1_abbr,
                team2_abbr,
                game_date,
                True  # use_live_api
            )
            if game_id is None:
                return FetchResult(
                    success=False,
                    error=f"未找到 {team1_abbr} vs {team2_abbr} 在 {game_date} 的比赛"
                )
            return FetchResult(success=True, data=game_id)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def get_boxscore(self, game_id: str) -> FetchResult:
        """异步获取详细统计数据"""
        loop = asyncio.get_event_loop()
        try:
            game_data = await loop.run_in_executor(
                self._executor,
                get_live_game_data,
                game_id
            )
            if game_data is None:
                return FetchResult(
                    success=False,
                    error=f"无法获取比赛 {game_id} 的详细数据"
                )
            return FetchResult(success=True, data=game_data)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def get_scoreboard(self, game_id: str) -> FetchResult:
        """异步获取比分板数据"""
        loop = asyncio.get_event_loop()
        try:
            summary = await loop.run_in_executor(
                self._executor,
                get_game_summary,
                game_id
            )
            if summary is None:
                return FetchResult(
                    success=False,
                    error=f"无法获取比赛 {game_id} 的比分数据"
                )
            return FetchResult(success=True, data=summary)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def get_playbyplay(self, game_id: str, limit: int = 20) -> FetchResult:
        """异步获取逐回合数据"""
        loop = asyncio.get_event_loop()
        try:
            actions = await loop.run_in_executor(
                self._executor,
                get_playbyplay_data,
                game_id,
                limit
            )
            if actions is None:
                return FetchResult(
                    success=False,
                    error=f"无法获取比赛 {game_id} 的逐回合数据"
                )
            return FetchResult(success=True, data=actions)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    async def get_playbyplay_since(
        self,
        game_id: str,
        since_action_number: int
    ) -> FetchResult:
        """异步获取增量逐回合数据"""
        loop = asyncio.get_event_loop()
        try:
            actions = await loop.run_in_executor(
                self._executor,
                get_playbyplay_since,
                game_id,
                since_action_number
            )
            if actions is None:
                return FetchResult(
                    success=False,
                    error=f"无法获取比赛 {game_id} 的增量数据"
                )
            return FetchResult(success=True, data=actions)
        except Exception as e:
            return FetchResult(success=False, error=str(e))

    def shutdown(self):
        """关闭线程池"""
        self._executor.shutdown(wait=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

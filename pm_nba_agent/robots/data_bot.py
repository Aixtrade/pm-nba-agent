"""NBADataBot — 轮询 NBA API 获取比分/统计数据。"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.agent import GameContext
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot
from .composer import register_robot


@register_robot("nba_data")
class NBADataBot(BaseRobot):
    """轮询 NBA API 获取比分、统计、逐回合数据。

    发出信号：scoreboard, boxscore, game_end
    """

    input_streams = []
    output_streams = [StreamName.NBA_DATA]

    @property
    def robot_type(self) -> str:
        return "nba_data"

    async def setup(self) -> None:
        self._fetcher = DataFetcher(max_workers=3)
        self._poll_interval = float(self.config.get("poll_interval", 10.0))
        self._include_scoreboard = bool(self.config.get("include_scoreboard", True))
        self._include_boxscore = bool(self.config.get("include_boxscore", True))
        self._game_id: str | None = None
        self._game_ended = False
        self._last_action_number = 0
        self._context = GameContext(game_id="")

        self._poll_task = asyncio.create_task(self._poll_loop())

    async def teardown(self) -> None:
        if hasattr(self, "_poll_task"):
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if hasattr(self, "_fetcher"):
            self._fetcher.shutdown()

    def get_runtime_metrics(self) -> dict[str, Any]:
        return {
            "game_id": self._game_id,
            "game_ended": self._game_ended,
            "poll_interval": self._poll_interval,
        }

    async def _poll_loop(self) -> None:
        """主轮询循环：解析 URL -> 查找比赛 -> 轮询数据。"""
        try:
            # 1. 解析 Polymarket URL 获取队伍信息
            url = self.config.get("url", "")
            url_result = await self._fetcher.parse_url(url)
            if not url_result.success or not url_result.data:
                logger.error("NBADataBot: URL 解析失败: {}", url_result.error)
                return

            event_info = url_result.data
            team1 = getattr(event_info, "team1_abbr", None) or ""
            team2 = getattr(event_info, "team2_abbr", None) or ""
            game_date = getattr(event_info, "game_date", None)

            if not team1 or not team2:
                # 尝试从 event_id 解析队伍信息
                event_id = getattr(event_info, "event_id", "") or ""
                parts = event_id.split("-")
                # 格式: nba-{team1}-{team2}-{date}
                if len(parts) >= 4 and parts[0].lower() == "nba":
                    team1 = parts[1].upper()
                    team2 = parts[2].upper()
                    game_date = "-".join(parts[3:])

            if not team1 or not team2:
                logger.error("NBADataBot: 无法从 URL 提取队伍信息")
                return

            # 2. 查找比赛 ID（可能需要等待开赛）
            await self._find_game_with_retry(team1, team2, game_date)
            if not self._game_id or self._cancelled:
                return

            self._context = GameContext(game_id=self._game_id)

            # 3. 进入数据轮询循环
            while not self._cancelled and not self._game_ended:
                await self._fetch_and_emit()
                if self._game_ended:
                    break
                await asyncio.sleep(self._poll_interval)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("NBADataBot poll_loop 异常: {}", exc)

    async def _find_game_with_retry(
        self, team1: str, team2: str, game_date: str | None
    ) -> None:
        """查找比赛 ID，找不到则等待重试。"""
        max_retries = 60  # 最多等待 10 分钟
        for attempt in range(max_retries):
            if self._cancelled:
                return
            result = await self._fetcher.find_game(team1, team2, game_date)
            if result.success and result.data:
                self._game_id = str(result.data)
                logger.info("NBADataBot: 找到比赛 game_id={}", self._game_id)
                return
            if attempt < max_retries - 1:
                logger.info(
                    "NBADataBot: 未找到比赛 {}-vs-{}，等待 10 秒后重试 ({}/{})",
                    team1, team2, attempt + 1, max_retries,
                )
                await asyncio.sleep(10.0)

        logger.error("NBADataBot: 无法找到比赛 {}-vs-{}", team1, team2)

    async def _fetch_and_emit(self) -> None:
        """轮询一次 NBA 数据并发出信号。"""
        if not self._game_id:
            return

        # Scoreboard
        if self._include_scoreboard:
            result = await self._fetcher.get_scoreboard(self._game_id)
            if result.success and result.data:
                data = result.data if isinstance(result.data, dict) else {}
                await self.emit(StreamName.NBA_DATA, SignalType.SCOREBOARD, data)

                # 更新 context
                self._context.update_scoreboard(data)

                # 检测比赛结束
                status = str(data.get("status", "")).lower()
                if status == "final":
                    self._game_ended = True
                    home = data.get("home_team", {})
                    away = data.get("away_team", {})
                    await self.emit(StreamName.NBA_DATA, SignalType.GAME_END, {
                        "game_id": self._game_id,
                        "final_score": {
                            "home": home.get("score", 0) if isinstance(home, dict) else 0,
                            "away": away.get("score", 0) if isinstance(away, dict) else 0,
                        },
                        "home_team": home.get("name", "") if isinstance(home, dict) else "",
                        "away_team": away.get("name", "") if isinstance(away, dict) else "",
                    })

        # Boxscore
        if self._include_boxscore:
            result = await self._fetcher.get_boxscore(self._game_id)
            if result.success and result.data:
                data = result.data
                if hasattr(data, "to_dict"):
                    data = data.to_dict()
                if isinstance(data, dict):
                    await self.emit(StreamName.NBA_DATA, SignalType.BOXSCORE, data)
                    self._context.update_boxscore(data)

        # Play-by-play（增量，仅更新 context）
        try:
            if self._last_action_number == 0:
                pbp_result = await self._fetcher.get_playbyplay(self._game_id, limit=20)
            else:
                pbp_result = await self._fetcher.get_playbyplay_since(
                    self._game_id, self._last_action_number
                )
            if pbp_result.success and pbp_result.data:
                actions = pbp_result.data
                if isinstance(actions, list) and actions:
                    for action in actions:
                        if isinstance(action, dict):
                            action_num = action.get("actionNumber", 0)
                            if isinstance(action_num, int) and action_num > self._last_action_number:
                                self._last_action_number = action_num
                    self._context.update_playbyplay(actions)
        except Exception as exc:
            logger.debug("NBADataBot: play-by-play 获取异常: {}", exc)

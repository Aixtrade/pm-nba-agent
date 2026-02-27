"""AnalysisBot — AI 分析比赛局势。"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.agent import GameAnalyzer, GameContext
from pm_nba_agent.shared.channels import SignalType, StreamName

from .base import BaseRobot, Signal, _now_iso
from .composer import register_robot


@register_robot("analysis")
class AnalysisBot(BaseRobot):
    """收到 scoreboard/boxscore 时更新 GameContext，定期触发 AI 分析。

    接收信号：scoreboard, boxscore（从 NBADataBot）
    发出信号：analysis_chunk
    """

    input_streams = [StreamName.NBA_DATA]
    output_streams = [StreamName.ANALYSIS]

    @property
    def robot_type(self) -> str:
        return "analysis"

    async def setup(self) -> None:
        self._analyzer = GameAnalyzer()
        self._context: Optional[GameContext] = None
        self._analysis_interval = float(
            self.config.get("analysis_interval", 30.0)
        )
        self._analysis_event_interval = float(
            os.getenv("ANALYSIS_EVENT_INTERVAL", "15")
        )
        self._analysis_round = 0
        self._game_id: str | None = None

    async def teardown(self) -> None:
        if hasattr(self, "_analyzer"):
            await self._analyzer.close()

    async def on_signal(self, stream: str, signal: Signal) -> None:
        if signal.type == SignalType.SCOREBOARD:
            self._handle_scoreboard(signal.data)
            await self._maybe_analyze()
        elif signal.type == SignalType.BOXSCORE:
            self._handle_boxscore(signal.data)

    def _handle_scoreboard(self, data: dict[str, Any]) -> None:
        game_id = data.get("game_id", "")
        if game_id and not self._context:
            self._game_id = game_id
            self._context = GameContext(game_id=game_id)
        if self._context:
            self._context.update_scoreboard(data)

    def _handle_boxscore(self, data: dict[str, Any]) -> None:
        if self._context:
            self._context.update_boxscore(data)

    async def _maybe_analyze(self) -> None:
        if not self._context or not self._analyzer.is_enabled():
            return

        if not self._context.should_analyze(
            normal_interval=self._analysis_interval,
            event_interval=self._analysis_event_interval,
        ):
            return

        self._analysis_round += 1
        round_num = self._analysis_round
        game_id = self._game_id or ""

        try:
            self._context.mark_analyzed()
            async for chunk in self._analyzer.analyze_stream(self._context):
                await self.emit(StreamName.ANALYSIS, SignalType.ANALYSIS_CHUNK, {
                    "game_id": game_id,
                    "chunk": chunk,
                    "is_final": False,
                    "round": round_num,
                    "timestamp": _now_iso(),
                })

            # 发送最终标记
            await self.emit(StreamName.ANALYSIS, SignalType.ANALYSIS_CHUNK, {
                "game_id": game_id,
                "chunk": "",
                "is_final": True,
                "round": round_num,
                "timestamp": _now_iso(),
            })
        except Exception as exc:
            logger.error("AnalysisBot: 分析失败: {}", exc)
            self._context.mark_analysis_attempted(success=False)

    def get_runtime_metrics(self) -> dict[str, Any]:
        return {
            "game_id": self._game_id,
            "analysis_round": self._analysis_round,
            "analyzer_enabled": self._analyzer.is_enabled() if hasattr(self, "_analyzer") else False,
        }

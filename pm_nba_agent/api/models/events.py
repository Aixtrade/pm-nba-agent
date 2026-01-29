"""SSE 事件模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import json


@dataclass
class SSEEvent:
    """SSE 事件基类"""
    event_type: str
    data: dict

    def to_sse(self) -> str:
        """转换为 SSE 格式字符串"""
        json_data = json.dumps(self.data, ensure_ascii=False)
        return f"event: {self.event_type}\ndata: {json_data}\n\n"


@dataclass
class ScoreboardEvent(SSEEvent):
    """比分板事件"""
    event_type: str = field(default="scoreboard", init=False)

    @classmethod
    def create(
        cls,
        game_id: str,
        status: str,
        period: int,
        game_clock: str,
        home_team: dict,
        away_team: dict,
        status_message: Optional[str] = None,
    ) -> "ScoreboardEvent":
        return cls(data={
            "game_id": game_id,
            "status": status,
            "period": period,
            "game_clock": game_clock,
            "home_team": home_team,
            "away_team": away_team,
            "status_message": status_message,
        })


@dataclass
class BoxscoreEvent(SSEEvent):
    """详细统计事件"""
    event_type: str = field(default="boxscore", init=False)

    @classmethod
    def create(cls, game_data: dict) -> "BoxscoreEvent":
        """从 GameData.to_dict() 创建事件"""
        return cls(data=game_data)


@dataclass
class PlayByPlayEvent(SSEEvent):
    """逐回合事件"""
    event_type: str = field(default="playbyplay", init=False)

    @classmethod
    def create(cls, game_id: str, actions: list[dict]) -> "PlayByPlayEvent":
        return cls(data={
            "game_id": game_id,
            "actions": actions,
        })


@dataclass
class HeartbeatEvent(SSEEvent):
    """心跳事件"""
    event_type: str = field(default="heartbeat", init=False)

    @classmethod
    def create(cls) -> "HeartbeatEvent":
        return cls(data={
            "timestamp": datetime.utcnow().isoformat(),
        })


@dataclass
class ErrorEvent(SSEEvent):
    """错误事件"""
    event_type: str = field(default="error", init=False)

    @classmethod
    def create(cls, code: str, message: str, recoverable: bool = True) -> "ErrorEvent":
        return cls(data={
            "code": code,
            "message": message,
            "recoverable": recoverable,
            "timestamp": datetime.utcnow().isoformat(),
        })


@dataclass
class GameEndEvent(SSEEvent):
    """比赛结束事件"""
    event_type: str = field(default="game_end", init=False)

    @classmethod
    def create(
        cls,
        game_id: str,
        final_score_home: int,
        final_score_away: int,
        home_team_name: str,
        away_team_name: str,
    ) -> "GameEndEvent":
        return cls(data={
            "game_id": game_id,
            "final_score": {
                "home": final_score_home,
                "away": final_score_away,
            },
            "home_team": home_team_name,
            "away_team": away_team_name,
            "timestamp": datetime.utcnow().isoformat(),
        })


@dataclass
class AnalysisChunkEvent(SSEEvent):
    """AI 分析流式事件"""
    event_type: str = field(default="analysis_chunk", init=False)

    @classmethod
    def create(
        cls,
        game_id: str,
        chunk: str,
        is_final: bool = False,
        round_number: int = 0,
    ) -> "AnalysisChunkEvent":
        return cls(data={
            "game_id": game_id,
            "chunk": chunk,
            "is_final": is_final,
            "round": round_number,
            "timestamp": datetime.utcnow().isoformat(),
        })

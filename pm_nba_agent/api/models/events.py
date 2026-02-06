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
class HeartbeatEvent(SSEEvent):
    """心跳事件"""
    event_type: str = field(default="heartbeat", init=False)

    @classmethod
    def create(cls) -> "HeartbeatEvent":
        return cls(data={
            "timestamp": datetime.utcnow().isoformat(),
        })


@dataclass
class PolymarketInfoEvent(SSEEvent):
    """Polymarket 事件信息"""

    event_type: str = field(default="polymarket_info", init=False)

    @classmethod
    def create(cls, event_info: dict) -> "PolymarketInfoEvent":
        return cls(data=event_info)


@dataclass
class PolymarketBookEvent(SSEEvent):
    """Polymarket 订单簿事件"""

    event_type: str = field(default="polymarket_book", init=False)

    @classmethod
    def create(cls, payload: dict) -> "PolymarketBookEvent":
        return cls(data=payload)


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


@dataclass
class StrategySignalEvent(SSEEvent):
    """策略信号事件"""
    event_type: str = field(default="strategy_signal", init=False)

    @classmethod
    def create(
        cls,
        signal_type: str,
        reason: str,
        market: Optional[dict] = None,
        position: Optional[dict] = None,
        execution: Optional[dict] = None,
        strategy_id: str = "",
        yes_size: Optional[float] = None,
        no_size: Optional[float] = None,
        yes_price: Optional[float] = None,
        no_price: Optional[float] = None,
        metadata: Optional[dict] = None,
        metrics: Optional[list[dict[str, Any]]] = None,
    ) -> "StrategySignalEvent":
        return cls(data={
            "signal": {
                "type": signal_type,
                "reason": reason,
                "yes_size": yes_size,
                "no_size": no_size,
                "yes_price": yes_price,
                "no_price": no_price,
                "metadata": metadata or {},
            },
            "market": market,
            "position": position,
            "execution": execution,
            "strategy": {"id": strategy_id} if strategy_id else None,
            "metrics": metrics or [],
            "timestamp": datetime.utcnow().isoformat(),
        })

    @classmethod
    def from_signal_event(cls, signal_event: Any) -> "StrategySignalEvent":
        """从 SignalEvent 模型创建 SSE 事件"""
        if hasattr(signal_event, "to_dict"):
            data = signal_event.to_dict()
        elif isinstance(signal_event, dict):
            data = signal_event
        else:
            data = {"raw": str(signal_event)}
        data["timestamp"] = datetime.utcnow().isoformat()
        return cls(data=data)

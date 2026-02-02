"""任务模型定义"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskState(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 等待启动
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 正常完成
    CANCELLED = "cancelled"  # 用户取消
    FAILED = "failed"  # 异常失败


@dataclass
class TaskConfig:
    """任务配置（从 LiveStreamRequest 提取）"""

    url: str
    poll_interval: float = 10.0
    include_scoreboard: bool = True
    include_boxscore: bool = True
    include_playbyplay: bool = True
    playbyplay_limit: int = 20
    enable_analysis: bool = True
    analysis_interval: float = 30.0
    strategy_id: str = "merge_long"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    enable_trading: bool = False
    execution_mode: str = "SIMULATION"
    order_type: str = "GTC"
    order_expiration: Optional[str] = None
    min_order_amount: float = 1.0
    trade_cooldown_seconds: float = 0.0
    private_key: Optional[str] = None
    proxy_address: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskConfig":
        """从字典创建"""
        return cls(
            url=data.get("url", ""),
            poll_interval=float(data.get("poll_interval", 10.0)),
            include_scoreboard=bool(data.get("include_scoreboard", True)),
            include_boxscore=bool(data.get("include_boxscore", True)),
            include_playbyplay=bool(data.get("include_playbyplay", True)),
            playbyplay_limit=int(data.get("playbyplay_limit", 20)),
            enable_analysis=bool(data.get("enable_analysis", True)),
            analysis_interval=float(data.get("analysis_interval", 30.0)),
            strategy_id=str(data.get("strategy_id", "merge_long")),
            strategy_params=data.get("strategy_params") or {},
            enable_trading=bool(data.get("enable_trading", False)),
            execution_mode=str(data.get("execution_mode", "SIMULATION")),
            order_type=str(data.get("order_type", "GTC")),
            order_expiration=data.get("order_expiration"),
            min_order_amount=float(data.get("min_order_amount", 1.0)),
            trade_cooldown_seconds=float(data.get("trade_cooldown_seconds", 0.0)),
            private_key=data.get("private_key"),
            proxy_address=data.get("proxy_address"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskConfig":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class TaskStatus:
    """任务状态"""

    task_id: str
    state: TaskState
    created_at: str  # ISO 格式时间戳
    updated_at: str  # ISO 格式时间戳
    game_id: Optional[str] = None
    error: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "game_id": self.game_id,
            "error": self.error,
            "home_team": self.home_team,
            "away_team": self.away_team,
        }

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskStatus":
        """从字典创建"""
        return cls(
            task_id=data["task_id"],
            state=TaskState(data["state"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            game_id=data.get("game_id"),
            error=data.get("error"),
            home_team=data.get("home_team"),
            away_team=data.get("away_team"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskStatus":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create(cls, task_id: str) -> "TaskStatus":
        """创建新任务状态"""
        now = datetime.utcnow().isoformat() + "Z"
        return cls(
            task_id=task_id,
            state=TaskState.PENDING,
            created_at=now,
            updated_at=now,
        )

    def update_state(self, state: TaskState, error: Optional[str] = None) -> None:
        """更新状态"""
        self.state = state
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        if error:
            self.error = error

    def set_game_info(
        self, game_id: str, home_team: str, away_team: str
    ) -> None:
        """设置比赛信息"""
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.updated_at = datetime.utcnow().isoformat() + "Z"

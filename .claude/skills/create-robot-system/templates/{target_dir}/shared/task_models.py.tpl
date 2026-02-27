"""任务模型定义"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskState(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"        # 等待启动
    CANCELLING = "cancelling"  # 取消中
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 正常完成
    CANCELLED = "cancelled"    # 用户取消
    FAILED = "failed"          # 异常失败


@dataclass
class TaskConfig:
    """任务配置

    # 🔧 自定义点: 添加业务特定的配置字段
    """

    task_id: str = ""
    user_id: str = ""
    custom_config: dict[str, Any] = field(default_factory=dict)

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
            task_id=str(data.get("task_id", "")),
            user_id=str(data.get("user_id", "")),
            custom_config=data.get("custom_config") or {},
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
    created_at: str   # ISO 格式时间戳
    updated_at: str   # ISO 格式时间戳
    error: Optional[str] = None
    user_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "user_id": self.user_id,
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
            error=data.get("error"),
            user_id=str(data.get("user_id", "")),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskStatus":
        """从 JSON 反序列化"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create(cls, task_id: str, user_id: str = "") -> "TaskStatus":
        """创建新任务状态"""
        now = datetime.utcnow().isoformat() + "Z"
        return cls(
            task_id=task_id,
            state=TaskState.PENDING,
            created_at=now,
            updated_at=now,
            user_id=user_id,
        )

    def update_state(self, state: TaskState, error: Optional[str] = None) -> None:
        """更新状态"""
        self.state = state
        self.updated_at = datetime.utcnow().isoformat() + "Z"
        if error:
            self.error = error

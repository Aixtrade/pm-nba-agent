"""Redis Channel 命名规范"""

from enum import StrEnum


class StreamName(StrEnum):
    """所有业务 Stream 的统一定义。

    新增 Stream 时只需在此处添加枚举值，ALL_STREAMS 会自动更新。
    """

{STREAM_ENUM_MEMBERS}


class SignalType(StrEnum):
    """所有信号类型的统一定义。

    系统控制信号和业务信号统一管理，避免裸字符串拼写错误。
    """

    # 系统控制信号
    ROBOT_START = "robot_start"
    ROBOT_STOP = "robot_stop"
    ROBOT_ERROR = "robot_error"

    # 🔧 自定义点: 添加业务信号类型
    DATA_UPDATE = "data_update"
    PROCESS_RESULT = "process_result"


class Channels:
    """Redis Channel 命名工具类"""

    # 🔧 自定义点: 修改前缀为你的项目名
    PREFIX = "{prefix}"

    # 控制 Channel（Worker 监听）
    CONTROL = f"{PREFIX}:control"

    # Stream 名常量（从枚举引用，保持向后兼容）
{STREAM_CONST_REFS}

    # 所有 Stream 列表（SSE Bridge 遍历用，自动从枚举生成）
    ALL_STREAMS: list[str] = [s.value for s in StreamName]

    @classmethod
    def task_stream(cls, task_id: str, stream_name: str) -> str:
        """任务 Stream Key"""
        return f"{cls.PREFIX}:task:{task_id}:stream:{stream_name}"

    @classmethod
    def task_stream_pattern(cls, task_id: str) -> str:
        """任务所有 Stream 的 glob 模式"""
        return f"{cls.PREFIX}:task:{task_id}:stream:*"

    @classmethod
    def task_status(cls, task_id: str) -> str:
        """任务状态 Key"""
        return f"{cls.PREFIX}:task:{task_id}:status"

    @classmethod
    def task_config(cls, task_id: str) -> str:
        """任务配置 Key"""
        return f"{cls.PREFIX}:task:{task_id}:config"

    @classmethod
    def task_snapshot(cls, task_id: str, name: str) -> str:
        """任务快照 Key"""
        safe_name = name.replace(":", "_")
        return f"{cls.PREFIX}:task:{task_id}:snapshot:{safe_name}"

    @classmethod
    def all_tasks(cls) -> str:
        """所有任务集合 Key"""
        return f"{cls.PREFIX}:tasks"

    @classmethod
    def user_tasks(cls, user_id: str) -> str:
        """用户任务集合 Key"""
        return f"{cls.PREFIX}:user:{user_id}:tasks"

    @classmethod
    def parse_task_id(cls, channel: str) -> str | None:
        """从 Channel 名称解析 task_id"""
        prefix = f"{cls.PREFIX}:task:"
        if not channel.startswith(prefix):
            return None
        parts = channel[len(prefix):].split(":")
        if len(parts) >= 1:
            return parts[0]
        return None

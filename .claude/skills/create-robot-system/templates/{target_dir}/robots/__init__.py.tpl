"""Robot 系统包。"""

from .base import BaseRobot, RobotState, RobotStatus, Signal
from .composer import TaskComposer
from .{producer_name} import {ProducerClassName}
from .{consumer_name} import {ConsumerClassName}

__all__ = [
    "BaseRobot",
    "RobotState",
    "RobotStatus",
    "Signal",
    "TaskComposer",
    "{ProducerClassName}",
    "{ConsumerClassName}",
]

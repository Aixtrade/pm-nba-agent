"""Robot 系统包。"""

from .base import BaseRobot, RobotState, RobotStatus, Signal
from .composer import TaskComposer, ROBOT_REGISTRY, register_robot

__all__ = [
    "BaseRobot",
    "RobotState",
    "RobotStatus",
    "Signal",
    "TaskComposer",
    "ROBOT_REGISTRY",
    "register_robot",
]

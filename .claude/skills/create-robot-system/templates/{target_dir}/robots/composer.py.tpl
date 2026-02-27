"""Robot 任务编排器。"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from {package_name}.shared import RedisClient, TaskConfig

from .base import BaseRobot, StatusCallback
from .{producer_name} import {ProducerClassName}
from .{consumer_name} import {ConsumerClassName}


class TaskComposer:
    """根据 TaskConfig 创建并管理机器人。

    # 🔧 自定义点: 在 compose() 中添加新机器人的实例化逻辑
    """

    def __init__(self, redis: RedisClient):
        self.redis = redis
        self._robots: dict[str, list[BaseRobot]] = {}
        self._robot_tasks: dict[str, list[asyncio.Task[None]]] = {}

    ROBOT_REGISTRY = {
        "{producer_name}": {ProducerClassName},
        "{consumer_name}": {ConsumerClassName},
    }

    @classmethod
    def available_robot_types(cls) -> list[str]:
        return sorted(cls.ROBOT_REGISTRY.keys())

    def compose(
        self,
        task_id: str,
        config: TaskConfig,
        status_callback: StatusCallback | None = None,
    ) -> list[BaseRobot]:
        """根据配置创建任务对应的机器人列表。

        # 🔧 自定义点: 添加条件创建逻辑
        """
        cfg = config.to_dict()
        custom_config = cfg.get("custom_config") or {}
        configured_robots = custom_config.get("robots")

        robots: list[BaseRobot] = []
        if configured_robots is None:
            robots = [
                {ProducerClassName}(task_id, self.redis, cfg, status_callback),
                {ConsumerClassName}(task_id, self.redis, cfg, status_callback),
            ]
        else:
            if not isinstance(configured_robots, list):
                raise ValueError("custom_config.robots must be a list")

            for index, spec in enumerate(configured_robots):
                parsed = self._parse_robot_spec(spec, index)
                if parsed is None:
                    continue
                robot_type, robot_config = parsed
                robot_cls = self.ROBOT_REGISTRY.get(robot_type)
                if robot_cls is None:
                    available = ", ".join(self.available_robot_types())
                    raise ValueError(f"Unknown robot type: {robot_type}. Available: {available}")

                merged_config = dict(cfg)
                merged_config.update(robot_config)
                robots.append(robot_cls(task_id, self.redis, merged_config, status_callback))

            if not robots:
                raise ValueError("No robots are enabled for this task")

        self._robots[task_id] = robots
        logger.info("编排器已创建 {} 个机器人: task={}", len(robots), task_id)
        return robots

    def _parse_robot_spec(
        self,
        spec: Any,
        index: int,
    ) -> tuple[str, dict[str, Any]] | None:
        if isinstance(spec, str):
            return spec, {}

        if not isinstance(spec, dict):
            raise ValueError(f"Invalid robot spec at index {index}: must be string or object")

        if spec.get("enabled", True) is False:
            return None

        robot_type = spec.get("type")
        if not isinstance(robot_type, str) or not robot_type:
            raise ValueError(f"Invalid robot spec at index {index}: missing 'type'")

        robot_config = spec.get("config") or {}
        if not isinstance(robot_config, dict):
            raise ValueError(f"Invalid robot config for {robot_type}: must be object")

        return robot_type, robot_config

    async def start_all(self, task_id: str) -> list[asyncio.Task[None]]:
        """启动任务的所有机器人。"""
        robots = self._robots.get(task_id, [])
        tasks: list[asyncio.Task[None]] = []
        for robot in robots:
            tasks.append(
                asyncio.create_task(
                    robot.run_loop(),
                    name=f"robot:{task_id}:{robot.robot_type}",
                )
            )
        self._robot_tasks[task_id] = tasks
        return tasks

    async def stop_all(self, task_id: str) -> None:
        """停止任务的所有机器人。"""
        for robot in self._robots.get(task_id, []):
            await robot.stop()

        tasks = self._robot_tasks.pop(task_id, [])
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        self._robots.pop(task_id, None)

    def get_robots(self, task_id: str) -> list[BaseRobot]:
        """查询任务机器人列表。"""
        return self._robots.get(task_id, [])

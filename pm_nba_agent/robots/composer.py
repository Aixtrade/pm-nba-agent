"""Robot 任务编排器。"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from pm_nba_agent.shared import RedisClient, TaskConfig

from .base import BaseRobot, StatusCallback


# Robot 注册表：robot_type -> Robot 类
ROBOT_REGISTRY: dict[str, type[BaseRobot]] = {}


def register_robot(robot_type: str):
    """Robot 注册装饰器。"""
    def decorator(cls: type[BaseRobot]):
        ROBOT_REGISTRY[robot_type] = cls
        return cls
    return decorator


class TaskComposer:
    """根据 TaskConfig 创建并管理机器人。"""

    def __init__(self, redis: RedisClient):
        self.redis = redis
        self._robots: dict[str, list[BaseRobot]] = {}
        self._robot_tasks: dict[str, list[asyncio.Task[None]]] = {}

    @classmethod
    def available_robot_types(cls) -> list[str]:
        return sorted(ROBOT_REGISTRY.keys())

    def compose(
        self,
        task_id: str,
        config: TaskConfig,
        status_callback: StatusCallback | None = None,
    ) -> list[BaseRobot]:
        """根据配置创建任务对应的机器人列表。"""
        cfg = config.to_dict()
        custom_robots = cfg.get("auto_trade", {}).get("robots")

        robots: list[BaseRobot] = []
        if custom_robots is None:
            robots = self._compose_default(task_id, cfg, status_callback)
        else:
            if not isinstance(custom_robots, list):
                raise ValueError("robots must be a list")

            for index, spec in enumerate(custom_robots):
                parsed = self._parse_robot_spec(spec, index)
                if parsed is None:
                    continue
                robot_type, robot_config = parsed
                robot_cls = ROBOT_REGISTRY.get(robot_type)
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

    def _compose_default(
        self,
        task_id: str,
        cfg: dict[str, Any],
        status_callback: StatusCallback | None,
    ) -> list[BaseRobot]:
        """默认编排：根据现有配置推导出需要的 Robot。"""
        robots: list[BaseRobot] = []

        # 数据层 Bot 总是需要的
        for robot_type in ["nba_data", "book", "position"]:
            robot_cls = ROBOT_REGISTRY.get(robot_type)
            if robot_cls:
                robots.append(robot_cls(task_id, self.redis, cfg, status_callback))

        # 策略层 Bot：根据 strategy_ids 配置
        strategy_ids = cfg.get("strategy_ids") or []
        if not strategy_ids:
            legacy_id = cfg.get("strategy_id", "merge_long")
            if legacy_id:
                strategy_ids = [legacy_id]

        strategy_to_robot = {
            "merge_long": "merge_long",
            "locked_profit": "locked_profit",
        }
        for sid in strategy_ids:
            robot_type = strategy_to_robot.get(sid)
            if robot_type:
                robot_cls = ROBOT_REGISTRY.get(robot_type)
                if robot_cls:
                    params = (cfg.get("strategy_params_map") or {}).get(sid, {})
                    bot_cfg = dict(cfg)
                    bot_cfg["strategy_params"] = params
                    robots.append(robot_cls(task_id, self.redis, bot_cfg, status_callback))

        # 交易层 Bot：根据 auto_trade rules 推导
        auto_trade = cfg.get("auto_trade", {})
        if auto_trade.get("enabled"):
            rules = auto_trade.get("rules", [])
            rule_type_to_robot = {
                "signal_buy": "signal_buy",
                "condition_buy": "condition_buy",
                "periodic_buy": "periodic_buy",
            }
            seen_types: set[str] = set()
            for rule in rules:
                if not isinstance(rule, dict) or not rule.get("enabled", True):
                    continue
                rtype = rule.get("type", "")
                robot_type = rule_type_to_robot.get(rtype)
                if robot_type and robot_type not in seen_types:
                    robot_cls = ROBOT_REGISTRY.get(robot_type)
                    if robot_cls:
                        robots.append(robot_cls(task_id, self.redis, cfg, status_callback))
                        seen_types.add(robot_type)

        # ProfitSell：如果 auto_sell 启用
        auto_sell = cfg.get("auto_sell", {})
        if auto_sell.get("enabled"):
            robot_cls = ROBOT_REGISTRY.get("profit_sell")
            if robot_cls:
                robots.append(robot_cls(task_id, self.redis, cfg, status_callback))

        # 分析层 Bot
        if cfg.get("enable_analysis", True):
            robot_cls = ROBOT_REGISTRY.get("analysis")
            if robot_cls:
                robots.append(robot_cls(task_id, self.redis, cfg, status_callback))

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

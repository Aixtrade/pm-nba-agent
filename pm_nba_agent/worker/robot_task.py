"""机器人任务运行时。"""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import datetime
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.robots import TaskComposer
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus
from pm_nba_agent.shared.channels import StreamName


class RobotTask:
    """单个任务的运行时容器。

    职责：
    - 通过 TaskComposer 创建并管理机器人
    - 监听 reconfigure 事件实现热重载
    - 定时发布机器人心跳快照
    - 管理任务生命周期（启动 -> 运行 -> 停止/取消/失败）
    """

    def __init__(
        self,
        task_id: str,
        config: TaskConfig,
        redis: RedisClient,
    ):
        self.task_id = task_id
        self.config = config
        self.redis = redis
        self._task: Optional[asyncio.Task] = None
        self._cancelled = False
        self._stop_event = asyncio.Event()
        self._reconfigure_event = asyncio.Event()
        self._config_lock = asyncio.Lock()
        self._composer = TaskComposer(redis)

    def cancel(self) -> None:
        """取消任务。"""
        self._cancelled = True
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()

    async def update_config(self, patch: dict[str, Any]) -> None:
        """更新任务配置并触发机器人重载。"""
        if not isinstance(patch, dict) or not patch:
            return

        async with self._config_lock:
            merged = _deep_merge_dict(self.config.to_dict(), patch)
            self.config = TaskConfig.from_dict(merged)

        config_key = Channels.task_config(self.task_id)
        await self.redis.set(config_key, self.config.to_json(), ex=86400)
        self._reconfigure_event.set()

    async def refresh_positions_once(self, force: bool = False) -> None:
        """触发 PositionBot 立即刷新一次持仓。"""
        robots = self._composer.get_robots(self.task_id)
        for robot in robots:
            refresh = getattr(robot, "refresh_positions_once", None)
            if callable(refresh):
                await refresh(force=force)
                return
        logger.debug("任务 {} 当前无可刷新的 PositionBot", self.task_id)

    async def run(self) -> None:
        """运行机器人任务。"""
        status = await self._load_or_create_status()
        status.update_state(TaskState.RUNNING)
        await self._save_status(status)
        await self._publish_status(status)

        heartbeat_task: Optional[asyncio.Task] = None

        try:
            await self._compose_and_start()
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            while not self._stop_event.is_set():
                if self._reconfigure_event.is_set():
                    self._reconfigure_event.clear()
                    await self._composer.stop_all(self.task_id)
                    await self._compose_and_start()
                    logger.info("任务 {} 已热重载机器人", self.task_id)
                await asyncio.sleep(0.5)

            if self._cancelled:
                status.update_state(TaskState.CANCELLED)
            else:
                status.update_state(TaskState.COMPLETED)

        except asyncio.CancelledError:
            status.update_state(TaskState.CANCELLED)
            logger.info("机器人任务 {} 已取消", self.task_id)
        except Exception as exc:
            status.update_state(TaskState.FAILED, error=str(exc))
            logger.error("机器人任务 {} 失败: {}", self.task_id, exc)
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            await self._composer.stop_all(self.task_id)
            await self._save_status(status)
            await self._publish_status(status)
            await self._emit_control(
                "task_end",
                {
                    "task_id": self.task_id,
                    "state": status.state.value,
                    "timestamp": _now_iso(),
                },
            )

    async def _robot_status_callback(self, status: dict[str, Any]) -> None:
        """机器人状态变更时立即广播。"""
        await self._emit_control("robot_status", status)

    async def _compose_and_start(self) -> None:
        """创建并启动机器人。"""
        async with self._config_lock:
            cfg = copy.deepcopy(self.config)
        self._composer.compose(self.task_id, cfg, status_callback=self._robot_status_callback)
        await self._composer.start_all(self.task_id)

    async def _heartbeat_loop(self) -> None:
        """低频心跳（30s），确认机器人存活。"""
        while not self._stop_event.is_set():
            await asyncio.sleep(30.0)
            if self._stop_event.is_set():
                break
            robots = self._composer.get_robots(self.task_id)
            for robot in robots:
                status = robot.get_status().to_dict()
                status.update(robot.get_runtime_metrics())
                status["timestamp"] = _now_iso()
                status["heartbeat"] = True
                await self._emit_control("robot_status", status)

    async def _save_status(self, status: TaskStatus) -> None:
        """持久化任务状态。"""
        key = Channels.task_status(self.task_id)
        await self.redis.set(key, status.to_json(), ex=86400)

    async def _load_or_create_status(self) -> TaskStatus:
        """加载或创建任务状态。"""
        key = Channels.task_status(self.task_id)
        data = await self.redis.get(key)
        if not data:
            return TaskStatus.create(self.task_id, user_id=self.config.user_id)
        try:
            status = TaskStatus.from_json(data)
            if not status.user_id and self.config.user_id:
                status.user_id = self.config.user_id
            return status
        except Exception:
            return TaskStatus.create(self.task_id, user_id=self.config.user_id)

    async def _publish_status(self, status: TaskStatus) -> None:
        """发布任务状态到控制 stream。"""
        await self._emit_control("task_status", status.to_dict())

    async def _emit_control(self, signal_type: str, payload: dict[str, Any]) -> None:
        """发出控制信号。"""
        fields = {
            "type": signal_type,
            "source": "task_runtime",
            "task_id": self.task_id,
            "timestamp": _now_iso(),
            "schema_version": "1.0",
            "data": json.dumps(payload, ensure_ascii=False),
        }
        await self.redis.xadd(
            Channels.task_stream(self.task_id, StreamName.CONTROL),
            fields,
            maxlen=1000,
        )


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """深度合并字典。"""
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(current, value)
        else:
            merged[key] = value
    return merged


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

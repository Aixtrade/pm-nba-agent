"""任务管理器"""

import asyncio
import json
from typing import Optional

from loguru import logger

from {package_name}.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus
from {package_name}.worker.robot_task import RobotTask


class TaskManager:
    """后台任务管理器。

    职责：
    - 监听 Redis Pub/Sub 控制 Channel
    - 任务 CRUD（创建、取消、查询）
    - 崩溃恢复（扫描 Redis 中 PENDING/RUNNING 状态的任务）
    - 配置热更新转发
    """

    def __init__(self, redis: RedisClient):
        self.redis = redis
        self._tasks: dict[str, RobotTask] = {}
        self._running = False

    async def start(self) -> None:
        """启动任务管理器。"""
        self._running = True
        logger.info("TaskManager 已启动")

        await self._recover_tasks()
        await self._listen_control()

    async def stop(self) -> None:
        """停止任务管理器。"""
        self._running = False

        for task_id, task in list(self._tasks.items()):
            logger.info("正在取消任务: {}", task_id)
            task.cancel()

        if self._tasks:
            await asyncio.gather(
                *[task._task for task in self._tasks.values() if task._task],
                return_exceptions=True,
            )

        self._tasks.clear()
        logger.info("TaskManager 已停止")

    async def create_task(self, task_id: str, config: TaskConfig) -> bool:
        """创建并启动任务。"""
        if task_id in self._tasks:
            logger.warning("任务已存在: {}", task_id)
            return False

        if not config.task_id or config.task_id != task_id:
            config.task_id = task_id

        config_key = Channels.task_config(task_id)
        await self.redis.set(config_key, config.to_json(), ex=86400)
        await self.redis.sadd(Channels.all_tasks(), task_id)
        if config.user_id:
            await self.redis.sadd(Channels.user_tasks(config.user_id), task_id)

        task = RobotTask(
            task_id=task_id,
            config=config,
            redis=self.redis,
        )
        self._tasks[task_id] = task
        task._task = asyncio.create_task(self._run_task(task_id, task))

        logger.info("任务已创建: {}", task_id)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务。"""
        task = self._tasks.get(task_id)
        if not task:
            logger.warning("任务不存在: {}", task_id)
            return False

        task.cancel()
        logger.info("任务取消请求已发送: {}", task_id)
        return True

    async def delete_task(self, task_id: str) -> bool:
        """删除任务（停止运行并清理 Redis 记录）。"""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            if task._task:
                await asyncio.gather(task._task, return_exceptions=True)

        config_key = Channels.task_config(task_id)
        status_key = Channels.task_status(task_id)
        config_raw = await self.redis.get(config_key)
        status_raw = await self.redis.get(status_key)

        user_id = ""
        if status_raw:
            try:
                user_id = TaskStatus.from_json(status_raw).user_id
            except Exception:
                user_id = ""
        if not user_id and config_raw:
            try:
                user_id = TaskConfig.from_json(config_raw).user_id
            except Exception:
                user_id = ""

        stream_keys = [Channels.task_stream(task_id, stream) for stream in Channels.ALL_STREAMS]
        removed_key_count = await self.redis.delete(config_key, status_key, *stream_keys)
        removed_task_count = await self.redis.srem(Channels.all_tasks(), task_id)
        if user_id:
            await self.redis.srem(Channels.user_tasks(user_id), task_id)

        logger.info(
            "任务已删除: task={} keys_removed={} task_set_removed={}",
            task_id,
            removed_key_count,
            removed_task_count,
        )
        return bool(task or removed_key_count or removed_task_count)

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态。"""
        key = Channels.task_status(task_id)
        data = await self.redis.get(key)
        if not data:
            return None
        return TaskStatus.from_json(data)

    async def list_tasks(self) -> list[TaskStatus]:
        """列出所有任务。"""
        task_ids = await self.redis.smembers(Channels.all_tasks())
        statuses = []

        for task_id in task_ids:
            status = await self.get_task_status(task_id)
            if status:
                statuses.append(status)

        return statuses

    async def _run_task(self, task_id: str, task: RobotTask) -> None:
        """运行任务并在完成后清理。"""
        try:
            await task.run()
        finally:
            self._tasks.pop(task_id, None)
            logger.info("任务已完成: {}", task_id)

    async def _recover_tasks(self) -> None:
        """恢复未完成任务（崩溃恢复）。"""
        task_ids = await self.redis.smembers(Channels.all_tasks())

        for task_id in task_ids:
            status = await self.get_task_status(task_id)
            if not status:
                continue

            if status.state not in (TaskState.PENDING, TaskState.RUNNING, TaskState.CANCELLING):
                continue

            config_key = Channels.task_config(task_id)
            config_data = await self.redis.get(config_key)
            if not config_data:
                logger.warning("任务配置不存在，跳过恢复: {}", task_id)
                continue

            config = TaskConfig.from_json(config_data)
            task = RobotTask(
                task_id=task_id,
                config=config,
                redis=self.redis,
            )
            self._tasks[task_id] = task
            task._task = asyncio.create_task(self._run_task(task_id, task))
            if status.state == TaskState.CANCELLING:
                task.cancel()

            logger.info("任务已恢复: {}", task_id)

    async def _listen_control(self) -> None:
        """监听控制 Channel。"""
        logger.info("开始监听控制 Channel: {}", Channels.CONTROL)

        try:
            async for message in self.redis.subscribe(Channels.CONTROL):
                if not self._running:
                    break
                await self._handle_control_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("控制 Channel 监听异常: {}", exc)

    async def _handle_control_message(self, message: dict) -> None:
        """处理控制消息。

        支持的 action:
        - create: 创建新任务
        - cancel: 取消任务
        - delete: 删除任务
        - update_config: 热更新任务配置
        - shutdown: 关闭 Worker
        """
        try:
            data = json.loads(message["data"])
            action = data.get("action")
            task_id = data.get("task_id")

            if action == "create" and task_id:
                config_data = data.get("config", {})
                user_id = data.get("user_id", "")
                if user_id and "user_id" not in config_data:
                    config_data["user_id"] = user_id
                config = TaskConfig.from_dict(config_data)
                await self.create_task(task_id, config)

            elif action == "cancel" and task_id:
                await self.cancel_task(task_id)

            elif action == "delete" and task_id:
                await self.delete_task(task_id)

            elif action == "update_config" and task_id:
                patch = data.get("patch", {})
                task = self._tasks.get(task_id)
                if not task:
                    logger.warning("任务未运行，无法更新配置: {}", task_id)
                    return
                await task.update_config(patch)
                logger.info("任务配置已更新: {}", task_id)

            elif action == "shutdown":
                logger.info("收到关闭指令")
                self._running = False

            else:
                logger.warning("未知控制消息: {}", data)

        except Exception as exc:
            logger.error("处理控制消息失败: {}", exc)

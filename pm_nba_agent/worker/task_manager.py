"""任务管理器"""

import asyncio
import json
from typing import Optional

from loguru import logger

from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.agent import GameAnalyzer
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus
from pm_nba_agent.worker.game_task import GameTask


class TaskManager:
    """后台任务管理器"""

    def __init__(
        self,
        redis: RedisClient,
        fetcher: DataFetcher,
        analyzer: Optional[GameAnalyzer] = None,
    ):
        self.redis = redis
        self.fetcher = fetcher
        self.analyzer = analyzer
        self._tasks: dict[str, GameTask] = {}
        self._running = False

    async def start(self) -> None:
        """启动任务管理器"""
        self._running = True
        logger.info("TaskManager 已启动")

        # 恢复未完成的任务
        await self._recover_tasks()

        # 监听控制 Channel
        await self._listen_control()

    async def stop(self) -> None:
        """停止任务管理器"""
        self._running = False

        # 取消所有运行中的任务
        for task_id, task in list(self._tasks.items()):
            logger.info("正在取消任务: {}", task_id)
            task.cancel()

        # 等待所有任务完成
        if self._tasks:
            await asyncio.gather(
                *[t._task for t in self._tasks.values() if t._task],
                return_exceptions=True,
            )

        self._tasks.clear()
        logger.info("TaskManager 已停止")

    async def create_task(self, task_id: str, config: TaskConfig) -> bool:
        """创建新任务"""
        if task_id in self._tasks:
            logger.warning("任务已存在: {}", task_id)
            return False

        # 保存配置到 Redis
        config_key = Channels.task_config(task_id)
        await self.redis.set(config_key, config.to_json(), ex=86400)

        # 添加到任务集合
        await self.redis.sadd(Channels.all_tasks(), task_id)

        # 创建并启动任务
        task = GameTask(
            task_id=task_id,
            config=config,
            redis=self.redis,
            fetcher=self.fetcher,
            analyzer=self.analyzer,
        )
        self._tasks[task_id] = task
        task._task = asyncio.create_task(self._run_task(task_id, task))

        logger.info("任务已创建: {}", task_id)
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(task_id)
        if not task:
            logger.warning("任务不存在: {}", task_id)
            return False

        task.cancel()
        logger.info("任务取消请求已发送: {}", task_id)
        return True

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        key = Channels.task_status(task_id)
        data = await self.redis.get(key)
        if not data:
            return None
        return TaskStatus.from_json(data)

    async def list_tasks(self) -> list[TaskStatus]:
        """列出所有任务"""
        task_ids = await self.redis.smembers(Channels.all_tasks())
        statuses = []

        for task_id in task_ids:
            status = await self.get_task_status(task_id)
            if status:
                statuses.append(status)

        return statuses

    async def _run_task(self, task_id: str, task: GameTask) -> None:
        """运行任务并在完成后清理"""
        try:
            await task.run()
        finally:
            self._tasks.pop(task_id, None)
            logger.info("任务已完成: {}", task_id)

    async def _recover_tasks(self) -> None:
        """恢复未完成的任务"""
        task_ids = await self.redis.smembers(Channels.all_tasks())

        for task_id in task_ids:
            status = await self.get_task_status(task_id)
            if not status:
                continue

            # 只恢复 PENDING 和 RUNNING 状态的任务
            if status.state not in (TaskState.PENDING, TaskState.RUNNING):
                continue

            # 获取配置
            config_key = Channels.task_config(task_id)
            config_data = await self.redis.get(config_key)
            if not config_data:
                logger.warning("任务配置不存在，跳过恢复: {}", task_id)
                continue

            config = TaskConfig.from_json(config_data)

            # 重新创建任务
            task = GameTask(
                task_id=task_id,
                config=config,
                redis=self.redis,
                fetcher=self.fetcher,
                analyzer=self.analyzer,
            )
            self._tasks[task_id] = task
            task._task = asyncio.create_task(self._run_task(task_id, task))

            logger.info("任务已恢复: {}", task_id)

    async def _listen_control(self) -> None:
        """监听控制 Channel"""
        logger.info("开始监听控制 Channel: {}", Channels.CONTROL)

        try:
            async for message in self.redis.subscribe(Channels.CONTROL):
                if not self._running:
                    break

                await self._handle_control_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("控制 Channel 监听异常: {}", e)

    async def _handle_control_message(self, message: dict) -> None:
        """处理控制消息"""
        try:
            data = json.loads(message["data"])
            action = data.get("action")
            task_id = data.get("task_id")

            if action == "create" and task_id:
                config_data = data.get("config", {})
                config = TaskConfig.from_dict(config_data)
                await self.create_task(task_id, config)

            elif action == "cancel" and task_id:
                await self.cancel_task(task_id)

            elif action == "shutdown":
                logger.info("收到关闭指令")
                self._running = False

            else:
                logger.warning("未知控制消息: {}", data)

        except Exception as e:
            logger.error("处理控制消息失败: {}", e)

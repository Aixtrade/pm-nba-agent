"""单场比赛任务封装"""

import asyncio
import json
from typing import Optional

from loguru import logger

from pm_nba_agent.api.models.requests import LiveStreamRequest
from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.api.services.game_stream import GameStreamService
from pm_nba_agent.agent import GameAnalyzer
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus


class GameTask:
    """单场比赛后台任务"""

    SNAPSHOT_EVENTS = {
        "polymarket_info",
        "polymarket_book",
        "scoreboard",
    }

    def __init__(
        self,
        task_id: str,
        config: TaskConfig,
        redis: RedisClient,
        fetcher: DataFetcher,
        analyzer: Optional[GameAnalyzer] = None,
    ):
        self.task_id = task_id
        self.config = config
        self.redis = redis
        self.fetcher = fetcher
        self.analyzer = analyzer
        self._cancelled = False
        self._task: Optional[asyncio.Task] = None

    def cancel(self) -> None:
        """取消任务"""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()

    async def run(self) -> None:
        """运行任务"""
        status = TaskStatus.create(self.task_id)
        status.update_state(TaskState.RUNNING)
        await self._save_status(status)
        await self._publish_status(status)

        try:
            await self._run_stream(status)

            if self._cancelled:
                status.update_state(TaskState.CANCELLED)
            else:
                status.update_state(TaskState.COMPLETED)
        except asyncio.CancelledError:
            status.update_state(TaskState.CANCELLED)
            logger.info("任务 {} 已取消", self.task_id)
        except Exception as e:
            status.update_state(TaskState.FAILED, error=str(e))
            logger.error("任务 {} 失败: {}", self.task_id, e)
        finally:
            await self._save_status(status)
            await self._publish_status(status)
            # 发送结束事件
            await self._publish_event(
                f'event: task_end\ndata: {{"task_id": "{self.task_id}", "state": "{status.state.value}"}}\n\n'
            )

    async def _run_stream(self, status: TaskStatus) -> None:
        """运行数据流"""
        # 构建 LiveStreamRequest
        request = LiveStreamRequest(
            url=self.config.url,
            poll_interval=self.config.poll_interval,
            include_scoreboard=self.config.include_scoreboard,
            include_boxscore=self.config.include_boxscore,
            include_playbyplay=self.config.include_playbyplay,
            playbyplay_limit=self.config.playbyplay_limit,
            enable_analysis=self.config.enable_analysis,
            analysis_interval=self.config.analysis_interval,
            strategy_id=self.config.strategy_id,
            strategy_params=self.config.strategy_params,
            enable_trading=self.config.enable_trading,
            execution_mode=self.config.execution_mode,
            order_type=self.config.order_type,
            order_expiration=self.config.order_expiration,
            min_order_amount=self.config.min_order_amount,
            trade_cooldown_seconds=self.config.trade_cooldown_seconds,
            private_key=self.config.private_key,
            proxy_address=self.config.proxy_address,
        )

        # 创建流服务
        stream_service = GameStreamService(self.fetcher, self.analyzer)

        # 消费事件流并发布到 Redis
        async for event in stream_service.create_stream(request):
            if self._cancelled:
                break

            # 发布事件到 Redis Channel
            await self._publish_event(event)

            # 从 scoreboard 事件提取比赛信息
            if event.startswith("event: scoreboard"):
                updated = self._extract_game_info(event, status)
                if updated:
                    await self._save_status(status)
                    await self._publish_status(status)

    def _extract_game_info(self, event: str, status: TaskStatus) -> bool:
        """从 scoreboard 事件提取比赛信息"""
        try:
            # 解析 SSE 事件
            lines = event.strip().split("\n")
            data_line = None
            for line in lines:
                if line.startswith("data: "):
                    data_line = line[6:]
                    break

            if not data_line:
                return

            data = json.loads(data_line)
            game_id = data.get("game_id")
            home_team = data.get("home_team", {}).get("name")
            away_team = data.get("away_team", {}).get("name")

            if game_id and home_team and away_team:
                if (
                    status.game_id != game_id
                    or status.home_team != home_team
                    or status.away_team != away_team
                ):
                    status.set_game_info(game_id, home_team, away_team)
                    return True

        except Exception:
            return False

        return False

    async def _publish_event(self, event: str) -> None:
        """发布事件到 Redis"""
        await self._cache_snapshot(event)
        channel = Channels.task_events(self.task_id)
        await self.redis.publish(channel, event)

    async def _save_status(self, status: TaskStatus) -> None:
        """保存任务状态到 Redis"""
        key = Channels.task_status(self.task_id)
        # 状态保留 24 小时
        await self.redis.set(key, status.to_json(), ex=86400)

    async def _publish_status(self, status: TaskStatus) -> None:
        """发布任务状态事件"""
        payload = json.dumps(status.to_dict(), ensure_ascii=False)
        await self._publish_event(f"event: task_status\ndata: {payload}\n\n")

    async def _cache_snapshot(self, event: str) -> None:
        """缓存可回放事件"""
        event_type = None
        for line in event.splitlines():
            if line.startswith("event:"):
                event_type = line[6:].strip()

        if not event_type or event_type not in self.SNAPSHOT_EVENTS:
            return

        snapshot_key = Channels.task_snapshot(self.task_id, event_type)
        await self.redis.set(snapshot_key, event, ex=86400)

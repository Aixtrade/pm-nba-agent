"""单场比赛任务封装 — 纯协调层"""

import asyncio
import copy
import json
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.api.models.requests import LiveStreamRequest
from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.api.services.game_stream import GameStreamService
from pm_nba_agent.agent import GameAnalyzer
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus

from .auto_buy import AutoBuyHandler
from .auto_sell import AutoSellHandler
from .auto_trade import AutoTradeHandler
from .event_bus import EventPublisher
from .market_state import MarketState
from .position_manager import PositionManager
from .sse_utils import deep_merge_dict, format_sse_event, parse_sse_event


class GameTask:
    """单场比赛后台任务 — 组装子模块并协调事件流。"""

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
        self._config_lock = asyncio.Lock()

        # 子模块
        self.market_state = MarketState()
        self.publisher = EventPublisher(task_id, redis)
        self.position_manager = PositionManager(
            task_id=task_id,
            market_state=self.market_state,
            publisher=self.publisher,
            config_provider=lambda: self.config,
        )
        self.auto_trade = AutoTradeHandler(
            task_id=task_id,
            config_provider=lambda: self.config,
            market_state=self.market_state,
            publisher=self.publisher,
        )
        self.auto_sell = AutoSellHandler(
            task_id=task_id,
            config_provider=lambda: self.config,
            market_state=self.market_state,
            position_manager=self.position_manager,
            publisher=self.publisher,
        )
        self.auto_buy = AutoBuyHandler(
            task_id=task_id,
            config_provider=lambda: self.config,
            market_state=self.market_state,
            publisher=self.publisher,
        )

        # 后台任务句柄
        self._position_refresh_task: Optional[asyncio.Task] = None
        self._auto_trade_tick_task: Optional[asyncio.Task] = None

    def cancel(self) -> None:
        """取消任务"""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()

    async def update_config(self, patch: dict[str, Any]) -> None:
        """更新任务配置（运行时生效）"""
        if not isinstance(patch, dict) or not patch:
            return

        old_auto_sell_enabled = bool(
            self.config.auto_sell.get("enabled", False)
            if isinstance(self.config.auto_sell, dict)
            else False
        )
        old_auto_trade = copy.deepcopy(self.config.auto_trade) if isinstance(self.config.auto_trade, dict) else {}

        async with self._config_lock:
            merged = deep_merge_dict(self.config.to_dict(), patch)
            self.config = TaskConfig.from_dict(merged)

        new_auto_trade = copy.deepcopy(self.config.auto_trade) if isinstance(self.config.auto_trade, dict) else {}
        await self.auto_trade.on_config_updated(old_auto_trade, new_auto_trade)

        new_auto_sell_enabled = bool(
            self.config.auto_sell.get("enabled", False)
            if isinstance(self.config.auto_sell, dict)
            else False
        )

        await self.auto_buy.publish_state()
        await self.auto_trade.publish_state()
        await self.auto_sell.publish_state()
        if not old_auto_sell_enabled and new_auto_sell_enabled:
            await self.refresh_positions_once(force=True)

    async def refresh_positions_once(self, force: bool = False) -> None:
        await self.position_manager.refresh_once(force=force)

    async def run(self) -> None:
        """运行任务"""
        status = await self.publisher.load_or_create_status()
        status.update_state(TaskState.RUNNING)
        await self.publisher.save_status(status)
        await self.publisher.publish_status(status)
        await self.auto_buy.publish_state()
        await self.auto_trade.publish_state()
        await self.auto_sell.publish_state()
        await self.position_manager.publish_state()
        self._position_refresh_task = asyncio.create_task(
            self.position_manager.start_refresh_loop(lambda: self._cancelled)
        )
        self._auto_trade_tick_task = asyncio.create_task(
            self.auto_trade.tick_loop(lambda: self._cancelled)
        )
        await self.refresh_positions_once(force=True)

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
            if self._position_refresh_task:
                self._position_refresh_task.cancel()
                try:
                    await self._position_refresh_task
                except asyncio.CancelledError:
                    pass
            if self._auto_trade_tick_task:
                self._auto_trade_tick_task.cancel()
                try:
                    await self._auto_trade_tick_task
                except asyncio.CancelledError:
                    pass
            await self.publisher.save_status(status)
            await self.publisher.publish_status(status)
            await self.publisher.publish_raw(
                f'event: task_end\ndata: {{"task_id": "{self.task_id}", "state": "{status.state.value}"}}\n\n'
            )

    async def _run_stream(self, status: TaskStatus) -> None:
        """运行数据流"""
        request = LiveStreamRequest(
            url=self.config.url,
            poll_interval=self.config.poll_interval,
            include_scoreboard=self.config.include_scoreboard,
            include_boxscore=self.config.include_boxscore,
            enable_analysis=self.config.enable_analysis,
            analysis_interval=self.config.analysis_interval,
            strategy_ids=self.config.strategy_ids,
            strategy_params_map=self.config.strategy_params_map,
            strategy_id=self.config.strategy_id,
            strategy_params=self.config.strategy_params,
            proxy_address=self.config.proxy_address,
        )

        stream_service = GameStreamService(
            self.fetcher,
            self.analyzer,
            position_provider=self.position_manager.get_position_context,
            analysis_enabled_fn=lambda: self.config.enable_analysis,
        )

        async for event in stream_service.create_stream(request):
            if self._cancelled:
                break

            event = await self._handle_runtime_event(event)
            await self.publisher.publish_raw(event)

            if event.startswith("event: scoreboard"):
                updated = self._extract_game_info(event, status)
                if updated:
                    await self.publisher.save_status(status)
                    await self.publisher.publish_status(status)

    async def _handle_runtime_event(self, event: str) -> str:
        """处理运行时事件（市场数据更新 + 自动交易触发）"""
        event_type, payload = parse_sse_event(event)
        if not event_type or payload is None:
            return event

        if event_type == "polymarket_info":
            self.market_state.update_from_polymarket_info(payload)
            if not self.position_manager.initial_refresh_done:
                await self.refresh_positions_once(force=True)
                self.position_manager.mark_initial_done()
            return event

        if event_type == "polymarket_book":
            self.market_state.update_from_polymarket_book(payload)
            await self.auto_sell.maybe_execute()
            await self.auto_trade.execute_intents(self.auto_trade.rule_engine.on_book_update())
            return event

        if event_type == "strategy_signal":
            return await self._handle_strategy_signal(event, payload)

        return event

    async def _handle_strategy_signal(self, event: str, payload: dict[str, Any]) -> str:
        await self.auto_trade.execute_intents(self.auto_trade.rule_engine.on_strategy_signal(payload))

        # 避免 legacy auto_buy 与 auto_trade.signal_buy 双通道重复下单
        if self.auto_trade.has_enabled_signal_buy():
            return event

        signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        signal_type = str(signal.get("type", "")).upper()
        strategy_id = str(strategy.get("id", "")).strip()

        if signal_type != "BUY" or not strategy_id:
            return event

        auto_buy_cfg = self.auto_buy._get_auto_buy_config()
        if not auto_buy_cfg.get("enabled", False):
            return event

        rule = auto_buy_cfg.get("strategy_rules", {}).get(strategy_id)
        if not isinstance(rule, dict) or not rule.get("enabled", True):
            return event

        signal_types = rule.get("signal_types") or ["BUY"]
        allowed_types = {
            str(t).upper()
            for t in signal_types
            if isinstance(t, str)
        }
        if allowed_types and signal_type not in allowed_types:
            return event

        execution = await self.auto_buy.on_strategy_signal(strategy_id, rule)
        payload["execution"] = execution
        return format_sse_event("strategy_signal", payload)

    @staticmethod
    def _extract_game_info(event: str, status: TaskStatus) -> bool:
        """从 scoreboard 事件提取比赛信息"""
        try:
            lines = event.strip().split("\n")
            data_line = None
            for line in lines:
                if line.startswith("data: "):
                    data_line = line[6:]
                    break

            if not data_line:
                return False

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

"""单场比赛任务封装"""

import asyncio
import copy
import json
from datetime import datetime
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.api.models.requests import LiveStreamRequest
from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.api.services.game_stream import GameStreamService
from pm_nba_agent.agent import GameAnalyzer
from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus


class GameTask:
    """单场比赛后台任务"""

    SNAPSHOT_EVENTS = {
        "polymarket_info",
        "polymarket_book",
        "scoreboard",
        "auto_buy_state",
    }
    BOTH_SIDE = "__BOTH__"

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

        # AutoBuy 运行态
        self._token_by_outcome: dict[str, str] = {}
        self._outcome_by_token: dict[str, str] = {}
        self._best_ask_by_token: dict[str, float] = {}
        self._auto_buy_is_ordering = False
        self._auto_buy_last_order_time: Optional[str] = None
        self._auto_buy_stats: dict[str, dict[str, Any]] = {}

    def cancel(self) -> None:
        """取消任务"""
        self._cancelled = True
        if self._task and not self._task.done():
            self._task.cancel()

    async def update_config(self, patch: dict[str, Any]) -> None:
        """更新任务配置（运行时生效）"""
        if not isinstance(patch, dict) or not patch:
            return

        async with self._config_lock:
            merged = self._deep_merge_dict(self.config.to_dict(), patch)
            self.config = TaskConfig.from_dict(merged)

        await self._publish_auto_buy_state()

    async def run(self) -> None:
        """运行任务"""
        status = TaskStatus.create(self.task_id)
        status.update_state(TaskState.RUNNING)
        await self._save_status(status)
        await self._publish_status(status)
        await self._publish_auto_buy_state()

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
            analysis_interval=self.config.analysis_interval,
            strategy_ids=self.config.strategy_ids,
            strategy_params_map=self.config.strategy_params_map,
            strategy_id=self.config.strategy_id,
            strategy_params=self.config.strategy_params,
            proxy_address=self.config.proxy_address,
        )

        # 创建流服务
        stream_service = GameStreamService(self.fetcher, self.analyzer)

        # 消费事件流并发布到 Redis
        async for event in stream_service.create_stream(request):
            if self._cancelled:
                break

            event = await self._handle_runtime_event(event)

            # 发布事件到 Redis Channel
            await self._publish_event(event)

            # 从 scoreboard 事件提取比赛信息
            if event.startswith("event: scoreboard"):
                updated = self._extract_game_info(event, status)
                if updated:
                    await self._save_status(status)
                    await self._publish_status(status)

    async def _handle_runtime_event(self, event: str) -> str:
        """处理运行时事件（自动买入与状态注入）"""
        event_type, payload = self._parse_sse_event(event)
        if not event_type or payload is None:
            return event

        if event_type == "polymarket_info":
            self._update_token_mapping(payload)
            return event

        if event_type == "polymarket_book":
            self._update_best_ask(payload)
            return event

        if event_type == "strategy_signal":
            return await self._handle_strategy_signal(event, payload)

        return event

    async def _handle_strategy_signal(self, event: str, payload: dict[str, Any]) -> str:
        signal = payload.get("signal") if isinstance(payload.get("signal"), dict) else {}
        strategy = payload.get("strategy") if isinstance(payload.get("strategy"), dict) else {}
        signal_type = str(signal.get("type", "")).upper()
        strategy_id = str(strategy.get("id", "")).strip()

        if signal_type != "BUY" or not strategy_id:
            return event

        cfg = await self._get_auto_buy_config_snapshot()
        if not cfg.get("enabled", False):
            return event

        rule = cfg.get("strategy_rules", {}).get(strategy_id)
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

        execution = await self._execute_auto_buy(strategy_id, rule)
        payload["execution"] = execution
        return self._format_sse_event("strategy_signal", payload)

    async def _execute_auto_buy(self, strategy_id: str, rule: dict[str, Any]) -> dict[str, Any]:
        if self._auto_buy_is_ordering:
            return {
                "success": False,
                "orders": [],
                "error": "下单中",
                "source": "task_auto_buy",
                "strategy_id": strategy_id,
            }

        self._auto_buy_is_ordering = True
        await self._publish_auto_buy_state()

        cfg = await self._get_auto_buy_config_snapshot()
        default_cfg = cfg.get("default", {})

        side = str(rule.get("side", self.BOTH_SIDE))
        amount = float(rule.get("amount", default_cfg.get("amount", 10.0)))
        round_size = bool(rule.get("round_size", default_cfg.get("round_size", False)))
        order_type = str(rule.get("order_type", default_cfg.get("order_type", "GTC")))
        private_key = self.config.private_key
        proxy_address = self.config.proxy_address

        outcomes = self._resolve_target_outcomes(side)
        orders: list[dict[str, Any]] = []
        error_messages: list[str] = []

        try:
            if amount <= 0:
                return {
                    "success": False,
                    "orders": [],
                    "error": "amount 必须大于 0",
                    "source": "task_auto_buy",
                    "strategy_id": strategy_id,
                }
            if not private_key:
                return {
                    "success": False,
                    "orders": [],
                    "error": "private_key 不能为空",
                    "source": "task_auto_buy",
                    "strategy_id": strategy_id,
                }

            for outcome in outcomes:
                token_id = self._token_by_outcome.get(outcome)
                if not token_id:
                    continue

                best_ask = self._best_ask_by_token.get(token_id)
                if best_ask is None or best_ask <= 0 or best_ask >= 1:
                    continue

                size = self._calculate_size(amount, best_ask, round_size)
                if size <= 0:
                    continue

                order_info = {
                    "token_id": token_id,
                    "side": "BUY",
                    "price": best_ask,
                    "size": size,
                    "order_type": order_type,
                    "outcome": outcome,
                }

                try:
                    result = await create_polymarket_order(
                        token_id=token_id,
                        side="BUY",
                        price=best_ask,
                        size=size,
                        order_type=order_type,
                        private_key=private_key,
                        proxy_address=proxy_address,
                    )
                    orders.append({**order_info, "status": "SUBMITTED", "result": result})
                    self._record_auto_buy_stat(outcome, amount)
                except Exception as exc:
                    logger.error("自动买入失败 task={} strategy={} outcome={}: {}", self.task_id, strategy_id, outcome, exc)
                    message = str(exc)
                    error_messages.append(message)
                    orders.append({**order_info, "status": "FAILED", "error": message})

            success = bool(orders) and all(order.get("status") != "FAILED" for order in orders)
            if success:
                self._auto_buy_last_order_time = self._now_iso()

            return {
                "success": success,
                "orders": orders,
                "error": "; ".join(error_messages) if error_messages else None,
                "source": "task_auto_buy",
                "strategy_id": strategy_id,
            }
        finally:
            self._auto_buy_is_ordering = False
            await self._publish_auto_buy_state()

    async def _get_auto_buy_config_snapshot(self) -> dict[str, Any]:
        async with self._config_lock:
            auto_buy = self.config.auto_buy if isinstance(self.config.auto_buy, dict) else {}
            return copy.deepcopy(auto_buy)

    def _resolve_target_outcomes(self, side: str) -> list[str]:
        if side == self.BOTH_SIDE:
            return list(self._token_by_outcome.keys())
        if side in self._token_by_outcome:
            return [side]
        return []

    def _update_token_mapping(self, payload: dict[str, Any]) -> None:
        tokens = payload.get("tokens")
        if not isinstance(tokens, list):
            return

        mapping: dict[str, str] = {}
        reverse: dict[str, str] = {}

        for token in tokens:
            if not isinstance(token, dict):
                continue
            outcome = str(token.get("outcome") or "").strip()
            token_id = str(token.get("token_id") or "").strip()
            if not outcome or not token_id:
                continue
            mapping[outcome] = token_id
            reverse[token_id] = outcome

        if mapping:
            self._token_by_outcome = mapping
            self._outcome_by_token = reverse

    def _update_best_ask(self, payload: dict[str, Any]) -> None:
        asset_id = payload.get("asset_id") or payload.get("assetId") or payload.get("token_id") or payload.get("tokenId")
        if not isinstance(asset_id, str) or not asset_id:
            return

        asks = payload.get("asks") or payload.get("sells") or []
        if not isinstance(asks, list) or not asks:
            return

        best_ask = self._extract_best_ask(asks)
        if best_ask is None:
            return

        self._best_ask_by_token[asset_id] = best_ask

    @staticmethod
    def _extract_best_ask(asks: list[Any]) -> Optional[float]:
        values: list[float] = []
        for ask in asks:
            price: Optional[float] = None
            if isinstance(ask, dict):
                raw = ask.get("price")
                if raw is not None:
                    try:
                        price = float(raw)
                    except (TypeError, ValueError):
                        price = None
            elif isinstance(ask, (list, tuple)) and len(ask) >= 1:
                try:
                    price = float(ask[0])
                except (TypeError, ValueError):
                    price = None

            if price is None:
                continue
            if 0 < price < 1:
                values.append(price)

        if not values:
            return None
        return min(values)

    @staticmethod
    def _calculate_size(amount: float, price: float, round_size: bool) -> float:
        if price <= 0 or price >= 1:
            return 0.0

        raw_size = amount / price
        if round_size:
            return float(int(raw_size))
        return float(int(raw_size * 100) / 100)

    def _record_auto_buy_stat(self, outcome: str, amount: float) -> None:
        if outcome not in self._auto_buy_stats:
            self._auto_buy_stats[outcome] = {"count": 0, "amount": 0.0}
        self._auto_buy_stats[outcome]["count"] += 1
        self._auto_buy_stats[outcome]["amount"] += amount

    async def _publish_auto_buy_state(self) -> None:
        cfg = await self._get_auto_buy_config_snapshot()
        payload = {
            "enabled": bool(cfg.get("enabled", False)),
            "is_ordering": self._auto_buy_is_ordering,
            "last_order_time": self._auto_buy_last_order_time,
            "stats": self._auto_buy_stats,
            "default": cfg.get("default", {}),
            "strategy_rules": cfg.get("strategy_rules", {}),
            "timestamp": self._now_iso(),
        }
        await self._publish_event(f"event: auto_buy_state\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n")

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

    @staticmethod
    def _parse_sse_event(event: str) -> tuple[Optional[str], Optional[dict[str, Any]]]:
        event_type: Optional[str] = None
        data_payload: Optional[str] = None

        for line in event.splitlines():
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:") and data_payload is None:
                data_payload = line[5:].strip()

        if not event_type or not data_payload:
            return None, None

        try:
            parsed = json.loads(data_payload)
        except Exception:
            return event_type, None

        if not isinstance(parsed, dict):
            return event_type, None

        return event_type, parsed

    @staticmethod
    def _format_sse_event(event_type: str, payload: dict[str, Any]) -> str:
        return f"event: {event_type}\\ndata: {json.dumps(payload, ensure_ascii=False)}\\n\\n"

    @staticmethod
    def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in patch.items():
            current = merged.get(key)
            if isinstance(current, dict) and isinstance(value, dict):
                merged[key] = GameTask._deep_merge_dict(current, value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _now_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

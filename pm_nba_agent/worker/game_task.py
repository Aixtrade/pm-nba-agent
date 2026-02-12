"""单场比赛任务封装"""

import asyncio
import copy
import json
from datetime import datetime
import time
from typing import Any, Optional

from loguru import logger

from pm_nba_agent.api.models.requests import LiveStreamRequest
from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.api.services.game_stream import GameStreamService
from pm_nba_agent.agent import GameAnalyzer
from pm_nba_agent.polymarket.models import PositionContext
from pm_nba_agent.polymarket.orders import create_polymarket_order
from pm_nba_agent.polymarket.positions import get_current_positions
from pm_nba_agent.shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus


class GameTask:
    """单场比赛后台任务"""

    SNAPSHOT_EVENTS = {
        "polymarket_info",
        "polymarket_book",
        "scoreboard",
        "auto_buy_state",
        "auto_sell_state",
        "position_state",
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
        self._best_bid_by_token: dict[str, float] = {}
        self._auto_buy_is_ordering = False
        self._auto_buy_last_order_time: Optional[str] = None
        self._auto_buy_stats: dict[str, dict[str, Any]] = {}
        self._market_condition_id: Optional[str] = None
        self._market_outcomes: list[str] = []

        # Positions 运行态
        self._position_sides: list[dict[str, Any]] = []
        self._positions_loading = False
        self._positions_updated_at: Optional[str] = None
        self._position_refresh_task: Optional[asyncio.Task] = None
        self._position_refresh_lock = asyncio.Lock()
        self._last_position_refresh_at = 0.0
        self._initial_position_refresh_done = False

        # AutoSell 运行态
        self._auto_sell_is_ordering = False
        self._auto_sell_last_order_time: Optional[str] = None
        self._auto_sell_stats: dict[str, dict[str, Any]] = {}
        self._auto_sell_last_sell_time: dict[str, str] = {}

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

        async with self._config_lock:
            merged = self._deep_merge_dict(self.config.to_dict(), patch)
            self.config = TaskConfig.from_dict(merged)

        new_auto_sell_enabled = bool(
            self.config.auto_sell.get("enabled", False)
            if isinstance(self.config.auto_sell, dict)
            else False
        )

        await self._publish_auto_buy_state()
        await self._publish_auto_sell_state()
        if not old_auto_sell_enabled and new_auto_sell_enabled:
            await self.refresh_positions_once(force=True)

    async def run(self) -> None:
        """运行任务"""
        status = await self._load_or_create_status()
        status.update_state(TaskState.RUNNING)
        await self._save_status(status)
        await self._publish_status(status)
        await self._publish_auto_buy_state()
        await self._publish_auto_sell_state()
        await self._publish_position_state()
        self._position_refresh_task = asyncio.create_task(self._position_refresh_loop())
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
            enable_analysis=self.config.enable_analysis,
            analysis_interval=self.config.analysis_interval,
            strategy_ids=self.config.strategy_ids,
            strategy_params_map=self.config.strategy_params_map,
            strategy_id=self.config.strategy_id,
            strategy_params=self.config.strategy_params,
            proxy_address=self.config.proxy_address,
        )

        # 创建流服务
        stream_service = GameStreamService(
            self.fetcher,
            self.analyzer,
            position_provider=self._get_strategy_position_context,
            analysis_enabled_fn=lambda: self.config.enable_analysis,
        )

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
            if not self._initial_position_refresh_done:
                await self.refresh_positions_once(force=True)
                self._initial_position_refresh_done = True
            return event

        if event_type == "polymarket_book":
            self._update_best_prices(payload)
            await self._maybe_execute_auto_sell()
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
            self._market_outcomes = list(mapping.keys())
            condition_id = payload.get("condition_id")
            if isinstance(condition_id, str) and condition_id:
                self._market_condition_id = condition_id

            market_info = payload.get("market_info")
            if isinstance(market_info, dict):
                nested_condition_id = market_info.get("condition_id")
                if isinstance(nested_condition_id, str) and nested_condition_id:
                    self._market_condition_id = nested_condition_id
                raw_outcomes = market_info.get("outcomes")
                if isinstance(raw_outcomes, list):
                    normalized_outcomes = [
                        str(outcome).strip()
                        for outcome in raw_outcomes
                        if str(outcome).strip()
                    ]
                    if normalized_outcomes:
                        self._market_outcomes = normalized_outcomes

    def _update_best_prices(self, payload: dict[str, Any]) -> None:
        price_changes = payload.get("price_changes")
        if isinstance(price_changes, list) and price_changes:
            for change in price_changes:
                if not isinstance(change, dict):
                    continue
                asset_id = change.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    continue
                best_bid = change.get("best_bid")
                best_ask = change.get("best_ask")
                try:
                    bid_value = float(best_bid) if best_bid is not None else None
                except (TypeError, ValueError):
                    bid_value = None
                try:
                    ask_value = float(best_ask) if best_ask is not None else None
                except (TypeError, ValueError):
                    ask_value = None

                if bid_value is not None and 0 < bid_value < 1:
                    self._best_bid_by_token[asset_id] = bid_value
                if ask_value is not None and 0 < ask_value < 1:
                    self._best_ask_by_token[asset_id] = ask_value
            return

        asset_id = payload.get("asset_id") or payload.get("assetId") or payload.get("token_id") or payload.get("tokenId")
        if not isinstance(asset_id, str) or not asset_id:
            return

        bids = payload.get("bids") or payload.get("buys") or []
        asks = payload.get("asks") or payload.get("sells") or []

        if isinstance(bids, list) and bids:
            best_bid = self._extract_best_bid(bids)
            if best_bid is not None:
                self._best_bid_by_token[asset_id] = best_bid

        if isinstance(asks, list) and asks:
            best_ask = self._extract_best_ask(asks)
            if best_ask is not None:
                self._best_ask_by_token[asset_id] = best_ask

    @staticmethod
    def _extract_best_bid(bids: list[Any]) -> Optional[float]:
        values: list[float] = []
        for bid in bids:
            price: Optional[float] = None
            if isinstance(bid, dict):
                raw = bid.get("price")
                if raw is not None:
                    try:
                        price = float(raw)
                    except (TypeError, ValueError):
                        price = None
            elif isinstance(bid, (list, tuple)) and len(bid) >= 1:
                try:
                    price = float(bid[0])
                except (TypeError, ValueError):
                    price = None

            if price is None:
                continue
            if 0 < price < 1:
                values.append(price)

        if not values:
            return None
        return max(values)

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
        await self._publish_event(f"event: auto_buy_state\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n")

    async def _get_auto_sell_config_snapshot(self) -> dict[str, Any]:
        async with self._config_lock:
            auto_sell = self.config.auto_sell if isinstance(self.config.auto_sell, dict) else {}
            return copy.deepcopy(auto_sell)

    async def _publish_auto_sell_state(self) -> None:
        cfg = await self._get_auto_sell_config_snapshot()
        payload = {
            "enabled": bool(cfg.get("enabled", False)),
            "is_ordering": self._auto_sell_is_ordering,
            "last_order_time": self._auto_sell_last_order_time,
            "last_sell_time": self._auto_sell_last_sell_time,
            "stats": self._auto_sell_stats,
            "default": cfg.get("default", {}),
            "outcome_rules": cfg.get("outcome_rules", {}),
            "timestamp": self._now_iso(),
        }
        await self._publish_event(f"event: auto_sell_state\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n")

    async def _publish_auto_sell_execution(
        self,
        success: bool,
        orders: list[dict[str, Any]],
        error: Optional[str] = None,
    ) -> None:
        payload = {
            "success": success,
            "orders": orders,
            "error": error,
            "source": "task_auto_sell",
            "timestamp": self._now_iso(),
        }
        await self._publish_event(f"event: auto_sell_execution\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n")

    async def _publish_position_state(self) -> None:
        payload = {
            "sides": self._position_sides,
            "loading": self._positions_loading,
            "updated_at": self._positions_updated_at,
            "condition_id": self._market_condition_id,
            "timestamp": self._now_iso(),
        }
        await self._publish_event(f"event: position_state\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n")

    async def _position_refresh_loop(self) -> None:
        while not self._cancelled:
            cfg = await self._get_auto_sell_config_snapshot()
            default_cfg = cfg.get("default", {}) if isinstance(cfg.get("default"), dict) else {}
            refresh_interval = float(default_cfg.get("refresh_interval", 3.0))
            refresh_interval = max(1.0, min(refresh_interval, 60.0))
            should_refresh = bool(
                cfg.get("enabled", False)
                and self._market_condition_id
                and self.config.proxy_address
            )

            if should_refresh:
                await self.refresh_positions_once()

            await asyncio.sleep(refresh_interval)

    async def refresh_positions_once(self, force: bool = False) -> None:
        if not force and not self._should_refresh_positions_now():
            return

        if self._position_refresh_lock.locked():
            return

        async with self._position_refresh_lock:
            self._last_position_refresh_at = time.monotonic()
            await self._refresh_positions()

    def _should_refresh_positions_now(self) -> bool:
        interval = self._get_position_refresh_interval()
        min_gap = max(0.8, min(interval * 0.6, 5.0))
        return (time.monotonic() - self._last_position_refresh_at) >= min_gap

    def _get_position_refresh_interval(self) -> float:
        auto_sell = self.config.auto_sell if isinstance(self.config.auto_sell, dict) else {}
        default_cfg = auto_sell.get("default") if isinstance(auto_sell.get("default"), dict) else {}
        refresh_interval = float(default_cfg.get("refresh_interval", 3.0))
        return max(1.0, min(refresh_interval, 60.0))

    async def _refresh_positions(self) -> None:
        if not self._market_condition_id:
            return
        if not self.config.proxy_address:
            return

        self._positions_loading = True
        await self._publish_position_state()

        try:
            positions = await get_current_positions(
                user_address=self.config.proxy_address,
                condition_ids=[self._market_condition_id],
                proxy_address=self.config.proxy_address,
            )
            if not isinstance(positions, list):
                return

            sides = self._build_position_sides(positions, self._market_outcomes)
            self._position_sides = sides
            self._positions_updated_at = self._now_iso()
        except Exception as exc:
            logger.error("刷新持仓失败 task={}: {}", self.task_id, exc)
        finally:
            self._positions_loading = False
            await self._publish_position_state()

    async def _maybe_execute_auto_sell(self) -> None:
        cfg = await self._get_auto_sell_config_snapshot()
        if not cfg.get("enabled", False):
            return
        if self._auto_sell_is_ordering:
            return
        if not self.config.private_key or not self.config.proxy_address:
            return

        default_cfg = cfg.get("default", {}) if isinstance(cfg.get("default"), dict) else {}
        max_stale_seconds = float(default_cfg.get("max_stale_seconds", 7.0))
        if self._positions_updated_at is None or self._is_stale(max_stale_seconds):
            await self.refresh_positions_once()
            if self._positions_updated_at is None or self._is_stale(max_stale_seconds):
                return

        outcome_rules = cfg.get("outcome_rules", {}) if isinstance(cfg.get("outcome_rules"), dict) else {}
        candidates: list[dict[str, Any]] = []
        for side in self._position_sides:
            outcome = str(side.get("outcome") or "").strip()
            if not outcome:
                continue

            rule = outcome_rules.get(outcome, {})
            if not isinstance(rule, dict) or not rule.get("enabled", False):
                continue

            size = float(side.get("size", 0) or 0)
            avg_price = side.get("avg_price")
            avg = float(avg_price) if avg_price is not None else 0.0
            if size <= 0 or avg <= 0:
                continue

            token_id = self._token_by_outcome.get(outcome)
            if not token_id:
                continue
            best_bid = self._best_bid_by_token.get(token_id)
            if best_bid is None or best_bid <= 0 or best_bid >= 1:
                continue

            profit_rate = self._calculate_profit_rate(avg, best_bid)
            min_profit_rate = float(rule.get("min_profit_rate", default_cfg.get("min_profit_rate", 5.0)))
            if profit_rate < (min_profit_rate / 100.0):
                continue

            cooldown_time = float(rule.get("cooldown_time", default_cfg.get("cooldown_time", 30.0)))
            last_sell_iso = self._auto_sell_last_sell_time.get(outcome)
            if last_sell_iso and self._seconds_since_iso(last_sell_iso) < cooldown_time:
                continue

            sell_ratio = float(rule.get("sell_ratio", default_cfg.get("sell_ratio", 100.0)))
            sell_size = float(int(size * (sell_ratio / 100.0) * 100) / 100.0)
            if sell_size <= 0:
                continue

            order_type = str(rule.get("order_type", default_cfg.get("order_type", "GTC")))
            candidates.append({
                "outcome": outcome,
                "token_id": token_id,
                "price": best_bid,
                "size": sell_size,
                "order_type": order_type,
                "profit_rate": profit_rate,
            })

        if not candidates:
            return

        self._auto_sell_is_ordering = True
        await self._publish_auto_sell_state()

        success_count = 0
        orders: list[dict[str, Any]] = []
        error_messages: list[str] = []
        try:
            for order in candidates:
                outcome = order["outcome"]
                now = self._now_iso()
                previous = self._auto_sell_last_sell_time.get(outcome)
                self._auto_sell_last_sell_time[outcome] = now

                try:
                    await create_polymarket_order(
                        token_id=order["token_id"],
                        side="SELL",
                        price=float(order["price"]),
                        size=float(order["size"]),
                        order_type=str(order["order_type"]),
                        private_key=self.config.private_key,
                        proxy_address=self.config.proxy_address,
                    )
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "SUBMITTED",
                    })
                    self._record_auto_sell_stat(outcome, float(order["size"]) * float(order["price"]))
                    success_count += 1
                except Exception as exc:
                    logger.error("自动卖出失败 task={} outcome={}: {}", self.task_id, outcome, exc)
                    message = str(exc)
                    error_messages.append(message)
                    orders.append({
                        **order,
                        "side": "SELL",
                        "status": "FAILED",
                        "error": message,
                    })
                    if previous:
                        self._auto_sell_last_sell_time[outcome] = previous
                    else:
                        self._auto_sell_last_sell_time.pop(outcome, None)

            success = success_count > 0 and all(item.get("status") != "FAILED" for item in orders)
            await self._publish_auto_sell_execution(
                success=success,
                orders=orders,
                error="; ".join(error_messages) if error_messages else None,
            )
            if success_count > 0:
                self._auto_sell_last_order_time = self._now_iso()
                await asyncio.sleep(2.0)
                await self.refresh_positions_once()
        finally:
            self._auto_sell_is_ordering = False
            await self._publish_auto_sell_state()

    @staticmethod
    def _build_position_sides(positions: list[dict[str, Any]], outcomes: list[str] | None) -> list[dict[str, Any]]:
        sizes: dict[str, float] = {}
        initial_values: dict[str, float] = {}
        avg_prices: dict[str, float | None] = {}
        cur_prices: dict[str, float | None] = {}

        for position in positions:
            outcome = str(position.get("outcome") or "").strip()
            if outcome:
                size_value = position.get("size", 0)
                try:
                    size = float(size_value)
                except (TypeError, ValueError):
                    size = 0.0
                sizes[outcome] = sizes.get(outcome, 0.0) + size

                initial_value = position.get("initialValue", 0)
                try:
                    cost = float(initial_value)
                except (TypeError, ValueError):
                    cost = 0.0
                initial_values[outcome] = initial_values.get(outcome, 0.0) + cost

                if outcome not in avg_prices:
                    avg_value = position.get("avgPrice")
                    if avg_value is not None:
                        try:
                            avg_prices[outcome] = float(avg_value)
                        except (TypeError, ValueError):
                            avg_prices[outcome] = None

                if outcome not in cur_prices:
                    cur_value = position.get("curPrice")
                    if cur_value is not None:
                        try:
                            cur_prices[outcome] = float(cur_value)
                        except (TypeError, ValueError):
                            cur_prices[outcome] = None

            opposite_outcome = str(position.get("oppositeOutcome") or "").strip()
            if opposite_outcome and opposite_outcome not in sizes:
                sizes[opposite_outcome] = 0.0
                initial_values[opposite_outcome] = 0.0

        if outcomes:
            for outcome in outcomes:
                if outcome not in sizes:
                    sizes[outcome] = 0.0
                if outcome not in initial_values:
                    initial_values[outcome] = 0.0

        ordered_outcomes = outcomes or list(sizes.keys())
        return [
            {
                "outcome": outcome,
                "size": sizes.get(outcome, 0.0),
                "initial_value": initial_values.get(outcome, 0.0),
                "avg_price": avg_prices.get(outcome),
                "cur_price": cur_prices.get(outcome),
            }
            for outcome in ordered_outcomes
        ]

    @staticmethod
    def _calculate_profit_rate(avg_price: float, current_price: float) -> float:
        if avg_price <= 0:
            return -1.0
        return (current_price - avg_price) / avg_price

    def _record_auto_sell_stat(self, outcome: str, amount: float) -> None:
        if outcome not in self._auto_sell_stats:
            self._auto_sell_stats[outcome] = {"count": 0, "amount": 0.0}
        self._auto_sell_stats[outcome]["count"] += 1
        self._auto_sell_stats[outcome]["amount"] += amount

    async def _get_strategy_position_context(
        self,
        yes_token_id: str,
        no_token_id: str,
        max_stale_seconds: float,
    ) -> Optional[PositionContext]:
        if not yes_token_id or not no_token_id:
            return None

        stale_limit = max(1.0, float(max_stale_seconds))
        if self._positions_updated_at is None or self._is_stale(stale_limit):
            await self.refresh_positions_once()

        yes_outcome = self._outcome_by_token.get(yes_token_id)
        no_outcome = self._outcome_by_token.get(no_token_id)
        if not yes_outcome or not no_outcome:
            return PositionContext()

        yes_side = self._find_position_side(yes_outcome)
        no_side = self._find_position_side(no_outcome)

        yes_size = float(yes_side.get("size", 0.0)) if yes_side else 0.0
        no_size = float(no_side.get("size", 0.0)) if no_side else 0.0
        yes_avg = float(yes_side.get("avg_price", 0.0) or 0.0) if yes_side else 0.0
        no_avg = float(no_side.get("avg_price", 0.0) or 0.0) if no_side else 0.0

        yes_initial = float(yes_side.get("initial_value", 0.0) or 0.0) if yes_side else 0.0
        no_initial = float(no_side.get("initial_value", 0.0) or 0.0) if no_side else 0.0

        yes_total_cost = yes_initial if yes_initial > 0 else yes_size * yes_avg
        no_total_cost = no_initial if no_initial > 0 else no_size * no_avg

        return PositionContext(
            yes_size=yes_size,
            no_size=no_size,
            yes_avg_cost=yes_avg,
            no_avg_cost=no_avg,
            yes_total_cost=yes_total_cost,
            no_total_cost=no_total_cost,
        )

    def _find_position_side(self, outcome: str) -> Optional[dict[str, Any]]:
        for side in self._position_sides:
            if str(side.get("outcome") or "") == outcome:
                return side
        return None

    def _is_stale(self, max_stale_seconds: float) -> bool:
        if not self._positions_updated_at:
            return True
        return self._seconds_since_iso(self._positions_updated_at) > max_stale_seconds

    @staticmethod
    def _seconds_since_iso(value: str) -> float:
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo)
            return max(0.0, (now - ts).total_seconds())
        except Exception:
            return 10 ** 9

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

    async def _load_or_create_status(self) -> TaskStatus:
        """加载已有状态，避免覆盖 created_at/user_id 等字段"""
        key = Channels.task_status(self.task_id)
        data = await self.redis.get(key)
        if not data:
            return TaskStatus.create(self.task_id)
        try:
            return TaskStatus.from_json(data)
        except Exception:
            return TaskStatus.create(self.task_id)

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
        return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

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

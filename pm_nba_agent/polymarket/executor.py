"""Polymarket 策略执行器"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from loguru import logger

from .book_stream import PolymarketBookStream
from .models import (
    MarketSnapshot,
    OrderBookContext,
    PositionContext,
    SideData,
    OrderLevel,
    SignalEvent,
)
from .orders import create_polymarket_order
from .positions import get_current_positions
from .strategies import StrategyRegistry, TradingSignal, SignalType


class ExecutionMode(Enum):
    """执行模式"""

    SIMULATION = "SIMULATION"  # 模拟模式，仅打印订单
    REAL = "REAL"  # 真实模式，提交订单


@dataclass
class ExecutorConfig:
    """执行器配置"""

    strategy_id: str = "merge_long"
    strategy_params: dict[str, Any] = field(default_factory=dict)
    execution_mode: ExecutionMode = ExecutionMode.SIMULATION
    order_type: str = "GTC"
    min_order_amount: float = 1.0
    total_budget: float = 100.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutorConfig":
        mode_str = data.get("execution_mode", "SIMULATION")
        if isinstance(mode_str, str):
            mode = ExecutionMode(mode_str.upper())
        else:
            mode = mode_str

        return cls(
            strategy_id=data.get("strategy_id", "merge_long"),
            strategy_params=data.get("strategy_params", {}),
            execution_mode=mode,
            order_type=data.get("order_type", "GTC"),
            min_order_amount=data.get("min_order_amount", 1.0),
            total_budget=data.get("total_budget", 100.0),
        )


@dataclass
class ExecutionResult:
    """执行结果"""

    success: bool
    signal: Optional[TradingSignal]
    orders_placed: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "signal": self.signal.to_dict() if self.signal else None,
            "orders_placed": self.orders_placed,
            "error": self.error,
        }


class StrategyExecutor:
    """策略执行器

    负责：
    1. 订阅订单簿数据
    2. 调用策略生成信号
    3. 执行订单
    4. 维护持仓状态

    Example:
        executor = StrategyExecutor(
            yes_token_id="12345",
            no_token_id="67890",
            config=ExecutorConfig(
                strategy_id="my_strategy",
                execution_mode=ExecutionMode.SIMULATION,
            ),
        )

        await executor.start()
        # ... 运行中 ...
        await executor.stop()
    """

    def __init__(
        self,
        yes_token_id: str,
        no_token_id: str,
        config: Optional[ExecutorConfig] = None,
        on_signal: Optional[Callable[[TradingSignal, ExecutionResult], None]] = None,
        on_snapshot: Optional[Callable[[MarketSnapshot], None]] = None,
        on_event: Optional[Callable[[SignalEvent], None]] = None,
    ) -> None:
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self.config = config or ExecutorConfig()

        self.on_signal = on_signal
        self.on_snapshot = on_snapshot
        self.on_event = on_event

        self._book_stream = PolymarketBookStream()
        self._last_snapshot: Optional[MarketSnapshot] = None
        self._position = PositionContext()
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._event_task: Optional[asyncio.Task[None]] = None
        self._event_queue: asyncio.Queue[SignalEvent] = asyncio.Queue()

        # 订单簿缓存
        self._yes_bids: list[OrderLevel] = []
        self._yes_asks: list[OrderLevel] = []
        self._no_bids: list[OrderLevel] = []
        self._no_asks: list[OrderLevel] = []
        self._yes_price: float = 0.0
        self._no_price: float = 0.0

    @property
    def position(self) -> PositionContext:
        """当前持仓上下文"""
        return self._position

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> bool:
        """启动执行器"""
        if self._running:
            logger.warning("执行器已在运行")
            return False

        # 加载策略
        strategy = StrategyRegistry.get(self.config.strategy_id)
        if strategy is None:
            logger.error("策略加载失败: {}", self.config.strategy_id)
            return False

        # 初始化持仓
        await self._sync_position()

        # 启动订单簿订阅
        asset_ids = [self.yes_token_id, self.no_token_id]
        connected = await self._book_stream.start(asset_ids)
        if not connected:
            logger.error("订单簿订阅失败")
            return False

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self._event_task = asyncio.create_task(self._event_dispatcher())
        logger.info(
            "执行器已启动: strategy={}, mode={}",
            self.config.strategy_id,
            self.config.execution_mode.value,
        )
        return True

    async def stop(self) -> None:
        """停止执行器"""
        self._running = False

        # 停止主循环任务
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # 停止事件分发任务
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
            self._event_task = None

        # 清空事件队列
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        await self._book_stream.close()
        logger.info("执行器已停止")

    async def _sync_position(self) -> None:
        """从 API 同步持仓"""
        try:
            positions = await get_current_positions()
            if positions:
                self._position = PositionContext.from_api_positions(
                    positions,
                    self.yes_token_id,
                    self.no_token_id,
                )
                logger.info(
                    "持仓同步完成: YES=%.2f, NO=%.2f",
                    self._position.yes_size,
                    self._position.no_size,
                )
        except Exception as exc:
            logger.warning("持仓同步失败: {}", exc)

    async def _event_dispatcher(self) -> None:
        """事件分发任务：从队列取出事件并推送给回调"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0,
                )
                if self.on_event:
                    try:
                        self.on_event(event)
                    except Exception as exc:
                        logger.warning("事件回调失败: {}", exc)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("事件分发失败: {}", exc)

    async def _run_loop(self) -> None:
        """主循环：处理订单簿消息"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._book_stream.queue.get(),
                    timeout=30.0,
                )
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("消息处理失败: {}", exc)

    async def _handle_message(self, message: Any) -> None:
        """处理订单簿消息"""
        if not isinstance(message, dict):
            return

        # 解析消息类型
        msg_type = message.get("event_type") or message.get("type")
        if msg_type not in ("book", "price_change", "last_trade_price"):
            return

        # 更新订单簿缓存
        self._update_order_book(message)

        # 构建快照
        snapshot = self._build_snapshot(message)
        if snapshot is None:
            return

        self._last_snapshot = snapshot

        # 回调
        if self.on_snapshot:
            try:
                self.on_snapshot(snapshot)
            except Exception as exc:
                logger.warning("on_snapshot 回调失败: {}", exc)

        # 执行策略
        result = await self._execute_strategy(snapshot)
        if result and result.signal:
            # 旧回调（兼容）
            if self.on_signal:
                try:
                    self.on_signal(result.signal, result)
                except Exception as exc:
                    logger.warning("on_signal 回调失败: {}", exc)

            # 新事件推送（通过队列异步分发）
            try:
                event = self._build_signal_event(result, snapshot)
                self._enqueue_event(event)
            except Exception as exc:
                logger.warning("事件入队失败: {}", exc)

    def _update_order_book(self, message: dict[str, Any]) -> None:
        """更新订单簿缓存"""
        asset_id = message.get("asset_id")
        if not asset_id:
            return

        # 解析买卖盘
        bids = message.get("bids") or message.get("buys") or []
        asks = message.get("asks") or message.get("sells") or []

        bid_levels = [OrderLevel.from_raw(b) for b in bids if isinstance(b, dict)]
        ask_levels = [OrderLevel.from_raw(a) for a in asks if isinstance(a, dict)]

        # 获取价格
        price = float(message.get("price", 0) or message.get("last_price", 0) or 0)

        if asset_id == self.yes_token_id:
            if bid_levels:
                self._yes_bids = bid_levels
            if ask_levels:
                self._yes_asks = ask_levels
            if price > 0:
                self._yes_price = price
        elif asset_id == self.no_token_id:
            if bid_levels:
                self._no_bids = bid_levels
            if ask_levels:
                self._no_asks = ask_levels
            if price > 0:
                self._no_price = price

    def _build_snapshot(self, message: dict[str, Any]) -> Optional[MarketSnapshot]:
        """构建市场快照"""
        if not self._yes_price and not self._no_price:
            return None

        yes_data = SideData(
            token_id=self.yes_token_id,
            price=self._yes_price,
            bids=self._yes_bids.copy(),
            asks=self._yes_asks.copy(),
        )
        no_data = SideData(
            token_id=self.no_token_id,
            price=self._no_price,
            bids=self._no_bids.copy(),
            asks=self._no_asks.copy(),
        )

        return MarketSnapshot(
            yes_data=yes_data,
            no_data=no_data,
            timestamp=message.get("timestamp"),
            raw_message=message,
        )

    async def _execute_strategy(
        self,
        snapshot: MarketSnapshot,
    ) -> Optional[ExecutionResult]:
        """执行策略并处理信号"""
        strategy = StrategyRegistry.get(self.config.strategy_id)
        if strategy is None:
            return None

        order_book = OrderBookContext.from_snapshot(snapshot)

        # 生成信号
        try:
            signal = strategy.generate_signal(
                snapshot=snapshot,
                order_book=order_book,
                position=self._position,
                params=self.config.strategy_params,
            )
        except Exception as exc:
            logger.error("策略执行失败: {}", exc)
            return ExecutionResult(success=False, signal=None, error=str(exc))

        if signal is None:
            return None

        # HOLD 信号不执行
        if signal.signal_type == SignalType.HOLD:
            logger.debug("HOLD: {}", signal.reason)
            return ExecutionResult(success=True, signal=signal)

        # 验证信号
        valid, reason = strategy.validate_signal(
            signal, order_book, self._position, self.config.strategy_params
        )
        if not valid:
            logger.warning("信号验证失败: {}", reason)
            return ExecutionResult(success=False, signal=signal, error=reason)

        # 执行订单
        return await self._execute_signal(signal)

    async def _execute_signal(self, signal: TradingSignal) -> ExecutionResult:
        """执行交易信号"""
        orders_placed: list[dict[str, Any]] = []

        # 确定交易方向
        side = "BUY" if signal.signal_type == SignalType.BUY else "SELL"

        # YES 方向订单
        if signal.yes_size and signal.yes_size >= self.config.min_order_amount:
            if signal.yes_price is None:
                return ExecutionResult(
                    success=False,
                    signal=signal,
                    error="YES 订单缺少价格",
                )

            order_info = {
                "token_id": self.yes_token_id,
                "side": side,
                "size": signal.yes_size,
                "price": signal.yes_price,
                "order_type": self.config.order_type,
            }

            if self.config.execution_mode == ExecutionMode.SIMULATION:
                logger.info(
                    "[模拟] YES {}: size={:.2f}, price={:.4f}",
                    side,
                    signal.yes_size,
                    signal.yes_price,
                )
                orders_placed.append({**order_info, "status": "SIMULATED"})
                # 模拟模式也更新持仓
                self._position.update_position(
                    "YES", signal.yes_size, signal.yes_price, is_buy=(side == "BUY")
                )
            else:
                try:
                    result = await create_polymarket_order(
                        token_id=self.yes_token_id,
                        side=side,
                        price=signal.yes_price,
                        size=signal.yes_size,
                        order_type=self.config.order_type,
                    )
                    orders_placed.append({**order_info, "result": result, "status": "SUBMITTED"})
                    self._position.update_position(
                        "YES", signal.yes_size, signal.yes_price, is_buy=(side == "BUY")
                    )
                    logger.info("YES {} 订单已提交: {}", side, result)
                except Exception as exc:
                    logger.error("YES 订单失败: {}", exc)
                    orders_placed.append({**order_info, "error": str(exc), "status": "FAILED"})

        # NO 方向订单
        if signal.no_size and signal.no_size >= self.config.min_order_amount:
            if signal.no_price is None:
                return ExecutionResult(
                    success=False,
                    signal=signal,
                    orders_placed=orders_placed,
                    error="NO 订单缺少价格",
                )

            order_info = {
                "token_id": self.no_token_id,
                "side": side,
                "size": signal.no_size,
                "price": signal.no_price,
                "order_type": self.config.order_type,
            }

            if self.config.execution_mode == ExecutionMode.SIMULATION:
                logger.info(
                    "[模拟] NO {}: size={:.2f}, price={:.4f}",
                    side,
                    signal.no_size,
                    signal.no_price,
                )
                orders_placed.append({**order_info, "status": "SIMULATED"})
                self._position.update_position(
                    "NO", signal.no_size, signal.no_price, is_buy=(side == "BUY")
                )
            else:
                try:
                    result = await create_polymarket_order(
                        token_id=self.no_token_id,
                        side=side,
                        price=signal.no_price,
                        size=signal.no_size,
                        order_type=self.config.order_type,
                    )
                    orders_placed.append({**order_info, "result": result, "status": "SUBMITTED"})
                    self._position.update_position(
                        "NO", signal.no_size, signal.no_price, is_buy=(side == "BUY")
                    )
                    logger.info("NO {} 订单已提交: {}", side, result)
                except Exception as exc:
                    logger.error("NO 订单失败: {}", exc)
                    orders_placed.append({**order_info, "error": str(exc), "status": "FAILED"})

        success = all(o.get("status") != "FAILED" for o in orders_placed)
        return ExecutionResult(
            success=success,
            signal=signal,
            orders_placed=orders_placed,
        )

    def _build_signal_event(
        self,
        result: ExecutionResult,
        snapshot: MarketSnapshot,
    ) -> SignalEvent:
        """构建信号事件"""
        signal = result.signal
        if signal is None:
            return SignalEvent.from_error("信号为空")

        return SignalEvent.from_signal(
            signal_type=signal.signal_type.value,
            reason=signal.reason,
            snapshot=snapshot,
            position=self._position,
            strategy_id=self.config.strategy_id,
            yes_size=signal.yes_size,
            no_size=signal.no_size,
            yes_price=signal.yes_price,
            no_price=signal.no_price,
            orders=result.orders_placed if result.orders_placed else None,
            success=result.success,
            error=result.error,
            metadata=signal.metadata,
        )

    def _enqueue_event(self, event: SignalEvent) -> None:
        """将事件放入队列（非阻塞）"""
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("事件队列已满，丢弃事件: {}", event.event_type)

    def emit_event(self, event: SignalEvent) -> None:
        """手动发送事件（通过队列异步分发）"""
        self._enqueue_event(event)

    def emit_status(self, message: str, data: Optional[dict[str, Any]] = None) -> None:
        """发送状态事件"""
        self.emit_event(SignalEvent.status(message, data))

    def emit_error(self, error: str, context: Optional[dict[str, Any]] = None) -> None:
        """发送错误事件"""
        self.emit_event(SignalEvent.from_error(error, context))

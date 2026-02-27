"""Robot 抽象基类与信号模型。"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from loguru import logger

from {package_name}.shared import Channels, RedisClient
from {package_name}.shared.channels import SignalType, StreamName

# 状态广播回调类型：接收状态字典，无返回值
StatusCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class RobotState(StrEnum):
    """机器人运行状态。"""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Signal:
    """统一信号格式。

    所有机器人之间通过 Signal 进行通信。
    Signal 通过 Redis Streams 传输，字段值均为字符串。
    """

    type: str                      # 信号类型（如 "data_update", "process_result"）
    source: str                    # 发送方机器人类型
    task_id: str                   # 所属任务 ID
    timestamp: str                 # ISO 时间戳
    data: dict[str, Any]           # 业务数据（JSON 序列化）
    schema_version: str = "1.0"    # 信号版本
    id: str = ""                   # Redis Stream 消息 ID（反序列化时填充）

    def to_fields(self) -> dict[str, str]:
        """序列化为 Redis Stream fields（值均为字符串）。"""
        return {
            "type": self.type,
            "source": self.source,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "data": json.dumps(self.data, ensure_ascii=False),
        }

    @classmethod
    def from_fields(cls, stream_id: str, fields: dict[str, str]) -> "Signal":
        """从 Redis Stream fields 反序列化。"""
        try:
            payload = json.loads(fields.get("data", "{}"))
            if not isinstance(payload, dict):
                payload = {"raw": payload}
        except Exception:
            payload = {}

        return cls(
            id=stream_id,
            type=fields.get("type", ""),
            source=fields.get("source", ""),
            task_id=fields.get("task_id", ""),
            timestamp=fields.get("timestamp", ""),
            schema_version=fields.get("schema_version", "1.0"),
            data=payload,
        )


@dataclass
class RobotStatus:
    """机器人状态快照。"""

    robot_type: str
    state: RobotState
    task_id: str
    signals_in: int = 0
    signals_out: int = 0
    last_error: str | None = None
    started_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "robot_type": self.robot_type,
            "state": self.state.value,
            "task_id": self.task_id,
            "signals_in": self.signals_in,
            "signals_out": self.signals_out,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


class BaseRobot(ABC):
    """机器人抽象基类。

    每个机器人都可以同时接收信号和发出信号。
    通过 input_streams / output_streams 声明订阅和发布的 stream。

    生命周期：__init__ → start() → run_loop() → stop()

    定时/并发逻辑由各机器人在 setup() 中用标准 asyncio 自行管理，
    在 teardown() 中负责清理：

        async def setup(self) -> None:
            self._loop_task = asyncio.create_task(self._my_loop())

        async def teardown(self) -> None:
            self._loop_task.cancel()
            await asyncio.gather(self._loop_task, return_exceptions=True)

        async def _my_loop(self) -> None:
            while not self._cancelled:
                await self.do_something()
                await asyncio.sleep(5.0)
    """

    def __init__(
        self,
        task_id: str,
        redis: RedisClient,
        config: dict[str, Any] | None = None,
        status_callback: StatusCallback | None = None,
    ):
        self.task_id = task_id
        self.redis = redis
        self.config = config or {}
        self._state = RobotState.IDLE
        self._signals_in = 0
        self._signals_out = 0
        self._last_error: str | None = None
        self._started_at: str | None = None
        self._cancelled = False
        self._status_callback = status_callback

    # ========== 抽象属性/方法（子类必须实现） ==========

    @property
    @abstractmethod
    def robot_type(self) -> str:
        """机器人类型标识。"""

    @abstractmethod
    async def setup(self) -> None:
        """初始化资源（连接外部服务、启动子任务等）。"""

    # ========== 子类声明（覆盖类变量即可） ==========

    input_streams: list[StreamName] = []
    """订阅的 stream 名列表。空列表表示不订阅任何 stream。"""

    output_streams: list[StreamName] = []
    """发布的 stream 名列表。空列表表示不发布到任何 stream。"""

    # ========== 可选覆盖 ==========

    async def on_signal(self, stream: str, signal: Signal) -> None:
        """处理输入信号。有 input_streams 时应覆盖此方法。"""

    async def teardown(self) -> None:
        """清理资源（关闭连接、释放锁等）。"""

    def get_runtime_metrics(self) -> dict[str, Any]:
        """返回机器人自定义运行指标（会随 robot_status 一起发送到前端）。"""
        return {}

    # ========== 生命周期管理 ==========

    async def start(self) -> None:
        """启动机器人。"""
        self._cancelled = False
        self._state = RobotState.RUNNING
        self._started_at = _now_iso()

        try:
            await self.setup()
            await self.emit(
                Channels.STREAM_CONTROL,
                SignalType.ROBOT_START,
                {"robot_type": self.robot_type},
            )
        except Exception as exc:
            self._state = RobotState.ERROR
            self._last_error = str(exc)
            logger.error("Robot {} setup 失败: {}", self.robot_type, exc)
            await self._broadcast_status()
            try:
                await self.emit(Channels.STREAM_CONTROL, SignalType.ROBOT_ERROR, {
                    "robot_type": self.robot_type,
                    "stage": "setup",
                    "error": str(exc),
                })
            except Exception:
                pass
            raise

        logger.info(
            "Robot 已启动: type={} task={} input={} output={}",
            self.robot_type,
            self.task_id,
            self.input_streams,
            self.output_streams,
        )

    async def stop(self) -> None:
        """停止机器人。"""
        self._cancelled = True
        try:
            await self.teardown()
        except Exception as exc:
            logger.warning("Robot {} teardown 异常: {}", self.robot_type, exc)

        self._state = RobotState.STOPPED
        await self._broadcast_status()
        try:
            await self.emit(
                Channels.STREAM_CONTROL,
                SignalType.ROBOT_STOP,
                {"robot_type": self.robot_type},
            )
        except Exception:
            pass
        logger.info("Robot 已停止: type={} task={}", self.robot_type, self.task_id)

    async def run_loop(self) -> None:
        """主运行循环。

        只负责消费 input_streams：持续 xread → on_signal。
        无 input_streams 的机器人（纯 Producer）依靠 setup() 中启动的异步任务驱动，
        run_loop 仅保持生命周期存活直到收到取消信号。
        """
        if self._state != RobotState.RUNNING:
            await self.start()

        stream_keys = [self._stream_key(name) for name in self.input_streams]
        last_ids: dict[str, str] = {key: "$" for key in stream_keys}

        try:
            while not self._cancelled:
                if stream_keys:
                    try:
                        results = await self.redis.xread(
                            streams=last_ids,
                            count=100,
                            block=1000,  # 固定 1s 超时，保证取消响应及时
                        )
                    except Exception as exc:
                        logger.warning("Robot {} xread 异常: {}", self.robot_type, exc)
                        self._last_error = str(exc)
                        await asyncio.sleep(1.0)
                        continue

                    for stream_key, messages in results:
                        stream_name = self._parse_stream_name(stream_key)
                        for msg_id, fields in messages:
                            last_ids[stream_key] = msg_id
                            signal = Signal.from_fields(msg_id, fields)
                            self._signals_in += 1
                            await self._broadcast_status()
                            try:
                                await self.on_signal(stream_name, signal)
                            except Exception as exc:
                                logger.warning(
                                    "Robot {} on_signal 异常: stream={} id={} err={}",
                                    self.robot_type,
                                    stream_name,
                                    msg_id,
                                    exc,
                                )
                                self._last_error = str(exc)
                                await self._broadcast_status()
                                await self.emit(
                                    Channels.STREAM_CONTROL,
                                    SignalType.ROBOT_ERROR,
                                    {
                                        "robot_type": self.robot_type,
                                        "stage": "on_signal",
                                        "stream": stream_name,
                                        "signal_id": msg_id,
                                        "error": str(exc),
                                    },
                                )
                else:
                    # 无 input_streams：等待取消信号，实际工作由机器人自身的异步任务驱动
                    await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._state = RobotState.ERROR
            self._last_error = str(exc)
            logger.error("Robot {} run_loop 异常: {}", self.robot_type, exc)
            await self._broadcast_status()
            try:
                await self.emit(Channels.STREAM_CONTROL, SignalType.ROBOT_ERROR, {
                    "robot_type": self.robot_type,
                    "stage": "run_loop",
                    "error": str(exc),
                })
            except Exception:
                pass
        finally:
            await self.stop()

    # ========== 信号发送 ==========

    async def emit(
        self,
        stream: StreamName | str,
        signal_type: SignalType | str,
        data: dict[str, Any],
        *,
        maxlen: int = 1000,
    ) -> str:
        """发出信号到指定 stream。"""
        signal = Signal(
            type=str(signal_type),
            source=self.robot_type,
            task_id=self.task_id,
            timestamp=_now_iso(),
            data=data,
        )
        msg_id = await self.redis.xadd(
            self._stream_key(str(stream)),
            signal.to_fields(),
            maxlen=maxlen,
        )
        self._signals_out += 1
        await self._broadcast_status()
        return msg_id

    # ========== 状态查询 ==========

    def get_status(self) -> RobotStatus:
        """获取当前状态快照。"""
        return RobotStatus(
            robot_type=self.robot_type,
            state=self._state,
            task_id=self.task_id,
            signals_in=self._signals_in,
            signals_out=self._signals_out,
            last_error=self._last_error,
            started_at=self._started_at,
            updated_at=_now_iso(),
        )

    async def _broadcast_status(self) -> None:
        """将当前状态快照推送给回调方（事件驱动，无回调则静默忽略）。"""
        if self._status_callback is None:
            return
        try:
            status = self.get_status().to_dict()
            status.update(self.get_runtime_metrics())
            status["timestamp"] = _now_iso()
            await self._status_callback(status)
        except Exception as exc:
            logger.warning("Robot {} 状态广播失败: {}", self.robot_type, exc)

    # ========== 内部方法 ==========

    def _stream_key(self, stream_name: str) -> str:
        return Channels.task_stream(self.task_id, stream_name)

    def _parse_stream_name(self, stream_key: str) -> str:
        prefix = f"{Channels.PREFIX}:task:{self.task_id}:stream:"
        if stream_key.startswith(prefix):
            return stream_key[len(prefix):]
        return stream_key


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

"""示例响应型机器人。

演示 Consumer 模式：
- 订阅 input_streams，在 on_signal() 中路由处理不同信号类型
- 消费输入信号 → 处理 → 可选地发出新信号
"""

from __future__ import annotations

from loguru import logger

from {package_name}.shared.channels import SignalType, StreamName

from .base import BaseRobot, Signal


class {ConsumerClassName}(BaseRobot):
    """响应型示例机器人。

    # 🔧 自定义点: 修改为你的业务逻辑
    订阅 {PRIMARY_STREAM} stream，接收并处理数据信号，生成输出信号。
    """

    robot_type = "{consumer_name}"
    input_streams: list[StreamName] = [StreamName.{PRIMARY_STREAM_UPPER}]     # 🔧 自定义点: 修改订阅的 stream
    output_streams: list[StreamName] = [StreamName.{SECONDARY_STREAM_UPPER}]  # 🔧 自定义点: 修改输出 stream

    async def setup(self) -> None:
        """初始化资源。"""
        # 🔧 自定义点: 初始化处理所需的状态、模型等
        logger.info("{ConsumerClassName} 初始化完成: task={}", self.task_id)

    async def on_signal(self, stream: str, signal: Signal) -> None:
        """处理输入信号。

        根据 signal.type 路由到不同的处理方法。
        """
        # 🔧 自定义点: 添加你的信号类型处理逻辑
        if signal.type == SignalType.DATA_UPDATE:
            await self._handle_data_update(signal)
        else:
            logger.debug(
                "{ConsumerClassName} 跳过未知信号: type={} stream={}",
                signal.type,
                stream,
            )

    async def _handle_data_update(self, signal: Signal) -> None:
        """处理数据更新信号。"""
        # 🔧 自定义点: 替换为实际的处理逻辑
        input_data = signal.data
        result = {
            "source_type": signal.type,
            "processed": True,
            "input_summary": str(input_data)[:100],
            "timestamp": signal.timestamp,
        }
        await self.emit(StreamName.{SECONDARY_STREAM_UPPER}, SignalType.PROCESS_RESULT, result)
        logger.debug("{ConsumerClassName} 已处理信号并发出结果: task={}", self.task_id)

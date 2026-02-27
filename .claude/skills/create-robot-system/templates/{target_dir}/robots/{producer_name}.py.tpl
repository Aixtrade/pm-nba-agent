"""示例轮询型机器人。

演示 Producer 模式：
- 无 input_streams，不消费任何信号
- 在 setup() 中用 asyncio.create_task() 启动自己的轮询循环
- 使用 emit() 向 output_streams 发送信号
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from loguru import logger

from {package_name}.shared.channels import SignalType, StreamName

from .base import BaseRobot


class {ProducerClassName}(BaseRobot):
    """轮询型示例机器人。

    # 🔧 自定义点: 修改为你的业务逻辑
    在 setup() 中启动 _produce_loop，按 poll_interval 周期性产生数据信号。
    """

    robot_type = "{producer_name}"
    output_streams: list[StreamName] = [StreamName.{PRIMARY_STREAM_UPPER}]  # 🔧 自定义点: 修改输出 stream

    async def setup(self) -> None:
        """初始化资源，启动数据产生循环。"""
        # 🔧 自定义点: 初始化外部连接、API 客户端等
        logger.info("{ProducerClassName} 初始化完成: task={}", self.task_id)
        self._produce_task = asyncio.create_task(self._produce_loop())

    async def teardown(self) -> None:
        """取消数据产生循环。"""
        self._produce_task.cancel()
        await asyncio.gather(self._produce_task, return_exceptions=True)

    async def _produce_loop(self) -> None:
        """周期性产生数据信号。"""
        while not self._cancelled:
            interval = float(self.config.get("poll_interval", 10.0))

            # 🔧 自定义点: 替换为实际的数据获取逻辑
            data = {
                "message": "示例数据",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await self.emit(StreamName.{PRIMARY_STREAM_UPPER}, SignalType.DATA_UPDATE, data)
            logger.debug(
                "{ProducerClassName} 已发送数据信号: task={}",
                self.task_id,
            )
            await asyncio.sleep(interval)

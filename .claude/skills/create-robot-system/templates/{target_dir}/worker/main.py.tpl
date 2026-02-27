"""Worker 入口"""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger

from {package_name}.shared import RedisClient
from {package_name}.worker.task_manager import TaskManager


async def main() -> None:
    """Worker 主函数"""
    logger.info("Worker 启动中...")

    # 初始化 Redis
    redis = RedisClient()
    await redis.connect()

    # 🔧 自定义点: 初始化业务特定的依赖（API 客户端、AI 模型等）

    # 创建任务管理器
    manager = TaskManager(redis)

    # 设置信号处理（优雅关闭）
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def handle_signal() -> None:
        logger.info("收到停止信号")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_signal)

    # 启动任务管理器（后台运行）
    manager_task = asyncio.create_task(manager.start())

    # 等待关闭信号
    await shutdown_event.wait()

    # 停止任务管理器
    await manager.stop()
    manager_task.cancel()

    try:
        await manager_task
    except asyncio.CancelledError:
        pass

    # 清理资源
    await redis.close()
    logger.info("Worker 已停止")


def run() -> None:
    """入口函数"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    run()

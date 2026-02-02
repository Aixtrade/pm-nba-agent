"""Worker 入口"""

import asyncio
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# 加载环境变量（在其他导入之前）
root_dir = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=root_dir / ".env", override=False)

from pm_nba_agent.api.services.data_fetcher import DataFetcher
from pm_nba_agent.agent import GameAnalyzer, AnalysisConfig
from pm_nba_agent.logging_config import configure_logging
from pm_nba_agent.shared import RedisClient
from pm_nba_agent.worker.task_manager import TaskManager


async def main() -> None:
    """Worker 主函数"""
    configure_logging()
    logger.info("Worker 启动中...")

    # 初始化 Redis
    redis = RedisClient()
    await redis.connect()

    # 初始化 DataFetcher
    fetcher = DataFetcher(max_workers=3)
    logger.info("DataFetcher 已初始化")

    # 初始化 GameAnalyzer
    config = AnalysisConfig()
    analyzer = GameAnalyzer(config)
    if config.is_configured():
        logger.info("GameAnalyzer 已初始化 (模型: {})", config.model)
    else:
        logger.warning("GameAnalyzer 未配置 API Key，AI 分析功能不可用")

    # 创建任务管理器
    manager = TaskManager(redis, fetcher, analyzer)

    # 设置信号处理
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
    await analyzer.close()
    fetcher.shutdown()
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

"""FastAPI 应用入口"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .routes.live_stream import router as live_stream_router
from .routes.parse import router as parse_router
from .routes.auth import router as auth_router
from .routes.orders import router as orders_router
from .routes.positions import router as positions_router
from .routes.tasks import router as tasks_router
from .services.data_fetcher import DataFetcher
from ..agent import GameAnalyzer, AnalysisConfig
from ..logging_config import configure_logging
from ..shared import RedisClient

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    root_dir = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=root_dir / ".env", override=False)

    # 启动时初始化资源
    app.state.fetcher = DataFetcher(max_workers=3)
    logger.info("DataFetcher 已初始化")

    # 初始化分析器
    config = AnalysisConfig()
    app.state.analyzer = GameAnalyzer(config)
    if config.is_configured():
        logger.info("GameAnalyzer 已初始化 (模型: {})", config.model)
    else:
        logger.warning("GameAnalyzer 未配置 API Key，AI 分析功能不可用")

    # 初始化 Redis（可选，仅在配置了 REDIS_URL 时启用）
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            app.state.redis = RedisClient(redis_url)
            await app.state.redis.connect()
            logger.info("Redis 已连接")
        except Exception as e:
            logger.warning("Redis 连接失败，任务模式不可用: {}", e)
            app.state.redis = None
    else:
        app.state.redis = None
        logger.info("未配置 REDIS_URL，任务模式不可用")

    yield

    # 关闭时清理资源
    if app.state.redis:
        await app.state.redis.close()
    await app.state.analyzer.close()
    app.state.fetcher.shutdown()
    logger.info("资源已关闭")


app = FastAPI(
    title="PM NBA Agent API",
    description="NBA 比赛实时数据 SSE 接口",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(live_stream_router)
app.include_router(parse_router)
app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(positions_router)
app.include_router(tasks_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "PM NBA Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "stream": "POST /api/v1/live/stream",
            "health": "GET /health",
        }
    }

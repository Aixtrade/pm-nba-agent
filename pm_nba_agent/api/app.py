"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.live_stream import router as live_stream_router
from .routes.parse import router as parse_router
from .routes.auth import router as auth_router
from .routes.orders import router as orders_router
from .services.data_fetcher import DataFetcher
from ..agent import GameAnalyzer, AnalysisConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    root_dir = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=root_dir / ".env", override=False)

    # 启动时初始化资源
    app.state.fetcher = DataFetcher(max_workers=3)
    print("DataFetcher 已初始化")

    # 初始化分析器
    config = AnalysisConfig()
    app.state.analyzer = GameAnalyzer(config)
    if config.is_configured():
        print(f"GameAnalyzer 已初始化 (模型: {config.model})")
    else:
        print("GameAnalyzer 未配置 API Key，AI 分析功能不可用")

    yield

    # 关闭时清理资源
    await app.state.analyzer.close()
    app.state.fetcher.shutdown()
    print("资源已关闭")


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

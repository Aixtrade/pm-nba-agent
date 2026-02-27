"""FastAPI app entry for live stream bridge."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from {package_name}.api.routes.live_stream import router as live_router
from {package_name}.api.routes.tasks import router as task_router
from {package_name}.shared import RedisClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = RedisClient()
    await redis.connect()
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.close()


app = FastAPI(title="PM Sports Bots API", lifespan=lifespan)
app.include_router(live_router)
app.include_router(task_router)

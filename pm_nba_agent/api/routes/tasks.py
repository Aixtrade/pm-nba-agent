"""任务管理 API"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.auth import require_auth
from ...shared import Channels, RedisClient, TaskConfig, TaskState, TaskStatus


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def require_redis(request: Request) -> RedisClient:
    """获取 Redis 客户端"""
    redis: RedisClient | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(
            status_code=503,
            detail="任务模式不可用，请配置 REDIS_URL",
        )
    return redis


async def _require_task_owner(
    redis: RedisClient, task_id: str, user_id: str
) -> TaskStatus:
    """加载 TaskStatus 并校验归属，不匹配返回 404"""
    status_key = Channels.task_status(task_id)
    data = await redis.get(status_key)
    if not data:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = TaskStatus.from_json(data)
    if status.user_id and status.user_id != user_id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return status


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    url: str = Field(..., description="Polymarket 事件 URL")
    poll_interval: float = Field(default=10.0, ge=5.0, le=60.0)
    include_scoreboard: bool = Field(default=True)
    include_boxscore: bool = Field(default=True)
    analysis_interval: float = Field(default=30.0, ge=10.0, le=120.0)
    strategy_ids: list[str] | None = Field(default=None)
    strategy_params_map: dict[str, dict[str, Any]] | None = Field(default=None)
    strategy_id: str = Field(default="merge_long")
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    enable_trading: bool = Field(default=False)
    execution_mode: str = Field(default="SIMULATION")
    order_type: str = Field(default="GTC")
    order_expiration: str | None = Field(default=None)
    min_order_amount: float = Field(default=1.0, ge=0.0)
    trade_cooldown_seconds: float = Field(default=0.0, ge=0.0)
    private_key: str | None = Field(default=None)
    proxy_address: str | None = Field(default=None)
    auto_buy: dict[str, Any] | None = Field(default=None)
    auto_sell: dict[str, Any] | None = Field(default=None)


class UpdateTaskConfigRequest(BaseModel):
    """更新任务配置请求"""

    patch: dict[str, Any] = Field(default_factory=dict)


class CreateTaskResponse(BaseModel):
    """创建任务响应"""

    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""

    task_id: str
    state: str
    created_at: str
    updated_at: str
    game_id: str | None = None
    error: str | None = None
    home_team: str | None = None
    away_team: str | None = None


class TaskListResponse(BaseModel):
    """任务列表响应"""

    tasks: list[TaskStatusResponse]


class TaskConfigResponse(BaseModel):
    """任务配置响应"""

    config: dict[str, Any]


@router.post("/create", response_model=CreateTaskResponse)
async def create_task(
    request: Request,
    body: CreateTaskRequest,
) -> CreateTaskResponse:
    """
    创建后台任务

    创建一个后台任务来监控比赛数据流。任务会持续运行直到比赛结束或被取消。

    **请求体参数与直连模式一致（前端配置）**

    **返回**:
    - `task_id`: 任务 ID，用于后续查询和订阅
    - `status`: 任务状态
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    # 生成任务 ID
    task_id = str(uuid.uuid4())[:8]

    # 创建配置
    config = TaskConfig(
        url=body.url,
        poll_interval=body.poll_interval,
        include_scoreboard=body.include_scoreboard,
        include_boxscore=body.include_boxscore,
        analysis_interval=body.analysis_interval,
        strategy_ids=body.strategy_ids,
        strategy_params_map=body.strategy_params_map,
        strategy_id=body.strategy_id,
        strategy_params=body.strategy_params,
        enable_trading=body.enable_trading,
        execution_mode=body.execution_mode,
        order_type=body.order_type,
        order_expiration=body.order_expiration,
        min_order_amount=body.min_order_amount,
        trade_cooldown_seconds=body.trade_cooldown_seconds,
        private_key=body.private_key,
        proxy_address=body.proxy_address,
        auto_buy=body.auto_buy or {},
        auto_sell=body.auto_sell or {},
        user_id=user_id,
    )

    # 保存配置到 Redis
    config_key = Channels.task_config(task_id)
    await redis.set(config_key, config.to_json(), ex=86400)

    # 创建初始状态
    status = TaskStatus.create(task_id, user_id=user_id)
    status_key = Channels.task_status(task_id)
    await redis.set(status_key, status.to_json(), ex=86400)

    # 添加到用户任务集合 + 全局任务集合
    await redis.sadd(Channels.user_tasks(user_id), task_id)
    await redis.sadd(Channels.all_tasks(), task_id)

    # 发送控制消息给 Worker
    control_message = json.dumps({
        "action": "create",
        "task_id": task_id,
        "config": config.to_dict(),
        "user_id": user_id,
    })
    await redis.publish(Channels.CONTROL, control_message)

    return CreateTaskResponse(
        task_id=task_id,
        status=status.state.value,
    )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(request: Request) -> TaskListResponse:
    """
    列出当前用户的所有任务

    返回当前用户所有任务的状态列表。
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    task_ids = await redis.smembers(Channels.user_tasks(user_id))
    tasks: list[TaskStatusResponse] = []

    for task_id in task_ids:
        status_key = Channels.task_status(task_id)
        data = await redis.get(status_key)
        if data:
            status = TaskStatus.from_json(data)
            tasks.append(TaskStatusResponse(
                task_id=status.task_id,
                state=status.state.value,
                created_at=status.created_at,
                updated_at=status.updated_at,
                game_id=status.game_id,
                error=status.error,
                home_team=status.home_team,
                away_team=status.away_team,
            ))

    # 按创建时间倒序
    tasks.sort(key=lambda t: t.created_at, reverse=True)

    return TaskListResponse(tasks=tasks)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(request: Request, task_id: str) -> TaskStatusResponse:
    """
    获取任务状态

    返回指定任务的详细状态。
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    status = await _require_task_owner(redis, task_id, user_id)
    return TaskStatusResponse(
        task_id=status.task_id,
        state=status.state.value,
        created_at=status.created_at,
        updated_at=status.updated_at,
        game_id=status.game_id,
        error=status.error,
        home_team=status.home_team,
        away_team=status.away_team,
    )


@router.get("/{task_id}/config", response_model=TaskConfigResponse)
async def get_task_config(request: Request, task_id: str) -> TaskConfigResponse:
    """获取任务配置"""
    user_id = require_auth(request)
    redis = require_redis(request)

    # 先校验归属
    await _require_task_owner(redis, task_id, user_id)

    config_key = Channels.task_config(task_id)
    config_data = await redis.get(config_key)
    if not config_data:
        raise HTTPException(status_code=404, detail="任务配置不存在")

    config = TaskConfig.from_json(config_data)
    return TaskConfigResponse(config=config.to_dict())


@router.delete("/{task_id}")
async def cancel_task(request: Request, task_id: str) -> dict[str, str]:
    """
    取消任务

    取消指定的后台任务。
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    status = await _require_task_owner(redis, task_id, user_id)

    # 检查任务状态
    if status.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
        return {"message": f"任务已处于终态: {status.state.value}"}

    # 发送取消消息给 Worker
    control_message = json.dumps({
        "action": "cancel",
        "task_id": task_id,
    })
    await redis.publish(Channels.CONTROL, control_message)

    return {"message": "取消请求已发送"}


@router.patch("/{task_id}/config")
async def update_task_config(
    request: Request,
    task_id: str,
    body: UpdateTaskConfigRequest,
) -> dict[str, str]:
    """
    动态更新任务配置

    支持在任务运行中更新参数（例如 auto_buy 开关、选边、策略配置等）。
    """
    user_id = require_auth(request)
    redis = require_redis(request)

    await _require_task_owner(redis, task_id, user_id)

    config_key = Channels.task_config(task_id)
    config_data = await redis.get(config_key)
    if not config_data:
        raise HTTPException(status_code=404, detail="任务配置不存在")

    config = TaskConfig.from_json(config_data)
    merged_config = _deep_merge_dict(config.to_dict(), body.patch)
    config = TaskConfig.from_dict(merged_config)

    await redis.set(config_key, config.to_json(), ex=86400)

    control_message = json.dumps({
        "action": "update_config",
        "task_id": task_id,
        "patch": body.patch,
    })
    await redis.publish(Channels.CONTROL, control_message)

    return {"message": "配置更新请求已发送"}


@router.post("/{task_id}/positions/refresh")
async def refresh_task_positions(request: Request, task_id: str) -> dict[str, str]:
    """触发任务立即刷新持仓"""
    user_id = require_auth(request)
    redis = require_redis(request)

    await _require_task_owner(redis, task_id, user_id)

    control_message = json.dumps({
        "action": "refresh_positions",
        "task_id": task_id,
    })
    await redis.publish(Channels.CONTROL, control_message)

    return {"message": "持仓刷新请求已发送"}


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """递归合并字典"""
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dict(current, value)
        else:
            merged[key] = value
    return merged

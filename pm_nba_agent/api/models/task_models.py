"""任务相关 API 模型"""

from typing import Any

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """创建任务请求"""

    url: str = Field(..., description="Polymarket 事件 URL")
    poll_interval: float = Field(default=10.0, ge=5.0, le=60.0)
    include_scoreboard: bool = Field(default=True)
    include_boxscore: bool = Field(default=True)
    enable_analysis: bool = Field(default=True)
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
    auto_trade: dict[str, Any] | None = Field(default=None)


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


class TaskCompletionWebhookPayload(BaseModel):
    """任务完成 webhook 请求体"""

    taskId: str = Field(..., min_length=1)
    groupFolder: str = Field(..., min_length=1)
    chatJid: str = Field(..., min_length=1)
    scheduleType: str = Field(..., min_length=1)
    scheduleValue: str = Field(..., min_length=1)
    durationMs: int = Field(..., ge=0)
    runAt: str = Field(..., min_length=1)
    nextRun: str | None = None
    status: str = Field(..., min_length=1)
    success: bool
    resultSummary: str = Field(default="")
    chatOutput: str = Field(default="")
    error: str | None = None


class TaskCompletionWebhookResponse(BaseModel):
    """任务完成 webhook 响应"""

    ok: bool
    task_id: str
    status_synced: bool

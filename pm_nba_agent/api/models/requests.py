"""API 请求模型"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class LiveStreamRequest(BaseModel):
    """SSE 实时流请求参数"""

    url: str = Field(
        ...,
        description="Polymarket 事件 URL",
        examples=["https://polymarket.com/event/nba-por-was-2026-01-27"]
    )
    poll_interval: float = Field(
        default=10.0,
        ge=5.0,
        le=60.0,
        description="轮询间隔（秒），范围 5-60"
    )
    include_scoreboard: bool = Field(
        default=True,
        description="是否包含比分板数据"
    )
    include_boxscore: bool = Field(
        default=True,
        description="是否包含详细统计数据"
    )
    include_playbyplay: bool = Field(
        default=True,
        description="是否获取逐回合数据（仅用于分析上下文）"
    )
    playbyplay_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="首次逐回合数据条数，范围 1-100"
    )
    enable_analysis: bool = Field(
        default=True,
        description="是否启用 AI 实时分析"
    )
    analysis_interval: float = Field(
        default=30.0,
        ge=10.0,
        le=120.0,
        description="AI 分析间隔（秒），范围 10-120"
    )
    strategy_id: str = Field(
        default="merge_long",
        description="策略 ID",
    )
    strategy_params: dict[str, Any] = Field(
        default_factory=dict,
        description="策略参数",
    )
    enable_trading: bool = Field(
        default=False,
        description="是否启用自动下单",
    )
    execution_mode: str = Field(
        default="SIMULATION",
        description="执行模式 (SIMULATION/REAL)",
    )
    order_type: str = Field(
        default="GTC",
        description="订单类型 (GTC/GTD)",
    )
    order_expiration: str | None = Field(
        default=None,
        description="GTD 到期时间 (毫秒字符串)",
    )
    min_order_amount: float = Field(
        default=1.0,
        ge=0.0,
        description="最小下单数量",
    )
    trade_cooldown_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="下单冷却时间（秒）",
    )
    private_key: str | None = Field(
        default=None,
        description="Polymarket 私钥 (可选，若未配置将使用服务端默认)",
    )
    proxy_address: str | None = Field(
        default=None,
        description="Polymarket 代理地址 (可选，覆盖服务端默认)",
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith('http'):
            raise ValueError('URL 必须以 http 或 https 开头')
        if 'polymarket.com' not in v.lower():
            raise ValueError('URL 必须是 Polymarket 链接')
        return v

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"SIMULATION", "REAL"}:
            raise ValueError("execution_mode 仅支持 SIMULATION 或 REAL")
        return normalized

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"GTC", "GTD"}:
            raise ValueError("order_type 仅支持 GTC 或 GTD")
        return normalized


class ParsePolymarketRequest(BaseModel):
    """Polymarket URL 解析请求"""

    url: str = Field(
        ...,
        description="Polymarket 事件 URL",
        examples=["https://polymarket.com/event/nba-por-was-2026-01-27"]
    )

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith('http'):
            raise ValueError('URL 必须以 http 或 https 开头')
        if 'polymarket.com' not in v.lower():
            raise ValueError('URL 必须是 Polymarket 链接')
        return v


class LoginRequest(BaseModel):
    """登录请求"""

    passphrase: str = Field(
        ...,
        description="登录口令",
        examples=["your-passphrase"]
    )


class LoginResponse(BaseModel):
    """登录响应"""

    token: str = Field(
        ...,
        description="访问令牌"
    )
    token_type: str = Field(
        default="Bearer",
        description="令牌类型"
    )


class PolymarketOrderRequest(BaseModel):
    """Polymarket 下单请求"""

    token_id: str = Field(
        ...,
        description="Polymarket 代币 ID",
        examples=["71321045679252212594626385532706912750332728571942532289631379312455583992563"],
    )
    side: str = Field(
        ...,
        description="买卖方向 (BUY/SELL)",
        examples=["BUY"],
    )
    price: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description="限价 (0-1)",
    )
    size: float = Field(
        ...,
        gt=0.0,
        description="下单数量",
    )
    order_type: str = Field(
        default="GTC",
        description="订单类型 (GTC/GTD)",
    )
    expiration: str | None = Field(
        default=None,
        description="GTD 到期时间 (毫秒字符串)",
        examples=["1000000000000"],
    )
    private_key: str | None = Field(
        default=None,
        description="Polymarket 私钥 (可选，若未配置将使用服务端默认)",
    )
    proxy_address: str | None = Field(
        default=None,
        description="Polymarket 代理地址 (可选，若未配置将使用服务端默认)",
    )

    @field_validator("side")
    @classmethod
    def validate_side(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"BUY", "SELL"}:
            raise ValueError("side 仅支持 BUY 或 SELL")
        return normalized

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in {"GTC", "GTD"}:
            raise ValueError("order_type 仅支持 GTC 或 GTD")
        return normalized


class PolymarketOrderResponse(BaseModel):
    """Polymarket 下单响应"""

    order_type: str = Field(
        ...,
        description="订单类型",
    )
    response: dict = Field(
        ...,
        description="Polymarket 下单返回",
    )


class PolymarketBatchOrderRequest(BaseModel):
    """Polymarket 批量下单请求"""

    orders: list[PolymarketOrderRequest] = Field(
        ...,
        description="订单列表",
    )


class PolymarketBatchOrderResponse(BaseModel):
    """Polymarket 批量下单响应"""

    results: list = Field(
        ...,
        description="批量下单返回",
    )


class PolymarketMarketPositionsRequest(BaseModel):
    """Polymarket 市场持仓查询请求"""

    condition_id: str = Field(
        ...,
        description="市场 condition_id",
        examples=[
            "0xdd22472e552920b8438158ea7238bfadfa4f736aa4cee91a6b86c39ead110917"
        ],
    )
    user_address: str | None = Field(
        default=None,
        description="用户地址 (0x 开头)。为空时使用服务端默认",
    )
    proxy_address: str | None = Field(
        default=None,
        description="代理地址 (可选，覆盖服务端默认)",
    )
    outcomes: list[str] | None = Field(
        default=None,
        description="可选，市场双边 outcome 名称，用于补齐 0 持仓",
    )
    size_threshold: float | None = Field(
        default=None,
        ge=0.0,
        description="sizeThreshold 过滤值",
    )
    redeemable: bool | None = Field(
        default=None,
        description="是否仅返回可赎回持仓",
    )
    mergeable: bool | None = Field(
        default=None,
        description="是否仅返回可合并持仓",
    )


class PolymarketPositionSide(BaseModel):
    """市场持仓单边信息"""

    outcome: str = Field(..., description="Outcome 名称")
    size: float = Field(..., description="持仓份额")
    initial_value: float = Field(..., description="持仓成本（initialValue 汇总）")
    asset: str | None = Field(default=None, description="Token 资产 ID")


class PolymarketMarketPositionsResponse(BaseModel):
    """市场持仓查询响应"""

    condition_id: str = Field(..., description="市场 condition_id")
    user_address: str = Field(..., description="用户地址")
    sides: list[PolymarketPositionSide] = Field(
        ..., description="双边持仓份额"
    )

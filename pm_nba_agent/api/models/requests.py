"""API 请求模型"""

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
        description="是否包含逐回合数据"
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

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith('http'):
            raise ValueError('URL 必须以 http 或 https 开头')
        if 'polymarket.com' not in v.lower():
            raise ValueError('URL 必须是 Polymarket 链接')
        return v


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

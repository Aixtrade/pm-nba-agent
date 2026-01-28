"""Agent 数据模型"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class AnalysisConfig:
    """分析配置"""
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    analysis_interval: float = field(default_factory=lambda: float(os.getenv("ANALYSIS_INTERVAL", "30")))
    event_interval: float = field(default_factory=lambda: float(os.getenv("ANALYSIS_EVENT_INTERVAL", "15")))
    max_tokens: int = 1024
    temperature: float = 0.7

    def is_configured(self) -> bool:
        """检查是否已配置 API Key"""
        return bool(self.api_key)


@dataclass
class SignificantEvent:
    """重要事件"""
    event_type: str  # "score_change", "lead_change", "big_play", "timeout", etc.
    description: str
    timestamp: float  # Unix timestamp
    data: dict = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """分析结果"""
    game_id: str
    round_number: int
    content: str
    timestamp: float
    context_summary: Optional[str] = None

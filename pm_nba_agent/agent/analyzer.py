"""比赛分析器核心逻辑"""

from typing import AsyncGenerator, Optional

from .context import GameContext
from .llm_client import LLMClient
from .models import AnalysisConfig
from .prompts import SYSTEM_PROMPT, build_analysis_prompt


class GameAnalyzer:
    """NBA 比赛实时分析器"""

    def __init__(self, config: Optional[AnalysisConfig] = None):
        self._config = config or AnalysisConfig()
        self._client = LLMClient(self._config)

    @property
    def config(self) -> AnalysisConfig:
        """获取配置"""
        return self._config

    def is_enabled(self) -> bool:
        """检查分析器是否可用"""
        return self._config.is_configured()

    def should_analyze(self, context: GameContext) -> bool:
        """
        判断是否应该触发分析

        Args:
            context: 比赛上下文

        Returns:
            是否应该分析
        """
        return context.should_analyze(
            normal_interval=self._config.analysis_interval,
            event_interval=self._config.event_interval,
        )

    async def analyze_stream(
        self,
        context: GameContext
    ) -> AsyncGenerator[str, None]:
        """
        流式分析比赛

        Args:
            context: 比赛上下文

        Yields:
            分析文本片段
        """
        if not self.is_enabled():
            yield "[分析不可用] OpenAI API Key 未配置"
            context.mark_analysis_attempted(success=False)
            return

        # 构建 Prompt
        prompt_context = context.to_prompt_context()
        user_prompt = build_analysis_prompt(prompt_context)

        # 流式生成
        had_error = False
        async for chunk in self._client.stream_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        ):
            if chunk.startswith("[错误]") or chunk.startswith("[分析不可用]"):
                had_error = True
            yield chunk

        # 标记分析结果
        context.mark_analysis_attempted(success=not had_error)

    async def analyze(self, context: GameContext) -> str:
        """
        非流式分析比赛（用于测试）

        Args:
            context: 比赛上下文

        Returns:
            完整分析文本
        """
        chunks = []
        async for chunk in self.analyze_stream(context):
            chunks.append(chunk)
        return "".join(chunks)

    async def close(self) -> None:
        """关闭资源"""
        await self._client.close()

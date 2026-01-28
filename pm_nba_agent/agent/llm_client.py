"""OpenAI 异步客户端封装"""

from typing import AsyncGenerator, Optional
import asyncio

from openai import AsyncOpenAI
from openai import APIError, RateLimitError, APIConnectionError

from .models import AnalysisConfig


class LLMClient:
    """OpenAI LLM 客户端"""

    def __init__(self, config: AnalysisConfig):
        self._config = config
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """获取或创建客户端"""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
        return self._client

    async def stream_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
    ) -> AsyncGenerator[str, None]:
        """
        流式生成回复

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            max_retries: 最大重试次数

        Yields:
            文本片段
        """
        if not self._config.is_configured():
            yield "[错误] OpenAI API Key 未配置"
            return

        client = self._get_client()
        retry_count = 0

        while retry_count < max_retries:
            try:
                stream = await client.chat.completions.create(
                    model=self._config.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=self._config.max_tokens,
                    temperature=self._config.temperature,
                    stream=True,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

                return  # 成功完成

            except RateLimitError:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    await asyncio.sleep(wait_time)
                else:
                    yield "[错误] API 请求频率限制，请稍后重试"

            except APIConnectionError:
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(1)
                else:
                    yield "[错误] 无法连接到 OpenAI API"

            except APIError as e:
                yield f"[错误] API 错误: {str(e)}"
                return

            except Exception as e:
                yield f"[错误] 未知错误: {str(e)}"
                return

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        非流式生成回复（用于测试或简单场景）

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示

        Returns:
            完整回复文本
        """
        chunks = []
        async for chunk in self.stream_completion(system_prompt, user_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def close(self) -> None:
        """关闭客户端"""
        if self._client is not None:
            await self._client.close()
            self._client = None

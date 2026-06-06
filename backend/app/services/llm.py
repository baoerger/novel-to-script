from openai import OpenAI

from backend.app.config import llm_config


class LLMClient:
    """统一的 LLM 调用接口，支持 DeepSeek / Qwen 多 Provider。"""

    def __init__(self, provider: str | None = None):
        self.provider = provider or llm_config.provider
        api_key = llm_config.api_keys.get(self.provider, "") or "sk-placeholder"
        self._client = OpenAI(
            api_key=api_key,
            base_url=llm_config.get_base_url(self.provider),
        )

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
        response_format: dict | None = None,
    ) -> dict:
        """统一的 chat completion 接口。

        Args:
            messages: OpenAI 格式的消息列表
            model: 模型名称，默认使用配置中的 model
            temperature: 温度参数，默认使用配置中的 temperature
            response_format: 响应格式，如 {"type": "json_object"}

        Returns:
            API 响应的完整 dict
        """
        kwargs = dict(
            model=model or llm_config.model,
            messages=messages,
            temperature=temperature if temperature is not None else llm_config.temperature,
        )
        if response_format:
            kwargs["response_format"] = response_format

        response = self._client.chat.completions.create(**kwargs)
        return response.model_dump()

    def extract_content(self, response: dict) -> str:
        """从 API 响应中提取文本内容。"""
        choices = response.get("choices", [])
        if not choices:
            raise ValueError("API 响应中没有 choices")
        return choices[0]["message"]["content"]


def get_client(provider: str | None = None) -> LLMClient:
    """工厂方法：创建指定 Provider 的 LLM 客户端。"""
    return LLMClient(provider=provider)

import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from pydantic import BaseModel, ValidationError

from backend.app.config import llm_config

logger = logging.getLogger(__name__)


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
        """统一的 chat completion 接口。"""
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


# Prompt 模板目录（相对于 backend 目录）
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def render_prompt(template_name: str, variables: dict) -> list[dict]:
    """加载 Jinja2 模板，注入变量，渲染为 OpenAI messages 格式。"""
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    tpl = env.get_template(template_name)
    rendered = tpl.render(**variables)

    # 模板包含 <!-- SYSTEM --> 和 <!-- USER --> 标记
    system_start = rendered.find("<!-- SYSTEM -->")
    user_start = rendered.find("<!-- USER -->")

    messages = []
    if system_start != -1 and user_start != -1:
        system_text = rendered[system_start + len("<!-- SYSTEM -->"):user_start].strip()
        user_text = rendered[user_start + len("<!-- USER -->"):].strip()
        if system_text:
            messages.append({"role": "system", "content": system_text})
        if user_text:
            messages.append({"role": "user", "content": user_text})
    else:
        # 无标记时整个作为 user 消息
        messages.append({"role": "user", "content": rendered.strip()})

    return messages


def structured_call(
    template_name: str,
    variables: dict,
    output_model: type[BaseModel],
    max_retries: int | None = None,
) -> BaseModel:
    """LLM 结构化输出：模板渲染 → JSON mode → Pydantic 校验 → 重试降级。

    流程:
    1. Jinja2 模板渲染为 messages
    2. LLM 调用（JSON mode）
    3. Pydantic 校验
    4. 校验失败 → 将错误注入 prompt → 重试（最多 max_retries 次）
    5. 全部重试耗尽 → 切换到 fallback_model → 再试 1 次
    6. 仍失败 → 抛异常
    """
    max_retries = max_retries if max_retries is not None else llm_config.max_retries
    client = get_client()

    messages = render_prompt(template_name, variables)
    errors: list[str] = []

    for attempt in range(max_retries):
        try:
            result = _try_call(client, messages, llm_config.model, output_model, errors)
            return result
        except (ValidationError, json.JSONDecodeError, ValueError) as e:
            error_msg = _format_error(e)
            errors.append(error_msg)
            logger.warning(
                "结构化输出校验失败 (attempt %d/%d): %s", attempt + 1, max_retries, error_msg
            )
            messages = _inject_errors(messages, errors)

    # 主模型全部失败，尝试 fallback
    logger.warning("主模型 %d 次重试均失败，降级到 %s", max_retries, llm_config.fallback_model)
    fallback_client = get_client("qwen")
    try:
        errors.clear()
        return _try_call(fallback_client, messages, llm_config.fallback_model, output_model, errors)
    except (ValidationError, json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(
            f"结构化输出失败: 主模型 {max_retries} 次 + fallback 1 次重试均失败。"
            f"最后错误: {_format_error(e)}"
        ) from e


def _try_call(
    client: LLMClient,
    messages: list[dict],
    model: str,
    output_model: type[BaseModel],
    errors: list[str],
) -> BaseModel:
    """单次 LLM 调用 + JSON 解析 + Pydantic 校验。"""
    response = client.chat(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
    )

    content = client.extract_content(response)
    data = json.loads(content)

    # 如果输出是数组包裹的对象，取第一个元素
    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("LLM 返回空数组")
        data = data[0]

    return output_model.model_validate(data)


def _format_error(e: Exception) -> str:
    """格式化错误信息用于注入 prompt。"""
    if isinstance(e, ValidationError):
        return str(e.errors())
    return str(e)


def _inject_errors(messages: list[dict], errors: list[str]) -> list[dict]:
    """将校验错误注入到消息列表中作为修正提示。"""
    error_text = "\n".join(f"- {e}" for e in errors)
    correction = {
        "role": "user",
        "content": (
            f"上次输出的 JSON 校验失败，错误如下：\n{error_text}\n"
            "请修正错误后重新输出符合格式要求的 JSON。"
        ),
    }
    return messages + [correction]

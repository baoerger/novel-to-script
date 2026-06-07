import json
import logging
import re
from pathlib import Path
from typing import get_origin

from jinja2 import Environment, FileSystemLoader
from openai import OpenAI
from pydantic import BaseModel, TypeAdapter, ValidationError

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

_JINJA_ENV: Environment | None = None


def _get_jinja_env() -> Environment:
    """获取缓存的 Jinja2 Environment 实例。"""
    global _JINJA_ENV
    if _JINJA_ENV is None:
        _JINJA_ENV = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))
    return _JINJA_ENV


def render_prompt(template_name: str, variables: dict) -> list[dict]:
    """加载 Jinja2 模板，注入变量，渲染为 OpenAI messages 格式。"""
    env = _get_jinja_env()
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
    output_model: type[BaseModel] | type,
    max_retries: int | None = None,
) -> BaseModel | list:
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
    output_model: type[BaseModel] | type,
    errors: list[str],
) -> BaseModel | list:
    """单次 LLM 调用 + JSON 解析 + Pydantic 校验。

    支持两种 output_model:
    - Pydantic BaseModel 子类：用 model_validate 校验
    - list[BaseModel] 泛型：用 TypeAdapter 校验

    在 json.loads 之前先对 LLM 原始响应做容错清洗。
    """
    response = client.chat(
        messages=messages,
        model=model,
        response_format={"type": "json_object"},
    )

    content = client.extract_content(response)
    data = _parse_json_with_repair(content)

    origin = get_origin(output_model)
    if origin is list:
        adapter = TypeAdapter(output_model)
        return adapter.validate_python(data)
    else:
        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("LLM 返回空数组")
            data = data[0]
        return output_model.model_validate(data)


def _parse_json_with_repair(raw: str) -> dict | list:
    """对 LLM 原始响应做容错清洗后再 json.loads。

    按顺序尝试:
    1. 提取 markdown code block（```json ... ```）
    2. 直接 json.loads(strict=False)
    3. 修复控制字符后 json.loads
    4. 修复尾逗号后 json.loads
    全部失败则抛出原始错误。
    """
    if not raw or not raw.strip():
        raise json.JSONDecodeError("LLM 返回空响应", "", 0)

    # Step 1: 提取 markdown code block
    cleaned = raw.strip()
    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL)
    if md_match:
        cleaned = md_match.group(1).strip()

    # Step 2: 直接解析（strict=False 允许控制字符）
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        pass

    # Step 3: 修复未转义的控制字符（\n \t \r 等）
    try:
        repaired = _escape_control_chars_in_strings(cleaned)
        return json.loads(repaired, strict=False)
    except json.JSONDecodeError:
        pass

    # Step 4: 修复尾逗号（最外层对象/数组）
    try:
        repaired = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return json.loads(repaired, strict=False)
    except json.JSONDecodeError:
        pass

    # 全部失败，抛出带上下文的错误
    preview = cleaned[:200] if len(cleaned) > 200 else cleaned
    raise json.JSONDecodeError(
        f"JSON 解析失败，响应预览: {preview}",
        cleaned,
        0,
    )


def _escape_control_chars_in_strings(text: str) -> str:
    """修复 JSON 字符串值中未转义的控制字符。

    扫描 JSON 结构，在字符串值内将字面换行/制表符替换为转义形式。
    """
    result = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == "\\":
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\r":
                result.append("\\r")
            elif ch == "\t":
                result.append("\\t")
            elif ord(ch) < 0x20:
                result.append(f"\\u{ord(ch):04x}")
            else:
                result.append(ch)
        else:
            result.append(ch)
    return "".join(result)


def _format_error(e: Exception) -> str:
    """格式化错误信息用于注入 prompt。"""
    if isinstance(e, ValidationError):
        return str(e.errors())
    return str(e)


def _inject_errors(messages: list[dict], errors: list[str]) -> list[dict]:
    """将校验错误注入到消息列表中，给出精确修正指示。"""
    latest = errors[-1] if errors else "未知错误"

    # 根据错误类型给出针对性指导
    if "Invalid control character" in latest or "control character" in latest.lower():
        hint = "JSON 字符串值中包含未经转义的换行符或控制字符。请将所有字符串内的换行替换为 \\\\n，制表符替换为 \\\\t。"
    elif "Expecting ',' delimiter" in latest or "Expecting value" in latest:
        hint = "JSON 格式错误：可能缺少逗号、多余逗号、或缺少值。请检查每个对象的花括号配对和逗号位置。"
    elif "Expecting property name" in latest:
        hint = "JSON 对象中多了一个尾逗号。请删除对象/数组最后一个元素后面的逗号。"
    elif "Unterminated string" in latest:
        hint = "JSON 中有未闭合的字符串引号。请检查所有字符串是否以双引号开始和结束。"
    elif "空" in latest or "empty" in latest.lower():
        hint = "输出为空。请务必返回完整的 JSON，即使没有匹配数据也要返回空数组 []。"
    elif "ValidationError" in latest or "validation error" in latest.lower():
        hint = "JSON 结构正确但字段类型不匹配。请仔细检查每个字段的类型定义并修正。"
    else:
        hint = "请仔细检查 JSON 格式：确保所有字符串用双引号包裹、控制字符已转义、数组/对象括号正确配对。"

    correction = {
        "role": "user",
        "content": (
            f"上次输出的 JSON 校验失败。\n"
            f"具体错误: {latest}\n"
            f"修正方法: {hint}\n"
            "请修正后重新输出符合格式要求的 JSON。"
        ),
    }
    return messages + [correction]

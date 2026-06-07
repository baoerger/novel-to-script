import os
from dataclasses import dataclass, field
from pathlib import Path

# ---- 自动加载 .env 文件（如果 python-dotenv 可用）----
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
except ImportError:
    pass


@dataclass
class LLMConfig:
    """AI 模型配置，所有字段可通过大写环境变量覆盖"""

    provider: str = os.getenv("LLM_PROVIDER", "deepseek")
    model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    fallback_model: str = os.getenv("LLM_FALLBACK_MODEL", "qwen3.7-plus")
    max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    base_urls: dict = field(default_factory=lambda: {
        "deepseek": "https://api.deepseek.com",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    })

    api_keys: dict = field(default_factory=lambda: {
        "deepseek": os.getenv("DEEPSEEK_API_KEY", ""),
        "qwen": os.getenv("QWEN_API_KEY", ""),
    })

    def get_api_key(self, provider: str | None = None) -> str:
        p = provider or self.provider
        key = self.api_keys.get(p, "")
        if not key:
            raise ValueError(f"缺少 API Key: 请设置环境变量 {p.upper()}_API_KEY")
        return key

    def get_base_url(self, provider: str | None = None) -> str:
        p = provider or self.provider
        return self.base_urls.get(p, "https://api.deepseek.com")


@dataclass
class AppConfig:
    """应用级配置"""

    projects_dir: str = os.getenv("PROJECTS_DIR", "./projects")
    max_chapters: int = int(os.getenv("MAX_CHAPTERS", "100"))
    max_tokens_per_chapter: int = int(os.getenv("MAX_TOKENS_PER_CHAPTER", "15000"))
    max_upload_size: int = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))
    supported_extensions: tuple = (".txt", ".docx")


# ---- 单例 ----
llm_config = LLMConfig()
app_config = AppConfig()

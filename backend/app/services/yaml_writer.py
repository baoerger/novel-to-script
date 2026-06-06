import logging
from pathlib import Path

import yaml

from backend.app.models.script import Script

logger = logging.getLogger(__name__)


def script_to_yaml(script: Script) -> str:
    """将 Script 对象序列化为 YAML 字符串。

    使用 Pydantic model_dump 转为 dict，排除空字段和空列表以减小输出体积。
    默认使用 allow_unicode=True 保留中文原文。
    """
    data = script.model_dump(
        mode="json",
        exclude_none=True,
        exclude_defaults=False,
    )
    # 移除顶层空列表以保持输出简洁
    for key in list(data.keys()):
        if isinstance(data[key], list) and len(data[key]) == 0:
            del data[key]

    return yaml.dump(
        data,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        indent=2,
    )


def save_script(script: Script, path: str | Path) -> Path:
    """将剧本序列化为 YAML 并写入文件。

    自动创建父目录。返回写入的文件路径。
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    yaml_str = script_to_yaml(script)
    path.write_text(yaml_str, encoding="utf-8")
    logger.info("剧本已保存到 %s", path)
    return path

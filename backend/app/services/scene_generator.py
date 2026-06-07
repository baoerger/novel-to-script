import logging

from app.models.script import ContentElement
from app.services.llm import structured_call

logger = logging.getLogger(__name__)


def generate_scene(
    scene_id: str,
    source_chapter: int,
    location: str,
    time_hint: str,
    summary: str,
    characters_info: str,
    scene_text: str,
) -> list[ContentElement]:
    """将单场叙事文本转换为剧本格式内容元素序列。

    使用 generate_scene.j2 模板，通过 LLM 将小说场景转化为
    stage_direction / dialogue / voiceover / transition 序列。
    失败时记录错误并返回空列表（不阻塞流程）。
    """
    variables = {
        "scene_id": scene_id,
        "source_chapter": source_chapter,
        "location": location,
        "time_hint": time_hint,
        "summary": summary,
        "characters_info": characters_info,
        "scene_text": scene_text,
    }

    try:
        result = structured_call(
            template_name="generate_scene.j2",
            variables=variables,
            output_model=list[ContentElement],
        )
        if isinstance(result, list):
            return result
        return list(result.root) if hasattr(result, "root") else []
    except Exception as e:
        logger.error(
            "场景剧本生成失败 [%s]: %s",
            scene_id,
            e,
        )
        return []

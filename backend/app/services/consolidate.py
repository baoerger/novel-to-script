import json
import logging

from backend.app.models.analysis import ChapterAnalysis
from backend.app.models.consolidated import ConsolidatedAnalysis
from backend.app.services.llm import structured_call

logger = logging.getLogger(__name__)


def merge_and_consolidate(analyses: list[ChapterAnalysis]) -> ConsolidatedAnalysis:
    """跨章汇总：角色去重、关系推断、时间线排序。

    将所有章节的分析结果序列化后提交 LLM，使用 consolidate.j2 模板
    进行跨章合并。失败时返回空的 ConsolidatedAnalysis（不阻塞流程）。
    """
    if not analyses:
        return ConsolidatedAnalysis()

    characters_json = _serialize_characters(analyses)
    scenes_json = _serialize_scenes(analyses)

    variables = {
        "characters_json": characters_json,
        "scenes_json": scenes_json,
    }

    try:
        result = structured_call(
            template_name="consolidate.j2",
            variables=variables,
            output_model=ConsolidatedAnalysis,
        )
        return result
    except Exception as e:
        logger.error("跨章汇总失败: %s", e)
        return ConsolidatedAnalysis()


def _serialize_characters(analyses: list[ChapterAnalysis]) -> str:
    """将各章角色提取结果序列化为 JSON 字符串。"""
    data = []
    for ch in analyses:
        for char in ch.characters:
            data.append({
                "chapter_index": ch.chapter_index,
                "name": char.name,
                "aliases": char.aliases,
                "role_hint": char.role_hint,
                "description": char.description,
                "first_appearance_chapter": char.first_appearance_chapter,
            })
    return json.dumps(data, ensure_ascii=False, indent=2)


def _serialize_scenes(analyses: list[ChapterAnalysis]) -> str:
    """将各章场景检测结果序列化为 JSON 字符串。"""
    data = []
    for ch in analyses:
        for scene in ch.scenes:
            data.append({
                "chapter_index": ch.chapter_index,
                "scene_index": scene.scene_index,
                "summary": scene.summary,
                "location": scene.location,
                "time_hint": scene.time_hint,
                "characters_present": scene.characters_present,
                "start_paragraph": scene.start_paragraph,
                "end_paragraph": scene.end_paragraph,
            })
    return json.dumps(data, ensure_ascii=False, indent=2)

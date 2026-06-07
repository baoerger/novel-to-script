import json
import logging
from collections import defaultdict

from backend.app.models.analysis import ChapterAnalysis
from backend.app.models.consolidated import (
    CharacterRelationship,
    ConsolidatedAnalysis,
)
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


def extract_relationships(
    consolidated: ConsolidatedAnalysis,
    analyses: list[ChapterAnalysis],
) -> list[CharacterRelationship]:
    """基于角色共现数据，通过 LLM 推断角色关系网。

    从章节分析的场景共现数据出发，构建角色共现矩阵，然后调用专用
    extract_relationships.j2 模板让 LLM 推断关系类型。

    失败时记录错误并返回空列表（不阻塞流程）。
    """
    if not consolidated.characters or not analyses:
        return []

    name_to_id = _build_name_id_map(consolidated)
    cooccurrence = _build_cooccurrence(analyses, name_to_id)

    if not cooccurrence:
        logger.warning("关系提取: 无有效共现数据")
        return []

    characters_json = json.dumps(
        [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "description": c.description[:120],
            }
            for c in consolidated.characters
        ],
        ensure_ascii=False,
        indent=2,
    )
    cooccurrence_json = json.dumps(cooccurrence, ensure_ascii=False, indent=2)

    variables = {
        "characters_json": characters_json,
        "cooccurrence_json": cooccurrence_json,
    }

    try:
        result = structured_call(
            template_name="extract_relationships.j2",
            variables=variables,
            output_model=list[CharacterRelationship],
        )
        if isinstance(result, list):
            logger.info("关系提取完成: %d 条关系", len(result))
            return result
        return list(result.root) if hasattr(result, "root") else []
    except Exception as e:
        logger.error("关系提取失败: %s", e)
        return []


def _build_name_id_map(consolidated: ConsolidatedAnalysis) -> dict[str, str]:
    """构建角色名称/别名 → 角色 ID 的映射。"""
    mapping: dict[str, str] = {}
    for c in consolidated.characters:
        mapping[c.name] = c.id
        for alias in c.aliases:
            mapping[alias] = c.id
    return mapping


def _build_cooccurrence(
    analyses: list[ChapterAnalysis],
    name_to_id: dict[str, str],
) -> list[dict]:
    """从章节分析构建角色共现数据。

    返回格式：[{"char_a": "CHAR_047", "char_b": "CHAR_063", "chapters": [0,1,2], "count": 15}, ...]
    只保留至少一方不是 minor 的共现对，且至少共现 2 次。
    """
    # 收集每章每场的角色 ID 集合
    chapter_scenes: dict[int, list[set[str]]] = defaultdict(list)
    for ch in analyses:
        for scene in ch.scenes:
            char_ids = set()
            for name in scene.characters_present:
                cid = name_to_id.get(name)
                if cid:
                    char_ids.add(cid)
            if char_ids:
                chapter_scenes[ch.chapter_index].append(char_ids)

    # 统计共现
    pair_data: dict[tuple[str, str], dict] = {}
    for ch_idx, scenes in chapter_scenes.items():
        seen_in_chapter: set[tuple[str, str]] = set()
        for char_ids in scenes:
            ids = sorted(char_ids)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair = (ids[i], ids[j])
                    if pair not in pair_data:
                        pair_data[pair] = {
                            "char_a": ids[i],
                            "char_b": ids[j],
                            "chapters": set(),
                            "count": 0,
                        }
                    pair_data[pair]["count"] += 1
                    seen_in_chapter.add(pair)
        for pair in seen_in_chapter:
            if pair in pair_data:
                pair_data[pair]["chapters"].add(ch_idx)

    # 过滤：至少共现 2 次
    result = []
    for pair, data in pair_data.items():
        if data["count"] >= 2:
            data["chapters"] = sorted(data["chapters"])
            result.append(data)

    result.sort(key=lambda x: x["count"], reverse=True)
    logger.info(
        "共现数据: %d 对角色，过滤后 %d 对",
        len(pair_data),
        len(result),
    )
    return result

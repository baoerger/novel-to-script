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

    # 构建带角色信息的共现数据
    id_to_info: dict[str, dict] = {
        c.id: {"name": c.name, "role": c.role}
        for c in consolidated.characters
    }
    # 在共现数据中附加角色名称和角色类型
    enriched = []
    for entry in cooccurrence:
        char_id = entry["char_id"]
        info = id_to_info.get(char_id, {})
        enriched_others = []
        for other in entry["co_occurs_with"]:
            other_info = id_to_info.get(other["char_id"], {})
            enriched_others.append({
                "char_id": other["char_id"],
                "name": other_info.get("name", other["char_id"]),
                "role": other_info.get("role", "minor"),
                "chapters": other["chapters"],
                "count": other["count"],
            })
        enriched.append({
            "char_id": char_id,
            "name": info.get("name", char_id),
            "role": info.get("role", "minor"),
            "co_occurs_with": enriched_others,
        })

    characters_json = json.dumps(
        [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "archetype": c.archetype,
                "description": c.description[:120],
            }
            for c in consolidated.characters
        ],
        ensure_ascii=False,
        indent=2,
    )
    cooccurrence_json = json.dumps(enriched, ensure_ascii=False, indent=2)

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


def filter_trivial_minors(consolidated: ConsolidatedAnalysis) -> ConsolidatedAnalysis:
    """过滤掉信息量过少的龙套角色。

    满足以下全部条件的视为冗余龙套，从角色列表和时间线中移除：
    - role == "minor"
    - description 少于 30 个字符
    - 只在 1 个章节中出现

    同时清理时间线场景中的角色引用。
    """
    if not consolidated.characters:
        return consolidated

    keep_ids: set[str] = set()
    removed_ids: set[str] = set()

    for c in consolidated.characters:
        if (
            c.role == "minor"
            and len(c.description) < 30
            and len(c.appears_in_chapters) <= 1
        ):
            removed_ids.add(c.id)
        else:
            keep_ids.add(c.id)

    if removed_ids:
        consolidated.characters = [
            c for c in consolidated.characters if c.id in keep_ids
        ]
        for ts in consolidated.timeline:
            ts.characters = [cid for cid in ts.characters if cid in keep_ids]
        logger.info(
            "过滤龙套角色: 移除 %d 个 (保留 %d 个)",
            len(removed_ids),
            len(keep_ids),
        )

    return consolidated


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

    按角色组织共现对，每个角色列出其所有共现者及频次。
    返回格式适合 LLM 逐角色推断关系网络。
    只保留至少共现 2 次的配对，且跳过两个都是 minor 的组合。
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

    # 统计共现：(char_a, char_b) → {chapters: set, count: int}
    pair_data: dict[tuple[str, str], dict] = {}
    for ch_idx, scenes in chapter_scenes.items():
        seen: set[tuple[str, str]] = set()
        for char_ids in scenes:
            ids = sorted(char_ids)
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair = (ids[i], ids[j])
                    if pair not in pair_data:
                        pair_data[pair] = {"chapters": set(), "count": 0}
                    pair_data[pair]["count"] += 1
                    seen.add(pair)
        for pair in seen:
            pair_data[pair]["chapters"].add(ch_idx)

    # 整理为角色→共现者列表格式
    per_char: dict[str, list[dict]] = defaultdict(list)
    for (a, b), data in pair_data.items():
        if data["count"] < 2:
            continue
        per_char[a].append({
            "char_id": b,
            "chapters": sorted(data["chapters"]),
            "count": data["count"],
        })
        per_char[b].append({
            "char_id": a,
            "chapters": sorted(data["chapters"]),
            "count": data["count"],
        })

    # 转为列表，按角色重要性排序：protagonist → supporting → minor
    result = []
    for char_id, co_occurrences in per_char.items():
        co_occurrences.sort(key=lambda x: x["count"], reverse=True)
        result.append({
            "char_id": char_id,
            "co_occurs_with": co_occurrences,
        })

    result.sort(key=lambda x: len(x["co_occurs_with"]), reverse=True)
    logger.info(
        "共现数据: %d 对角色 → %d 个角色有共现数据",
        len(pair_data),
        len(result),
    )
    return result

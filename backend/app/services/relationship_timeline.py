import logging

from app.models.consolidated import ConsolidatedAnalysis, TimelineScene

logger = logging.getLogger(__name__)


def build_relationship_graph(
    consolidated: ConsolidatedAnalysis,
) -> dict[str, list[dict]]:
    """基于角色关系列表构建邻接表关系图。

    返回 {char_id: [{to: id, relation: str, description: str}, ...]} 格式。
    每个关系会双向记录。
    """
    graph: dict[str, list[dict]] = {}

    for rel in consolidated.relationships:
        graph.setdefault(rel.from_char, []).append({
            "to": rel.to_char,
            "relation": rel.relation,
            "description": rel.description,
        })
        graph.setdefault(rel.to_char, []).append({
            "to": rel.from_char,
            "relation": _reverse_relation(rel.relation),
            "description": rel.description,
        })

    return graph


def sort_timeline(timeline: list[TimelineScene]) -> list[TimelineScene]:
    """按来源章节与场景 ID 排序全局时间线。"""
    return sorted(timeline, key=lambda s: (s.source_chapter, s.scene_id))


def validate_consolidated(consolidated: ConsolidatedAnalysis) -> list[str]:
    """校验 ConsolidatedAnalysis 中角色引用的一致性。

    检查关系中的角色 ID 和时间线中的角色 ID 是否在角色列表中存在。
    返回问题描述列表。
    """
    issues: list[str] = []
    char_ids = {c.id for c in consolidated.characters}

    for rel in consolidated.relationships:
        if rel.from_char not in char_ids:
            issues.append(f"关系源角色 {rel.from_char} 未在角色列表中定义")
        if rel.to_char not in char_ids:
            issues.append(f"关系目标角色 {rel.to_char} 未在角色列表中定义")

    for scene in consolidated.timeline:
        for char_id in scene.characters:
            if char_id not in char_ids:
                issues.append(
                    f"时间线 {scene.scene_id} 引用未定义角色 {char_id}"
                )

    if issues:
        logger.warning("ConsolidatedAnalysis 一致性校验发现问题: %s", issues)

    return issues


def process_consolidated(consolidated: ConsolidatedAnalysis) -> ConsolidatedAnalysis:
    """对跨章汇总结果进行后处理：排序时间线、校验一致性。

    如果校验发现角色引用不一致问题，通过日志记录但不阻断流程。
    """
    consolidated.timeline = sort_timeline(consolidated.timeline)
    validate_consolidated(consolidated)
    return consolidated


def _reverse_relation(relation: str) -> str:
    """反转关系方向时的关系类型映射。"""
    reverse_map = {
        "师徒": "弟子",
        "父子": "子女",
        "母女": "子女",
        "主仆": "仆从",
        "统治者": "被统治者",
    }
    return reverse_map.get(relation, relation)

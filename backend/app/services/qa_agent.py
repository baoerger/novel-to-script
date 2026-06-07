"""质检 Agent：自动检查生成剧本的格式规范性、角色一致性和结构完整性。

质检不阻塞转换流程，仅生成 AdaptationNote 列表供用户参考。
"""

from backend.app.models.script import (
    AdaptationNote,
    ContentType,
    Script,
)


def qa_check(script: Script) -> list[AdaptationNote]:
    """对完整剧本执行所有质检项，返回备注列表。

    检查三类问题：
    - 格式规范 (format): 场景内容为空、对话缺 speaker
    - 角色一致性 (character): 幽灵角色、角色清单不完整
    - 结构完整 (structure): 溯源映射缺失、场标题缺失
    """
    notes: list[AdaptationNote] = []

    # 收集所有已知角色 ID
    known_ids = {c.id for c in script.characters}

    # 收集所有溯源映射覆盖的 scene_id
    mapped_ids = {m.scene_id for m in script.source_mapping}

    for act in script.acts:
        for scene in act.scenes:
            sid = scene.scene_id
            notes.extend(_check_format(sid, scene))
            notes.extend(_check_characters(sid, scene, known_ids))
            notes.extend(_check_structure(sid, scene, mapped_ids))

    return notes


def _check_format(
    scene_id: str, scene
) -> list[AdaptationNote]:
    """格式规范性检查。"""
    notes: list[AdaptationNote] = []

    # 场景内容不能为空
    if not scene.content:
        notes.append(AdaptationNote(
            scene_id=scene_id,
            severity="warning",
            message="场景内容为空，可能生成失败",
        ))
        return notes

    for i, elem in enumerate(scene.content):
        prefix = f"第{i + 1}个元素"

        # 对白/独白必须有说话角色
        if elem.type in (ContentType.DIALOGUE, ContentType.VOICEOVER):
            if not elem.character:
                notes.append(AdaptationNote(
                    scene_id=scene_id,
                    severity="warning",
                    message=f"{prefix}: {elem.type} 缺少角色归属",
                ))

        # 文本内容不应为空
        if not elem.text and elem.type != ContentType.TRANSITION:
            notes.append(AdaptationNote(
                scene_id=scene_id,
                severity="info",
                message=f"{prefix}: {elem.type} 文本为空",
            ))

    return notes


def _check_characters(
    scene_id: str, scene, known_ids: set[str]
) -> list[AdaptationNote]:
    """角色一致性检查。"""
    notes: list[AdaptationNote] = []

    # characters_present 中的角色是否都在总清单中
    for char_id in scene.characters_present:
        if char_id not in known_ids:
            notes.append(AdaptationNote(
                scene_id=scene_id,
                severity="warning",
                message=f"出场角色 {char_id} 不在角色总清单中（幽灵角色）",
            ))

    # content 中对白的角色是否都在总清单中
    for i, elem in enumerate(scene.content):
        if elem.character and elem.character not in known_ids:
            notes.append(AdaptationNote(
                scene_id=scene_id,
                severity="warning",
                message=f"第{i + 1}个元素: 角色 {elem.character} 不在角色总清单中",
            ))

    return notes


def _check_structure(
    scene_id: str, scene, mapped_ids: set[str]
) -> list[AdaptationNote]:
    """结构完整性检查。"""
    notes: list[AdaptationNote] = []

    # 场标题不能为空
    if not scene.scene_heading:
        notes.append(AdaptationNote(
            scene_id=scene_id,
            severity="info",
            message="场景缺少场标题 (scene_heading)",
        ))

    # 溯源映射覆盖检查
    if scene_id not in mapped_ids:
        notes.append(AdaptationNote(
            scene_id=scene_id,
            severity="info",
            message="场景缺少溯源映射 (source_mapping)",
        ))

    return notes

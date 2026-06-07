import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from backend.app.models.input import NovelText
from backend.app.models.analysis import ChapterAnalysis
from backend.app.models.script import (
    AdaptationNote,
    CharacterRelation,
    Script,
    ScriptAct,
    ScriptCharacter,
    ScriptMeta,
    ScriptScene,
    Setting,
    SourceMapping,
)
from backend.app.services.checkpoint import CheckpointManager
from backend.app.services.chunker import split_long_chapter
from backend.app.services.consolidate import (
    extract_relationships,
    filter_trivial_minors,
    merge_and_consolidate,
)
from backend.app.services.orchestrator import analyze_chapter
from backend.app.services.qa_agent import qa_check
from backend.app.services.relationship_timeline import process_consolidated
from backend.app.services.scene_generator import generate_scene
from backend.app.services.task_manager import TaskManager
from backend.app.services.yaml_writer import save_script

logger = logging.getLogger(__name__)


def run_conversion(
    novel_text: NovelText,
    task_manager: TaskManager,
    task_id: str,
    output_dir: str | Path,
    max_tokens_per_chapter: int = 15000,
) -> Script | None:
    """执行小说→剧本完整转换流程，每阶段自动 checkpoint。

    串联全部阶段：
    1. 章节分片 → 2. 逐章分析 → 3. 跨章汇总 → 4. 关系时间线
    → 5. 场景生成 → 6. 组装 Script → 7. YAML 写入

    每阶段完成后落盘到 output_dir/ 下，重启时自动跳过已完成阶段。
    """
    output_dir = Path(output_dir)
    ck = CheckpointManager(output_dir)

    try:
        total_start = time.perf_counter()
        task_manager.update_progress(task_id, 0, "开始转换")
        task_manager.set_running(task_id)

        # ── Phase 1: 章节分片 ──
        all_chapters = _phase_chunk(
            ck, novel_text, max_tokens_per_chapter, task_manager, task_id
        )

        # ── Phase 2: 逐章分析 ──
        analyses = _phase_analyze(
            ck, all_chapters, task_manager, task_id
        )

        # ── Phase 3: 跨章汇总 ──
        consolidated = _phase_consolidate(
            ck, analyses, task_manager, task_id
        )

        # ── Phase 3.5: 关系提取 ──
        consolidated = _phase_relationships(
            ck, consolidated, analyses, task_manager, task_id
        )

        # ── Phase 4: 场景生成 ──
        script_scenes = _phase_generate_scenes(
            ck, consolidated, all_chapters, task_manager, task_id
        )

        # ── Phase 5: 组装 Script ──
        task_manager.update_progress(task_id, 85, "组装剧本中")
        script = _phase_assemble(ck, novel_text, consolidated, script_scenes)

        # ── YAML 写入 ──
        task_manager.update_progress(task_id, 95, "写入 YAML")
        result_path = output_dir / f"{_safe_filename(novel_text.title)}.yaml"
        save_script(script, result_path)

        task_manager.set_completed(task_id, str(result_path))
        logger.info(
            "转换完成: %s → %s (总耗时 %.1fs)",
            novel_text.title, result_path, time.perf_counter() - total_start,
        )
        return script

    except Exception as e:
        logger.exception("转换流程异常: %s", e)
        task_manager.set_failed(task_id, str(e))
        return None


# ═══════════════════════════════════════════════════════════════
# 各阶段实现（每个阶段先查 checkpoint，已完成则跳过）
# ═══════════════════════════════════════════════════════════════

def _phase_chunk(ck, novel_text, max_tokens, task_manager, task_id):
    """Phase 1: 章节分片。先读 checkpoint，有则跳过。"""
    if ck.is_done("chunked"):
        cached = ck.load_chapters(novel_text.title)
        if cached is not None:
            logger.info("Phase 1 跳过 — checkpoint 已存在 (%d 章)", len(cached))
            return cached
    chapters = _chunk_all(novel_text, max_tokens)
    ck.save_chapters(novel_text, chapters)
    ck.mark_done("chunked")
    task_manager.update_progress(task_id, 5, f"章节分片完成 ({len(chapters)} 章)")
    return chapters


def _phase_analyze(ck, all_chapters, task_manager, task_id):
    """Phase 2: 逐章分析。逐章检查 checkpoint，跳过已完成的。"""
    if ck.is_done("analyses"):
        cached = ck.load_all_analyses()
        if len(cached) == len(all_chapters):
            logger.info("Phase 2 跳过 — checkpoint 已存在 (%d 章)", len(cached))
            task_manager.update_progress(task_id, 50, "逐章分析 (已缓存)")
            return cached
        logger.info("Phase 2 部分恢复 — 缓存 %d/%d 章", len(cached), len(all_chapters))

    total = len(all_chapters)
    analyses = ck.load_all_analyses()  # 恢复已完成的
    completed_indices = {a.chapter_index for a in analyses}

    # 过滤出未完成的章节
    pending = [
        (i, ch) for i, ch in enumerate(all_chapters)
        if ch.chapter_index not in completed_indices
    ]

    if not pending:
        ck.mark_done("analyses")
        return analyses

    task_manager.update_progress(task_id, 10, f"逐章分析中 ({len(analyses)}/{total} 已缓存)")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(analyze_chapter, ch): idx
            for idx, ch in pending
        }
        completed = len(analyses)
        for future in as_completed(futures):
            try:
                result = future.result()
                if result is not None:
                    ck.save_analysis(result)
                    analyses.append(result)
            except Exception as e:
                logger.error("章节分析失败: %s", e)
            completed += 1
            progress = 10 + int(40 * completed / total)
            task_manager.update_progress(task_id, progress, f"分析中 {completed}/{total}")

    ck.mark_done("analyses")
    return [a for a in analyses if a is not None]


def _phase_consolidate(ck, analyses, task_manager, task_id):
    """Phase 3: 跨章汇总去重。"""
    if ck.is_done("consolidated"):
        cached = ck.load_consolidated()
        if cached is not None:
            logger.info("Phase 3 跳过 — checkpoint 已存在")
            task_manager.update_progress(task_id, 65, "跨章汇总 (已缓存)")
            return cached

    t0 = time.perf_counter()
    task_manager.update_progress(task_id, 50, "跨章汇总去重中")
    consolidated = merge_and_consolidate(analyses)
    consolidated = process_consolidated(consolidated)
    consolidated = filter_trivial_minors(consolidated)
    logger.info("Phase 3 (跨章汇总) 耗时: %.1fs", time.perf_counter() - t0)

    ck.save_consolidated(consolidated)
    ck.mark_done("consolidated")
    return consolidated


def _phase_relationships(ck, consolidated, analyses, task_manager, task_id):
    """Phase 3.5: 基于共现数据提取角色关系。"""
    if ck.is_done("relationships"):
        cached = ck.load_consolidated()
        if cached is not None and cached.relationships:
            logger.info("Phase 3.5 跳过 — checkpoint 已存在 (%d 条关系)", len(cached.relationships))
            task_manager.update_progress(task_id, 68, "角色关系 (已缓存)")
            consolidated.relationships = cached.relationships
            return consolidated

    t0 = time.perf_counter()
    task_manager.update_progress(task_id, 60, "提取角色关系中")
    relationships = extract_relationships(consolidated, analyses)
    consolidated.relationships = relationships
    logger.info(
        "Phase 3.5 (关系提取) 耗时: %.1fs, %d 条关系",
        time.perf_counter() - t0,
        len(relationships),
    )
    ck.save_consolidated(consolidated)
    ck.mark_done("relationships")
    return consolidated


def _phase_generate_scenes(ck, consolidated, chapters, task_manager, task_id):
    """Phase 4: 场景生成。逐场景检查 checkpoint。"""
    timeline_ids = [ts.scene_id for ts in consolidated.timeline]

    if ck.is_done("scenes"):
        cached = ck.load_all_scenes(timeline_ids)
        if cached is not None:
            logger.info("Phase 4 跳过 — checkpoint 已存在 (%d 场)", len(cached))
            task_manager.update_progress(task_id, 85, "场景生成 (已缓存)")
            return cached
        # 部分缓存
        logger.info("Phase 4 部分恢复")

    chapter_map = {ch.chapter_index: ch.raw_text for ch in chapters}
    chars_info_lines = []
    for c in consolidated.characters:
        chars_info_lines.append(
            f"- {c.id} ({c.name}): {c.role}, {c.description[:80]}"
        )
    characters_info = "\n".join(chars_info_lines)

    total = len(consolidated.timeline)
    # 尝试从缓存恢复已完成的场景
    completed_scenes: dict[str, ScriptScene] = {}
    if ck._scenes_dir.exists():
        for sid in timeline_ids:
            s = ck.load_scene(sid)
            if s is not None:
                completed_scenes[sid] = s

    # 过滤出待生成的场景
    pending = [
        (i, ts) for i, ts in enumerate(consolidated.timeline)
        if ts.scene_id not in completed_scenes
    ]

    if not pending:
        ck.mark_done("scenes")
        return [completed_scenes[sid] for sid in timeline_ids]

    task_manager.update_progress(
        task_id, 65,
        f"场景生成中 ({len(completed_scenes)}/{total} 已缓存)",
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_generate_one_scene, ts, chapter_map, characters_info): idx
            for idx, ts in pending
        }
        completed_count = len(completed_scenes)
        for future in as_completed(futures):
            try:
                scene = future.result()
                if scene is not None:
                    ck.save_scene(scene)
                    completed_scenes[scene.scene_id] = scene
            except Exception as e:
                logger.error("场景生成失败: %s", e)
            completed_count += 1
            progress = 65 + int(20 * completed_count / total)
            task_manager.update_progress(task_id, progress, f"场景 {completed_count}/{total}")

    ck.mark_done("scenes")
    return [completed_scenes.get(sid) for sid in timeline_ids if sid in completed_scenes]


def _phase_assemble(ck, novel_text, consolidated, scenes):
    """Phase 5: 组装 Script 并缓存。"""
    if ck.is_done("script"):
        cached = ck.load_script()
        if cached is not None:
            logger.info("Phase 5 跳过 — script.json 已存在")
            return cached
    script = _build_script(novel_text, consolidated, scenes)
    ck.save_script(script)
    ck.mark_done("script")
    return script


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _chunk_all(novel_text, max_tokens):
    chapters = []
    for ch in novel_text.chapters:
        sub_chapters, _summary = split_long_chapter(ch, max_tokens=max_tokens)
        chapters.extend(sub_chapters)
    return chapters


def _generate_one_scene(ts, chapter_map, characters_info) -> ScriptScene:
    scene_text = chapter_map.get(ts.source_chapter, "")
    try:
        content = generate_scene(
            scene_id=ts.scene_id,
            source_chapter=ts.source_chapter,
            location=ts.location,
            time_hint=ts.time_hint,
            summary=ts.summary,
            characters_info=characters_info,
            scene_text=scene_text,
        )
    except Exception as e:
        logger.error("场景 %s 生成失败: %s", ts.scene_id, e)
        content = []

    return ScriptScene(
        scene_id=ts.scene_id,
        scene_heading=_build_heading(ts.location, ts.time_hint),
        setting=Setting(location=ts.location, time=ts.time_hint, description=ts.summary),
        characters_present=ts.characters,
        content=content,
    )


def _build_script(novel_text, consolidated, scenes) -> Script:
    meta = ScriptMeta(
        title=novel_text.title,
        source_novel=novel_text.title,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_acts=0,
        total_scenes=len(scenes),
    )

    characters = [
        ScriptCharacter(
            id=c.id,
            name=c.name,
            aliases=c.aliases,
            role=c.role,
            archetype=c.archetype,
            description=c.description,
        )
        for c in consolidated.characters
    ]

    relationships = [
        CharacterRelation(
            from_char=r.from_char,
            to_char=r.to_char,
            relation=r.relation,
            description=r.description,
        )
        for r in consolidated.relationships
    ]

    acts = _split_into_acts(scenes, consolidated.timeline)
    meta.total_acts = len(acts)

    source_mapping = _build_source_mapping(consolidated.timeline)

    script = Script(
        meta=meta,
        characters=characters,
        character_relationships=relationships,
        acts=acts,
        source_mapping=source_mapping,
        adaptation_notes=[],
    )

    # 基础检查 + AI 质检
    notes = _build_adaptation_notes(scenes)
    notes.extend(qa_check(script))
    script.adaptation_notes = notes

    return script


def _build_heading(location: str, time_hint: str) -> str:
    loc = location if location and location != "未知" else "某处"
    time_str = time_hint if time_hint and time_hint != "未知" else ""
    return f"INT. {loc}" + (f" - {time_str}" if time_str else "")


def _safe_filename(title: str) -> str:
    unsafe = r'<>:"/\|?*'
    result = title
    for ch in unsafe:
        result = result.replace(ch, "_")
    return result.strip()[:100]


def _build_source_mapping(timeline) -> list[SourceMapping]:
    """从时间线自动生成溯源映射，每个场景标记其来源章节。"""
    return [
        SourceMapping(
            scene_id=ts.scene_id,
            source_chapter=ts.source_chapter,
            source_paragraphs=[],
        )
        for ts in timeline
    ]


def _build_adaptation_notes(scenes: list[ScriptScene]) -> list[AdaptationNote]:
    """轻量质检：检查场景内容完整性和地点/时间信息。"""
    notes: list[AdaptationNote] = []
    for scene in scenes:
        if not scene.content:
            notes.append(AdaptationNote(
                scene_id=scene.scene_id,
                severity="warning",
                message=f"场景 {scene.scene_id} 内容为空，可能生成失败",
            ))
        if not scene.setting.location or scene.setting.location == "未知":
            notes.append(AdaptationNote(
                scene_id=scene.scene_id,
                severity="info",
                message=f"场景 {scene.scene_id} 地点信息不完整",
            ))
        if not scene.setting.time or scene.setting.time == "未知":
            notes.append(AdaptationNote(
                scene_id=scene.scene_id,
                severity="info",
                message=f"场景 {scene.scene_id} 时间信息不完整",
            ))
    return notes


def _split_into_acts(
    scenes: list[ScriptScene],
    timeline: list,
) -> list[ScriptAct]:
    """按场景数+章节边界将场景列表切分为幕。

    每幕约 12 场，在章节边界处切分以保证剧情完整性。
    需要 timeline 来获取每个场景的 source_chapter。
    """
    SCENES_PER_ACT = 12
    if not scenes:
        return []

    # 建立 scene_id → source_chapter 映射
    ch_map = {ts.scene_id: ts.source_chapter for ts in timeline}

    acts: list[ScriptAct] = []
    batch: list[ScriptScene] = []
    last_chapter: int | None = None

    for scene in scenes:
        current_chapter = ch_map.get(scene.scene_id)
        if (
            len(batch) >= SCENES_PER_ACT
            and current_chapter is not None
            and last_chapter is not None
            and current_chapter != last_chapter
        ):
            acts.append(_make_act(len(acts), batch))
            batch = []
        batch.append(scene)
        last_chapter = current_chapter

    if batch:
        acts.append(_make_act(len(acts), batch))

    return acts


def _make_act(act_num: int, scenes: list[ScriptScene]) -> ScriptAct:
    """创建一个有中文序数标题的幕。"""
    _TITLES = [
        "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
        "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
        "二十一", "二十二", "二十三", "二十四", "二十五",
    ]
    title = f"第{_TITLES[act_num]}幕" if act_num < len(_TITLES) else f"第{act_num + 1}幕"
    return ScriptAct(act_number=act_num, act_title=title, scenes=scenes)

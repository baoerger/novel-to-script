import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from backend.app.models.input import NovelText
from backend.app.models.script import (
    CharacterRelation,
    Script,
    ScriptAct,
    ScriptCharacter,
    ScriptMeta,
    ScriptScene,
    Setting,
)
from backend.app.services.chunker import split_long_chapter
from backend.app.services.consolidate import merge_and_consolidate
from backend.app.services.orchestrator import analyze_chapter
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
    """执行小说→剧本完整转换流程。

    串联全部阶段：
    1. 章节分片 → 2. 逐章分析 → 3. 跨章汇总 → 4. 关系时间线
    → 5. 场景生成 → 6. 组装 Script → 7. YAML 写入

    进度通过 TaskManager 上报。失败时标记任务为 failed 并返回 None。
    """
    output_dir = Path(output_dir)

    try:
        task_manager.update_progress(task_id, 0, "开始转换")
        task_manager.set_running(task_id)

        # ── Phase 2: 章节分片 ──
        task_manager.update_progress(task_id, 5, "章节分片中")
        all_chapters = _chunk_all(novel_text, max_tokens_per_chapter)

        # ── Phase 4: 逐章分析（并行） ──
        task_manager.update_progress(task_id, 10, "逐章分析中")
        analyses = _analyze_all(all_chapters, task_manager, task_id)

        # ── Phase 5: 跨章汇总 ──
        task_manager.update_progress(task_id, 50, "跨章汇总去重中")
        consolidated = merge_and_consolidate(analyses)
        consolidated = process_consolidated(consolidated)

        # ── Phase 6: 场景生成 ──
        task_manager.update_progress(task_id, 65, "场景剧本生成中")
        script_scenes = _generate_all_scenes(
            consolidated, all_chapters, task_manager, task_id
        )

        # ── 组装 Script ──
        task_manager.update_progress(task_id, 85, "组装剧本中")
        script = _build_script(
            novel_text=novel_text,
            consolidated=consolidated,
            scenes=script_scenes,
        )

        # ── YAML 写入 ──
        task_manager.update_progress(task_id, 95, "写入 YAML")
        result_path = output_dir / f"{_safe_filename(novel_text.title)}.yaml"
        save_script(script, result_path)

        task_manager.set_completed(task_id, str(result_path))
        logger.info("转换完成: %s → %s", novel_text.title, result_path)
        return script

    except Exception as e:
        logger.exception("转换流程异常: %s", e)
        task_manager.set_failed(task_id, str(e))
        return None


def _chunk_all(novel_text, max_tokens):
    """对所有章节执行分片，返回扁平化的章节列表。"""
    chapters = []
    for ch in novel_text.chapters:
        sub_chapters, _summary = split_long_chapter(ch, max_tokens=max_tokens)
        chapters.extend(sub_chapters)
    return chapters


def _analyze_all(chapters, task_manager, task_id):
    """并行分析所有章节，按进度比例更新。"""
    total = len(chapters)
    analyses = [None] * total

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(analyze_chapter, ch): i for i, ch in enumerate(chapters)}
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                analyses[idx] = future.result()
            except Exception as e:
                logger.error("章节 %d 分析失败: %s", idx, e)
                analyses[idx] = None
            completed += 1
            progress = 10 + int(40 * completed / total)
            task_manager.update_progress(task_id, progress, f"分析中 {completed}/{total}")

    return [a for a in analyses if a is not None]


def _generate_all_scenes(consolidated, chapters, task_manager, task_id):
    """为时间线中的每个场景生成剧本内容元素。"""
    # 构建章节索引：chapter_index → raw_text
    chapter_map = {ch.chapter_index: ch.raw_text for ch in chapters}

    # 构建角色 info 字符串
    char_map = {c.id: c for c in consolidated.characters}
    chars_info_lines = []
    for c in consolidated.characters:
        chars_info_lines.append(
            f"- {c.id} ({c.name}): {c.role}, {c.description[:80]}"
        )
    characters_info = "\n".join(chars_info_lines)

    total = len(consolidated.timeline)
    scenes = []
    for i, ts in enumerate(consolidated.timeline):
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

        script_scene = ScriptScene(
            scene_id=ts.scene_id,
            scene_heading=_build_heading(ts.location, ts.time_hint),
            setting=Setting(location=ts.location, time=ts.time_hint, description=ts.summary),
            characters_present=ts.characters,
            content=content,
        )
        scenes.append(script_scene)

        progress = 65 + int(20 * (i + 1) / total)
        task_manager.update_progress(task_id, progress, f"场景 {i + 1}/{total}")

    return scenes


def _build_script(novel_text, consolidated, scenes) -> Script:
    """组装完整 Script 对象。"""
    meta = ScriptMeta(
        title=novel_text.title,
        source_novel=novel_text.title,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_acts=1,
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

    act = ScriptAct(act_number=0, act_title="第一幕", scenes=scenes)

    return Script(
        meta=meta,
        characters=characters,
        character_relationships=relationships,
        acts=[act],
    )


def _build_heading(location: str, time_hint: str) -> str:
    """构建剧本场标题，如 INT. 城主府 - 日"""
    loc = location if location and location != "未知" else "某处"
    time_str = time_hint if time_hint and time_hint != "未知" else ""
    return f"INT. {loc}" + (f" - {time_str}" if time_str else "")


def _safe_filename(title: str) -> str:
    """将书名转为安全的文件名。"""
    # 移除或替换不安全字符
    unsafe = r'<>:"/\|?*'
    result = title
    for ch in unsafe:
        result = result.replace(ch, "_")
    return result.strip()[:100]

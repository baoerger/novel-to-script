"""转换质量评估报告生成器。

生成 Markdown 格式报告，包含转换概览、质量指标、QA 问题详情和成本估算。
"""

from datetime import datetime, timezone

from backend.app.models.script import ContentType, Script


def generate_report(
    script: Script,
    total_duration_s: float,
    total_tokens: int,
    chapter_count: int,
    degradation_events: list[dict] | None = None,
) -> str:
    """生成 Markdown 格式的质量评估报告。

    Args:
        script: 转换完成的 Script 对象
        total_duration_s: 转换总耗时（秒）
        total_tokens: 估算的总 Token 用量
        chapter_count: 原始章节数
        degradation_events: 降级事件列表，每项含 {phase, detail}
    """
    lines: list[str] = []
    _section(lines, 1, f"转换报告: {script.meta.title}")

    _section(lines, 2, "转换概览")
    total_dialogues = _count_dialogues(script)
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 书名 | {script.meta.source_novel} |")
    lines.append(f"| 原始章节数 | {chapter_count} |")
    lines.append(f"| 角色数 | {len(script.characters)} |")
    lines.append(f"| 幕数 | {script.meta.total_acts} |")
    lines.append(f"| 场次数 | {script.meta.total_scenes} |")
    lines.append(f"| 对白数 | {total_dialogues} |")
    lines.append(f"| 总耗时 | {_format_duration(total_duration_s)} |")
    lines.append(f"| 生成时间 | {script.meta.generated_at} |")
    lines.append("")

    _section(lines, 2, "质量评估")
    notes = script.adaptation_notes
    errors = [n for n in notes if n.severity == "warning"]
    warnings = [n for n in notes if n.severity == "info"]
    total_checks = len(notes) + 1  # +1 避免除零
    pass_rate = max(0, 100 - int(100 * len(notes) / total_checks))

    lines.append(f"- **质检通过率**: {pass_rate}%")
    lines.append(f"- **问题总数**: {len(notes)}（warning {len(errors)} 条, info {len(warnings)} 条）")
    lines.append(f"- **角色覆盖率**: {len(script.characters)} 个角色已录入")
    lines.append("")

    if notes:
        _section(lines, 2, "问题详情")
        for n in notes:
            icon = "⚠️" if n.severity == "warning" else "ℹ️"
            sid = n.scene_id or "-"
            lines.append(f"- {icon} **[{n.severity}]** `{sid}`: {n.message}")
        lines.append("")

    _section(lines, 2, "Token 用量估算")
    est_cost = total_tokens / 1_000_000 * 0.28  # DeepSeek 约 ¥0.28/百万 tokens
    lines.append(f"- **Token 总量**: {total_tokens:,}")
    lines.append(f"- **估算成本**: ¥{est_cost:.4f}（基于 DeepSeek V4 公开定价）")
    lines.append("")

    deg = degradation_events or []
    if deg:
        _section(lines, 2, "降级事件")
        for d in deg:
            lines.append(f"- **{d.get('phase', '?')}**: {d.get('detail', '未知')}")
        lines.append("")

    _section(lines, 2, "建议")
    suggestions = _generate_suggestions(script, chapter_count)
    for s in suggestions:
        lines.append(f"- {s}")
    lines.append("")

    lines.append("---")
    lines.append(f"*报告由 AI 小说转剧本工具自动生成于 {datetime.now(timezone.utc).isoformat()}*")
    lines.append("")

    return "\n".join(lines)


def _section(lines: list[str], level: int, title: str) -> None:
    prefix = "#" * level
    lines.append(f"{prefix} {title}")
    lines.append("")


def _count_dialogues(script: Script) -> int:
    count = 0
    for act in script.acts:
        for scene in act.scenes:
            for elem in scene.content:
                if elem.type in (ContentType.DIALOGUE, ContentType.VOICEOVER):
                    count += 1
    return count


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    elif seconds < 3600:
        return f"{seconds / 60:.1f} 分钟"
    else:
        return f"{seconds / 3600:.1f} 小时"


def _generate_suggestions(script: Script, chapter_count: int) -> list[str]:
    suggestions: list[str] = []
    notes = script.adaptation_notes
    errors = [n for n in notes if n.severity == "warning"]

    if errors:
        suggestions.append(
            f"发现 {len(errors)} 个需关注的问题，建议在编辑器中逐条检查修复。"
        )
    else:
        suggestions.append("质量良好，可直接使用或进入在线编辑器微调。")

    if chapter_count > 50:
        suggestions.append("原著超过 50 章，建议按分卷分别转换以降低 API 成本。")

    dialogue_scenes = 0
    for act in script.acts:
        for scene in act.scenes:
            if any(
                e.type in (ContentType.DIALOGUE, ContentType.VOICEOVER)
                for e in scene.content
            ):
                dialogue_scenes += 1

    if dialogue_scenes > 0 and script.meta.total_scenes > 0:
        ratio = dialogue_scenes / max(script.meta.total_scenes, 1)
        if ratio < 0.5:
            suggestions.append(
                f"仅 {dialogue_scenes}/{script.meta.total_scenes} 场包含对白 ({ratio:.0%})，"
                "可检查原文中是否有大量对话未识别。"
            )

    return suggestions

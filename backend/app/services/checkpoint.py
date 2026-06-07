"""中间结果持久化服务。

在 task_dir 下按阶段保存管道中间产物，支持断点续跑。
目录结构：

    task_dir/
    ├── checkpoint.json        ← 阶段完成标记
    ├── chapters.json          ← NovelChapter[]
    ├── analyses/
    │   ├── 0.json             ← ChapterAnalysis (per chapter_index)
    │   └── 1.json
    ├── consolidated.json      ← ConsolidatedAnalysis
    ├── scenes/
    │   ├── SCENE_001.json     ← ScriptScene (per scene_id)
    │   └── SCENE_002.json
    └── script.json            ← 最终组装前的 Script
"""

import json
import logging
from pathlib import Path

from backend.app.models.input import NovelChapter, NovelText
from backend.app.models.analysis import ChapterAnalysis
from backend.app.models.consolidated import ConsolidatedAnalysis
from backend.app.models.script import Script, ScriptScene

logger = logging.getLogger(__name__)

_STAGES = ("chunked", "analyses", "consolidated", "scenes", "script")


class CheckpointManager:
    """管理管道各阶段中间结果的持久化与恢复。"""

    def __init__(self, task_dir: str | Path):
        self._dir = Path(task_dir)
        self._state_path = self._dir / "checkpoint.json"
        self._analyses_dir = self._dir / "analyses"
        self._scenes_dir = self._dir / "scenes"

    # ── 阶段状态 ──

    def _read_state(self) -> dict[str, bool]:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_state(self, state: dict[str, bool]):
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_done(self, stage: str) -> bool:
        return self._read_state().get(stage, False)

    def mark_done(self, stage: str):
        state = self._read_state()
        state[stage] = True
        self._write_state(state)

    def clear_from(self, stage: str):
        """清除指定阶段及之后的所有 checkpoint，用于增量修复后重新跑下游。"""
        state = self._read_state()
        clear = False
        for s in _STAGES:
            if s == stage:
                clear = True
            if clear:
                state.pop(s, None)
        self._write_state(state)

    # ── 章节分片 ──

    def save_chapters(self, novel_text: NovelText, chapters: list[NovelChapter]):
        path = self._dir / "chapters.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "title": novel_text.title,
            "chapters": [ch.model_dump(mode="json") for ch in chapters],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_chapters(self, title: str) -> list[NovelChapter] | None:
        path = self._dir / "chapters.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("title") != title:
                return None  # 书名变了，分片结果无效
            return [NovelChapter(**ch) for ch in data["chapters"]]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    # ── 逐章分析 ──

    def save_analysis(self, analysis: ChapterAnalysis):
        self._analyses_dir.mkdir(parents=True, exist_ok=True)
        path = self._analyses_dir / f"{analysis.chapter_index}.json"
        path.write_text(
            json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_analysis(self, chapter_index: int) -> ChapterAnalysis | None:
        path = self._analyses_dir / f"{chapter_index}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ChapterAnalysis(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def load_all_analyses(self) -> list[ChapterAnalysis]:
        if not self._analyses_dir.exists():
            return []
        analyses = []
        for f in sorted(self._analyses_dir.iterdir(), key=lambda x: int(x.stem)):
            result = self.load_analysis(int(f.stem))
            if result is not None:
                analyses.append(result)
        return analyses

    # ── 汇总去重 ──

    def save_consolidated(self, consolidated: ConsolidatedAnalysis):
        path = self._dir / "consolidated.json"
        path.write_text(
            json.dumps(consolidated.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_consolidated(self) -> ConsolidatedAnalysis | None:
        path = self._dir / "consolidated.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ConsolidatedAnalysis(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    # ── 场景生成 ──

    def save_scene(self, scene: ScriptScene):
        self._scenes_dir.mkdir(parents=True, exist_ok=True)
        path = self._scenes_dir / f"{scene.scene_id}.json"
        path.write_text(
            json.dumps(scene.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_scene(self, scene_id: str) -> ScriptScene | None:
        path = self._scenes_dir / f"{scene_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ScriptScene(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def load_all_scenes(self, timeline_scene_ids: list[str]) -> list[ScriptScene] | None:
        """按时间线顺序加载所有已完成场景。如果有任何一个缺失则返回 None。"""
        scenes = []
        for sid in timeline_scene_ids:
            s = self.load_scene(sid)
            if s is None:
                return None
            scenes.append(s)
        return scenes

    # ── 最终 Script ──

    def save_script(self, script: Script):
        path = self._dir / "script.json"
        path.write_text(
            json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_script(self) -> Script | None:
        path = self._dir / "script.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Script(**data)
        except (json.JSONDecodeError, TypeError):
            return None

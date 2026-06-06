from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.models.analysis import ChapterAnalysis, ExtractedCharacter, SceneBoundary
from backend.app.models.consolidated import (
    CharacterRelationship,
    ConsolidatedAnalysis,
    ConsolidatedCharacter,
    TimelineScene,
)
from backend.app.models.input import NovelChapter, NovelText
from backend.app.services.task_manager import TaskManager


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_txt_short() -> Path:
    return FIXTURES_DIR / "sample_short.txt"


@pytest.fixture
def sample_txt_medium() -> Path:
    return FIXTURES_DIR / "sample_medium.txt"


@pytest.fixture
def sample_txt_long_chapter() -> Path:
    return FIXTURES_DIR / "sample_long_chapter.txt"


@pytest.fixture
def sample_txt_no_chapters() -> Path:
    return FIXTURES_DIR / "sample_no_chapters.txt"


@pytest.fixture
def sample_docx() -> Path:
    return FIXTURES_DIR / "sample.docx"


@pytest.fixture
def sample_chapter() -> NovelChapter:
    return NovelChapter(
        chapter_index=0,
        chapter_title="第一章 初入江湖",
        raw_text="江南三月，烟雨朦胧。青石小巷深处，一座老旧茶馆门前挂着一面褪色的酒旗。",
    )


@pytest.fixture
def sample_novel_text() -> NovelText:
    chapters = [
        NovelChapter(
            chapter_index=i,
            chapter_title=f"第{i + 1}章",
            raw_text=f"这是第{i + 1}章的测试内容。包含了足够的文本用于验证解析和分片逻辑。"
            * 10,
        )
        for i in range(3)
    ]
    return NovelText(title="测试小说", chapters=chapters)


@pytest.fixture
def sample_extracted_character() -> ExtractedCharacter:
    return ExtractedCharacter(
        name="张三",
        aliases=["三哥", "张兄"],
        role_hint="主角",
        description="年轻剑客，性格刚烈。",
        first_appearance_chapter=0,
    )


@pytest.fixture
def sample_scene_boundary() -> SceneBoundary:
    return SceneBoundary(
        scene_index=0,
        summary="酒楼初遇",
        location="悦来酒楼",
        time_hint="傍晚",
        characters_present=["张三", "李四"],
        start_paragraph=0,
        end_paragraph=3,
    )


@pytest.fixture
def sample_chapter_analysis() -> ChapterAnalysis:
    return ChapterAnalysis(
        chapter_index=0,
        characters=[
            ExtractedCharacter(
                name="张三",
                aliases=["三哥"],
                role_hint="主角",
                description="剑客",
                first_appearance_chapter=0,
            )
        ],
        scenes=[
            SceneBoundary(
                scene_index=0,
                summary="测试场景",
                location="某地",
                time_hint="日",
                characters_present=["张三"],
                start_paragraph=0,
                end_paragraph=5,
            )
        ],
        dialogues=[],
        props=[],
        locations=[],
    )


@pytest.fixture
def sample_consolidated_analysis() -> ConsolidatedAnalysis:
    return ConsolidatedAnalysis(
        characters=[
            ConsolidatedCharacter(
                id="CHAR_001",
                name="张三",
                aliases=["三哥"],
                role="protagonist",
                archetype="热血青年",
                description="年轻剑客",
                appears_in_chapters=[0, 1],
                related_props=[],
            )
        ],
        relationships=[
            CharacterRelationship(
                from_char="CHAR_001",
                to_char="CHAR_002",
                relation="师徒",
                description="师徒关系",
            )
        ],
        timeline=[
            TimelineScene(
                scene_id="S1",
                source_chapter=0,
                location="酒楼",
                time_hint="日",
                summary="初次相遇",
                characters=["CHAR_001", "CHAR_002"],
            )
        ],
        global_locations=["酒楼"],
        global_props=["长剑"],
    )


@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端，可配置返回内容。"""
    with patch("backend.app.services.llm.get_client") as mock_get_client:
        client = MagicMock()
        mock_get_client.return_value = client
        yield client


@pytest.fixture
def task_manager() -> TaskManager:
    return TaskManager()

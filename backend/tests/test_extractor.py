from unittest.mock import patch

import pytest

from backend.app.models.analysis import (
    ChapterAnalysis,
    DialogueEntry,
    ExtractedCharacter,
    SceneBoundary,
)
from backend.app.models.input import NovelChapter
from backend.app.services.dialogue_extractor import extract_dialogues
from backend.app.services.extractor import extract_characters
from backend.app.services.orchestrator import analyze_chapter
from backend.app.services.scene_detector import detect_scenes


def _make_char(name="张三") -> ExtractedCharacter:
    return ExtractedCharacter(
        name=name,
        aliases=["三哥"],
        role_hint="主角",
        description="年轻剑客",
        first_appearance_chapter=0,
    )


def _make_scene(index=0) -> SceneBoundary:
    return SceneBoundary(
        scene_index=index,
        summary="酒楼初遇",
        location="悦来酒楼",
        time_hint="傍晚",
        characters_present=["张三"],
        start_paragraph=0,
        end_paragraph=3,
    )


def _make_dialogue(index=0) -> DialogueEntry:
    return DialogueEntry(
        paragraph_index=index,
        speaker="张三",
        raw_text="\"来得正好！\"",
        cleaned_dialogue="来得正好！",
        stage_direction="张三大笑一声",
    )


# ── extract_characters ──────────────────────────────────────────


class TestExtractCharacters:
    def test_successful_extraction(self, sample_chapter):
        with patch("backend.app.services.extractor.structured_call") as mock_sc:
            mock_sc.return_value = [_make_char("张三"), _make_char("李四")]
            result = extract_characters(sample_chapter)
            assert len(result) == 2
            assert result[0].name == "张三"
            assert result[1].name == "李四"

    def test_empty_list(self, sample_chapter):
        with patch("backend.app.services.extractor.structured_call") as mock_sc:
            mock_sc.return_value = []
            result = extract_characters(sample_chapter)
            assert result == []

    def test_root_attribute_fallback(self, sample_chapter):
        class Wrapped:
            root = [_make_char("张三")]

        with patch("backend.app.services.extractor.structured_call") as mock_sc:
            mock_sc.return_value = Wrapped()
            result = extract_characters(sample_chapter)
            assert len(result) == 1
            assert result[0].name == "张三"

    def test_llm_failure_returns_empty(self, sample_chapter):
        with patch("backend.app.services.extractor.structured_call") as mock_sc:
            mock_sc.side_effect = RuntimeError("all retries exhausted")
            result = extract_characters(sample_chapter)
            assert isinstance(result, list)
            assert result == []

    def test_passes_chapter_info_to_llm(self, sample_chapter):
        with patch("backend.app.services.extractor.structured_call") as mock_sc:
            mock_sc.return_value = []
            extract_characters(sample_chapter)
            call_kwargs = mock_sc.call_args.kwargs
            assert call_kwargs["template_name"] == "extract_characters.j2"
            assert call_kwargs["variables"]["chapter_index"] == sample_chapter.chapter_index
            assert call_kwargs["variables"]["chapter_title"] == sample_chapter.chapter_title
            assert call_kwargs["variables"]["chapter_text"] == sample_chapter.raw_text


# ── detect_scenes ───────────────────────────────────────────────


class TestDetectScenes:
    def test_successful_detection(self, sample_chapter):
        with patch("backend.app.services.scene_detector.structured_call") as mock_sc:
            mock_sc.return_value = [_make_scene(0), _make_scene(1)]
            result = detect_scenes(sample_chapter)
            assert len(result) == 2
            assert result[0].summary == "酒楼初遇"

    def test_empty_list(self, sample_chapter):
        with patch("backend.app.services.scene_detector.structured_call") as mock_sc:
            mock_sc.return_value = []
            result = detect_scenes(sample_chapter)
            assert result == []

    def test_root_attribute_fallback(self, sample_chapter):
        class Wrapped:
            root = [_make_scene(0)]

        with patch("backend.app.services.scene_detector.structured_call") as mock_sc:
            mock_sc.return_value = Wrapped()
            result = detect_scenes(sample_chapter)
            assert len(result) == 1

    def test_llm_failure_returns_empty(self, sample_chapter):
        with patch("backend.app.services.scene_detector.structured_call") as mock_sc:
            mock_sc.side_effect = RuntimeError("all retries exhausted")
            result = detect_scenes(sample_chapter)
            assert result == []

    def test_passes_paragraph_numbers(self, sample_chapter):
        with patch("backend.app.services.scene_detector.structured_call") as mock_sc:
            mock_sc.return_value = []
            detect_scenes(sample_chapter)
            variables = mock_sc.call_args.kwargs["variables"]
            assert "paragraph_count" in variables
            assert variables["paragraph_count"] > 0
            assert "[0]" in variables["chapter_text_with_line_numbers"]


# ── extract_dialogues ───────────────────────────────────────────


class TestExtractDialogues:
    def test_successful_extraction(self, sample_chapter):
        with patch("backend.app.services.dialogue_extractor.structured_call") as mock_sc:
            mock_sc.return_value = [_make_dialogue(0), _make_dialogue(1)]
            result = extract_dialogues(sample_chapter)
            assert len(result) == 2
            assert result[0].speaker == "张三"

    def test_empty_list(self, sample_chapter):
        with patch("backend.app.services.dialogue_extractor.structured_call") as mock_sc:
            mock_sc.return_value = []
            result = extract_dialogues(sample_chapter)
            assert result == []

    def test_root_attribute_fallback(self, sample_chapter):
        class Wrapped:
            root = [_make_dialogue(0)]

        with patch("backend.app.services.dialogue_extractor.structured_call") as mock_sc:
            mock_sc.return_value = Wrapped()
            result = extract_dialogues(sample_chapter)
            assert len(result) == 1

    def test_llm_failure_returns_empty(self, sample_chapter):
        with patch("backend.app.services.dialogue_extractor.structured_call") as mock_sc:
            mock_sc.side_effect = RuntimeError("all retries exhausted")
            result = extract_dialogues(sample_chapter)
            assert result == []

    def test_passes_paragraph_numbers(self, sample_chapter):
        with patch("backend.app.services.dialogue_extractor.structured_call") as mock_sc:
            mock_sc.return_value = []
            extract_dialogues(sample_chapter)
            variables = mock_sc.call_args.kwargs["variables"]
            assert "chapter_text_with_line_numbers" in variables
            assert "[0]" in variables["chapter_text_with_line_numbers"]


# ── analyze_chapter ─────────────────────────────────────────────


class TestAnalyzeChapter:
    def test_successful_analysis(self, sample_chapter):
        with (
            patch("backend.app.services.orchestrator.extract_characters") as mock_chars,
            patch("backend.app.services.orchestrator.detect_scenes") as mock_scenes,
            patch("backend.app.services.orchestrator.extract_dialogues") as mock_diags,
        ):
            mock_chars.return_value = [_make_char("张三")]
            mock_scenes.return_value = [_make_scene(0)]
            mock_diags.return_value = [_make_dialogue(0)]

            result = analyze_chapter(sample_chapter)

            assert isinstance(result, ChapterAnalysis)
            assert result.chapter_index == sample_chapter.chapter_index
            assert len(result.characters) == 1
            assert len(result.scenes) == 1
            assert len(result.dialogues) == 1

    def test_partial_failure_characters(self, sample_chapter):
        with (
            patch("backend.app.services.orchestrator.extract_characters") as mock_chars,
            patch("backend.app.services.orchestrator.detect_scenes") as mock_scenes,
            patch("backend.app.services.orchestrator.extract_dialogues") as mock_diags,
        ):
            mock_chars.side_effect = RuntimeError("character extraction failed")
            mock_scenes.return_value = [_make_scene(0)]
            mock_diags.return_value = [_make_dialogue(0)]

            result = analyze_chapter(sample_chapter)

            assert len(result.characters) == 0
            assert len(result.scenes) == 1
            assert len(result.dialogues) == 1

    def test_partial_failure_scenes(self, sample_chapter):
        with (
            patch("backend.app.services.orchestrator.extract_characters") as mock_chars,
            patch("backend.app.services.orchestrator.detect_scenes") as mock_scenes,
            patch("backend.app.services.orchestrator.extract_dialogues") as mock_diags,
        ):
            mock_chars.return_value = [_make_char("张三")]
            mock_scenes.side_effect = RuntimeError("scene detection failed")
            mock_diags.return_value = [_make_dialogue(0)]

            result = analyze_chapter(sample_chapter)

            assert len(result.characters) == 1
            assert len(result.scenes) == 0
            assert len(result.dialogues) == 1

    def test_all_extractors_fail(self, sample_chapter):
        with (
            patch("backend.app.services.orchestrator.extract_characters") as mock_chars,
            patch("backend.app.services.orchestrator.detect_scenes") as mock_scenes,
            patch("backend.app.services.orchestrator.extract_dialogues") as mock_diags,
        ):
            mock_chars.side_effect = RuntimeError("fail")
            mock_scenes.side_effect = RuntimeError("fail")
            mock_diags.side_effect = RuntimeError("fail")

            result = analyze_chapter(sample_chapter)

            assert result.characters == []
            assert result.scenes == []
            assert result.dialogues == []
            assert result.chapter_index == sample_chapter.chapter_index

    def test_locations_from_scenes(self, sample_chapter):
        with (
            patch("backend.app.services.orchestrator.extract_characters") as mock_chars,
            patch("backend.app.services.orchestrator.detect_scenes") as mock_scenes,
            patch("backend.app.services.orchestrator.extract_dialogues") as mock_diags,
        ):
            mock_chars.return_value = []
            mock_scenes.return_value = [
                SceneBoundary(
                    scene_index=0,
                    summary="s1",
                    location="酒楼",
                    time_hint="日",
                    characters_present=[],
                    start_paragraph=0,
                    end_paragraph=2,
                ),
                SceneBoundary(
                    scene_index=1,
                    summary="s2",
                    location="酒楼",  # duplicate
                    time_hint="夜",
                    characters_present=[],
                    start_paragraph=3,
                    end_paragraph=5,
                ),
                SceneBoundary(
                    scene_index=2,
                    summary="s3",
                    location="未知",  # filtered out
                    time_hint="日",
                    characters_present=[],
                    start_paragraph=6,
                    end_paragraph=8,
                ),
            ]
            mock_diags.return_value = []

            result = analyze_chapter(sample_chapter)
            assert result.locations == ["酒楼"]  # deduplicated, "未知" filtered

from unittest.mock import patch

from app.models.analysis import ChapterAnalysis, ExtractedCharacter, SceneBoundary
from app.models.consolidated import (
    CharacterRelationship,
    ConsolidatedAnalysis,
    ConsolidatedCharacter,
    TimelineScene,
)
from app.services.consolidate import (
    _serialize_characters,
    _serialize_scenes,
    merge_and_consolidate,
)
from app.services.relationship_timeline import (
    build_relationship_graph,
    process_consolidated,
    sort_timeline,
    validate_consolidated,
)


def _make_analysis(chapter_index=0) -> ChapterAnalysis:
    return ChapterAnalysis(
        chapter_index=chapter_index,
        characters=[
            ExtractedCharacter(
                name="张三",
                aliases=["三哥"],
                role_hint="主角",
                description="剑客",
                first_appearance_chapter=chapter_index,
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
        locations=["某地"],
    )


def _make_consolidated() -> ConsolidatedAnalysis:
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
            ),
            ConsolidatedCharacter(
                id="CHAR_002",
                name="李四",
                aliases=[],
                role="supporting",
                archetype="导师",
                description="老剑客",
                appears_in_chapters=[0],
            ),
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
                scene_id="SCENE_001",
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


# ── merge_and_consolidate ───────────────────────────────────────


class TestMergeAndConsolidate:
    def test_successful_consolidation(self):
        analyses = [_make_analysis(0), _make_analysis(1)]
        expected = _make_consolidated()

        with patch("backend.app.services.consolidate.structured_call") as mock_sc:
            mock_sc.return_value = expected
            result = merge_and_consolidate(analyses)
            assert result == expected

    def test_empty_analyses(self):
        result = merge_and_consolidate([])
        assert isinstance(result, ConsolidatedAnalysis)
        assert result.characters == []
        assert result.relationships == []
        assert result.timeline == []

    def test_llm_failure_returns_empty(self):
        with patch("backend.app.services.consolidate.structured_call") as mock_sc:
            mock_sc.side_effect = RuntimeError("all retries exhausted")
            result = merge_and_consolidate([_make_analysis(0)])
            assert isinstance(result, ConsolidatedAnalysis)
            assert result.characters == []

    def test_passes_serialized_data(self):
        analyses = [_make_analysis(0)]

        with patch("backend.app.services.consolidate.structured_call") as mock_sc:
            mock_sc.return_value = _make_consolidated()
            merge_and_consolidate(analyses)

            variables = mock_sc.call_args.kwargs["variables"]
            assert "characters_json" in variables
            assert "scenes_json" in variables
            assert "张三" in variables["characters_json"]


# ── _serialize_characters ───────────────────────────────────────


class TestSerializeCharacters:
    def test_includes_all_fields(self):
        result = _serialize_characters([_make_analysis(0)])
        assert "张三" in result
        assert "三哥" in result
        assert "chapter_index" in result
        assert "first_appearance_chapter" in result

    def test_empty_analyses(self):
        result = _serialize_characters([])
        assert result == "[]"


# ── _serialize_scenes ───────────────────────────────────────────


class TestSerializeScenes:
    def test_includes_all_fields(self):
        result = _serialize_scenes([_make_analysis(0)])
        assert "测试场景" in result
        assert "某地" in result
        assert "chapter_index" in result

    def test_empty_analyses(self):
        result = _serialize_scenes([])
        assert result == "[]"


# ── build_relationship_graph ────────────────────────────────────


class TestBuildRelationshipGraph:
    def test_bidirectional_edges(self):
        consolidated = ConsolidatedAnalysis(
            relationships=[
                CharacterRelationship(
                    from_char="A", to_char="B", relation="师徒", description="test"
                )
            ]
        )
        graph = build_relationship_graph(consolidated)
        assert "A" in graph
        assert "B" in graph
        assert graph["A"][0]["to"] == "B"
        assert graph["A"][0]["relation"] == "师徒"
        # reverse edge
        assert graph["B"][0]["to"] == "A"

    def test_empty_relationships(self):
        graph = build_relationship_graph(ConsolidatedAnalysis())
        assert graph == {}

    def test_multiple_relations(self):
        consolidated = ConsolidatedAnalysis(
            relationships=[
                CharacterRelationship(from_char="A", to_char="B", relation="师徒", description=""),
                CharacterRelationship(from_char="A", to_char="C", relation="敌对", description=""),
            ]
        )
        graph = build_relationship_graph(consolidated)
        assert len(graph["A"]) == 2
        assert len(graph["B"]) == 1
        assert len(graph["C"]) == 1


# ── sort_timeline ───────────────────────────────────────────────


class TestSortTimeline:
    def test_sorts_by_chapter_then_scene_id(self):
        timeline = [
            TimelineScene(scene_id="SCENE_003", source_chapter=0, summary=""),
            TimelineScene(scene_id="SCENE_001", source_chapter=1, summary=""),
            TimelineScene(scene_id="SCENE_002", source_chapter=0, summary=""),
        ]
        sorted_scenes = sort_timeline(timeline)
        ids = [s.scene_id for s in sorted_scenes]
        assert ids == ["SCENE_002", "SCENE_003", "SCENE_001"]

    def test_empty_timeline(self):
        result = sort_timeline([])
        assert result == []


# ── validate_consolidated ───────────────────────────────────────


class TestValidateConsolidated:
    def test_fixture_detects_missing_references(self, sample_consolidated_analysis):
        # Fixture has CHAR_002 referenced in relationship/timeline but not in characters
        issues = validate_consolidated(sample_consolidated_analysis)
        assert len(issues) == 2
        assert any("CHAR_002" in issue for issue in issues)

    def test_missing_character_in_relationship(self):
        consolidated = ConsolidatedAnalysis(
            characters=[
                ConsolidatedCharacter(id="A", name="甲"),
            ],
            relationships=[
                CharacterRelationship(from_char="A", to_char="B", relation="师徒"),
            ],
        )
        issues = validate_consolidated(consolidated)
        assert len(issues) >= 1
        assert any("B" in issue for issue in issues)

    def test_missing_character_in_timeline(self):
        consolidated = ConsolidatedAnalysis(
            characters=[
                ConsolidatedCharacter(id="A", name="甲"),
            ],
            timeline=[
                TimelineScene(scene_id="S1", source_chapter=0, characters=["A", "B"]),
            ],
        )
        issues = validate_consolidated(consolidated)
        assert len(issues) >= 1
        assert any("B" in issue for issue in issues)

    def test_all_characters_valid(self):
        consolidated = ConsolidatedAnalysis(
            characters=[
                ConsolidatedCharacter(id="A", name="甲"),
                ConsolidatedCharacter(id="B", name="乙"),
            ],
            relationships=[
                CharacterRelationship(from_char="A", to_char="B", relation="师徒"),
            ],
            timeline=[
                TimelineScene(scene_id="S1", source_chapter=0, characters=["A", "B"]),
            ],
        )
        issues = validate_consolidated(consolidated)
        assert issues == []

    def test_both_relationship_and_timeline_issues(self):
        consolidated = ConsolidatedAnalysis(
            characters=[
                ConsolidatedCharacter(id="A", name="甲"),
            ],
            relationships=[
                CharacterRelationship(from_char="X", to_char="Y", relation="师徒"),
            ],
            timeline=[
                TimelineScene(scene_id="S1", source_chapter=0, characters=["Z"]),
            ],
        )
        issues = validate_consolidated(consolidated)
        assert len(issues) == 3  # X, Y from relationship, Z from timeline


# ── process_consolidated ────────────────────────────────────────


class TestProcessConsolidated:
    def test_sorts_timeline(self):
        consolidated = ConsolidatedAnalysis(
            timeline=[
                TimelineScene(scene_id="SCENE_003", source_chapter=0, summary=""),
                TimelineScene(scene_id="SCENE_001", source_chapter=0, summary=""),
            ]
        )
        result = process_consolidated(consolidated)
        ids = [s.scene_id for s in result.timeline]
        assert ids == ["SCENE_001", "SCENE_003"]

    def test_returns_same_object(self):
        consolidated = _make_consolidated()
        result = process_consolidated(consolidated)
        assert result is consolidated

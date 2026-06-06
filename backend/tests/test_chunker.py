from backend.app.models.input import NovelChapter
from backend.app.services.chunker import (
    estimate_tokens,
    normalize_paragraphs,
    normalize_text,
    split_long_chapter,
    update_chapter_stats,
)


class TestNormalizeText:
    def test_merges_multiple_blank_lines(self):
        text = "第一段\n\n\n\n第二段"
        result = normalize_text(text)
        assert result == "第一段\n\n第二段"

    def test_strips_surrounding_whitespace(self):
        text = "  \n  内容  \n  "
        result = normalize_text(text)
        assert result == "内容"

    def test_unifies_line_endings(self):
        text = "第一行\r\n第二行\r第三行"
        result = normalize_text(text)
        assert "\r" not in result
        assert "\r\n" not in result

    def test_preserves_single_newlines(self):
        text = "行一\n行二\n行三"
        result = normalize_text(text)
        assert result == "行一\n行二\n行三"


class TestNormalizeParagraphs:
    def test_splits_by_newlines(self):
        text = "段落一\n\n段落二\n段落三"
        result = normalize_paragraphs(text)
        assert len(result) >= 2
        assert "段落一" in result

    def test_filters_empty_lines(self):
        text = "\n\n段落一\n\n\n段落二\n\n"
        result = normalize_paragraphs(text)
        assert all(p.strip() for p in result)
        assert len(result) == 2

    def test_strips_paragraph_whitespace(self):
        text = "  段落一  \n\n  段落二  "
        result = normalize_paragraphs(text)
        assert result[0] == "段落一"
        assert result[1] == "段落二"


class TestEstimateTokens:
    def test_chinese_text(self):
        tokens = estimate_tokens("这是一段中文测试文本")
        assert tokens > 0
        assert tokens == int(10 * 1.5)  # 10 Chinese chars

    def test_english_text(self):
        tokens = estimate_tokens("Hello World")
        # 10 non-CJK chars × 1.3 ≈ 13
        assert 10 < tokens < 20

    def test_empty_text(self):
        assert estimate_tokens("") == 0

    def test_mixed_text(self):
        tokens = estimate_tokens("中文English混合")
        # 4 CJK * 1.5 + 7 non-CJK * 1.3 = 6 + 9 = 15
        expected = int(4 * 1.5 + 7 * 1.3)
        assert tokens == expected


class TestUpdateChapterStats:
    def test_fills_paragraph_count(self):
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="测试",
            raw_text="段落一\n\n段落二\n\n段落三",
        )
        update_chapter_stats(ch)
        assert ch.paragraph_count == 3

    def test_fills_token_estimate(self):
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="测试",
            raw_text="这是一段测试文本用于验证",
        )
        update_chapter_stats(ch)
        assert ch.token_estimate > 0

    def test_empty_chapter(self):
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="空章",
            raw_text=" ",
        )
        update_chapter_stats(ch)
        assert ch.paragraph_count == 0
        assert ch.token_estimate == 0


class TestSplitLongChapter:
    def test_short_chapter_not_split(self):
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="短章",
            raw_text="只有一段内容的短章节。",
        )
        update_chapter_stats(ch)
        subs, summary = split_long_chapter(ch, max_tokens=15000)
        assert len(subs) == 1
        assert summary.sub_chapter_count == 1
        assert subs[0].chapter_index == ch.chapter_index

    def test_long_chapter_splits(self):
        para = "这是一个测试段落包含足够多的中文字符以达到一定的token数量要求。" * 35
        raw = "\n\n".join([para] * 10)
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="超长章",
            raw_text=raw,
        )
        update_chapter_stats(ch)
        assert ch.token_estimate > 15000, f"token_estimate={ch.token_estimate}"

        subs, summary = split_long_chapter(ch, max_tokens=6000)
        assert len(subs) > 1, f"subs count={len(subs)}"
        assert summary.sub_chapter_count == len(subs)

    def test_preserves_paragraph_boundaries(self):
        # Build a long chapter with known paragraph structure
        para = "这是一个测试段落包含足够多的中文字符以达到一定的token数量。" * 20
        raw = "\n\n".join([para] * 20)
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="长章",
            raw_text=raw,
        )
        update_chapter_stats(ch)
        subs, _ = split_long_chapter(ch, max_tokens=2000)

        # Each sub-chapter should have complete paragraphs
        for sub in subs:
            # Re-join split paragraphs and check they match original paragraphs
            sub_paras = normalize_paragraphs(sub.raw_text)
            for sp in sub_paras:
                assert sp == para

    def test_empty_chapter_no_split(self):
        ch = NovelChapter(
            chapter_index=0,
            chapter_title="空",
            raw_text=" ",
        )
        update_chapter_stats(ch)
        subs, summary = split_long_chapter(ch, max_tokens=15000)
        # Empty paragraph content → no paragraphs to batch → returned as-is
        assert len(subs) == 1
        assert summary.sub_chapter_count == 1

    def test_sub_chapter_retains_original_index(self):
        para = "这是一个测试段落包含足够多的中文字符。" * 30
        raw = "\n\n".join([para] * 15)
        ch = NovelChapter(
            chapter_index=5,
            chapter_title="第五章",
            raw_text=raw,
        )
        update_chapter_stats(ch)
        subs, _ = split_long_chapter(ch, max_tokens=5000)

        assert len(subs) > 1
        for i, sub in enumerate(subs):
            assert sub.chapter_index // 1000 == 5
            assert "第五章" in sub.chapter_title

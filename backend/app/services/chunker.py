import re
from dataclasses import dataclass, field

from backend.app.models.input import NovelChapter


def normalize_text(text: str) -> str:
    """段落归一化：多余空行合并、首尾空白去除。"""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 合并连续空行（3 个及以上换行 → 2 个换行）
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除首尾空白
    text = text.strip()
    return text


def normalize_paragraphs(text: str) -> list[str]:
    """将文本按段落分割并逐一归一化，过滤空段落。"""
    text = normalize_text(text)
    paragraphs = text.split("\n")
    result = [p.strip() for p in paragraphs if p.strip()]
    return result


def estimate_tokens(text: str) -> int:
    """Token 数量粗略估算。

    中文按字符数 × 1.5 估算（中文每个字约为 1-2 个 token）。
    英文按字符数 × 1.3 估算。
    """
    # 统计中文字符
    cjk_chars = sum(
        1 for ch in text
        if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"
    )
    # 统计非中文/非空白字符（粗略作为英文部分）
    non_cjk = sum(
        1 for ch in text
        if ch not in (" ", "\n", "\t")
        and not ("一" <= ch <= "鿿")
        and not ("㐀" <= ch <= "䶿")
    )

    return int(cjk_chars * 1.5 + non_cjk * 1.3)


def update_chapter_stats(chapter: NovelChapter) -> None:
    """根据章节文本补充 paragraph_count 和 token_estimate 字段。"""
    paragraphs = normalize_paragraphs(chapter.raw_text)
    chapter.paragraph_count = len(paragraphs)
    chapter.token_estimate = estimate_tokens(chapter.raw_text)


@dataclass
class ChunkSummary:
    """分片摘要记录：记录原章到子章的映射关系。"""
    original_chapter_index: int
    original_chapter_title: str
    sub_chapter_count: int
    sub_chapter_indices: list[int] = field(default_factory=list)


def split_long_chapter(
    chapter: NovelChapter,
    max_tokens: int = 15000,
) -> tuple[list[NovelChapter], ChunkSummary]:
    """将超长章节按段落边界切分为多个子章。

    仅在 chapter.token_estimate > max_tokens 时执行分片。
    保证不在段落中间切断。

    Returns:
        (sub_chapters, summary): 子章列表和分片摘要。
        如果不需要分片，返回原章单元素列表。
    """
    if chapter.token_estimate <= max_tokens:
        summary = ChunkSummary(
            original_chapter_index=chapter.chapter_index,
            original_chapter_title=chapter.chapter_title,
            sub_chapter_count=1,
            sub_chapter_indices=[chapter.chapter_index],
        )
        return [chapter], summary

    paragraphs = normalize_paragraphs(chapter.raw_text)
    if not paragraphs:
        summary = ChunkSummary(
            original_chapter_index=chapter.chapter_index,
            original_chapter_title=chapter.chapter_title,
            sub_chapter_count=0,
        )
        return [], summary

    sub_chapters = []
    current_batch = []
    current_tokens = 0
    sub_index = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > max_tokens and current_batch:
            # 当前批次已满，写入子章
            sub_chapters.append(_build_sub_chapter(chapter, sub_index, current_batch))
            sub_index += 1
            current_batch = []
            current_tokens = 0

        current_batch.append(para)
        current_tokens += para_tokens

    # 处理最后一批
    if current_batch:
        sub_chapters.append(_build_sub_chapter(chapter, sub_index, current_batch))
        sub_index += 1

    summary = ChunkSummary(
        original_chapter_index=chapter.chapter_index,
        original_chapter_title=chapter.chapter_title,
        sub_chapter_count=len(sub_chapters),
        sub_chapter_indices=[chapter.chapter_index * 1000 + i for i in range(len(sub_chapters))],
    )

    return sub_chapters, summary


def _build_sub_chapter(
    original: NovelChapter,
    sub_index: int,
    paragraphs: list[str],
) -> NovelChapter:
    """构建子章实例，保留原始章节索引并附加子序号标记。"""
    raw_text = "\n".join(paragraphs)
    sub = NovelChapter(
        chapter_index=original.chapter_index * 1000 + sub_index,
        chapter_title=f"{original.chapter_title}（第{sub_index + 1}部分）",
        raw_text=raw_text,
    )
    update_chapter_stats(sub)
    return sub

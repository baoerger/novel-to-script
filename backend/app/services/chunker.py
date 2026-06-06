import re

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

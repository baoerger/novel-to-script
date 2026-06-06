import re
from pathlib import Path

from backend.app.models.input import NovelChapter, NovelText


# 章节标题正则：匹配 "第X章" 格式（支持中文数字、阿拉伯数字）
_CHAPTER_PATTERN = re.compile(
    r"^\s*第[零一二三四五六七八九十百千万\d]+章\s*.*$",
    re.MULTILINE,
)


def parse_txt(file_path: str) -> NovelText:
    """从 .txt 文件中识别章节边界并分割为 NovelText。

    正则匹配以 "第X章" 开头的行作为章节边界。
    降级策略：匹配到的章节标题数 ≥3 时采用正则结果，否则全文作为单章。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.suffix.lower() not in (".txt", ".text"):
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 .txt")

    title = _infer_title(path)
    raw_text = path.read_text(encoding="utf-8")

    # 查找所有章节标题匹配位置
    matches = list(_CHAPTER_PATTERN.finditer(raw_text))

    if len(matches) >= 3:
        chapters = _split_by_matches(raw_text, matches)
    else:
        # 降级：全文作为单章
        chapters = [
            NovelChapter(
                chapter_index=0,
                chapter_title="全文",
                raw_text=raw_text.strip(),
            )
        ]

    return NovelText(title=title, chapters=chapters)


def _infer_title(path: Path) -> str:
    """从文件名推断书名（去除扩展名）。"""
    return path.stem


def _split_by_matches(text: str, matches: list[re.Match]) -> list[NovelChapter]:
    """根据章节标题匹配位置分割正文为 NovelChapter 列表。"""
    chapters = []

    for i, match in enumerate(matches):
        chapter_title = match.group().strip()
        start = match.end() + 1  # 跳过标题行
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        raw_text = text[start:end].strip()

        chapters.append(
            NovelChapter(
                chapter_index=i,
                chapter_title=chapter_title,
                raw_text=raw_text,
            )
        )

    return chapters

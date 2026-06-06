import re
from pathlib import Path

from docx import Document

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


def parse_docx(file_path: str) -> NovelText:
    """从 .docx 文件中提取章节文本为 NovelText。

    优先使用 Word 标题样式识别章节边界，降级时回退到正则匹配。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.suffix.lower() != ".docx":
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 .docx")

    title = _infer_title(path)
    doc = Document(file_path)

    # 提取所有段落文本及样式信息
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        is_heading = para.style.name.startswith("Heading") if para.style else False
        paragraphs.append((text, is_heading))

    if not paragraphs:
        return NovelText(title=title, chapters=[])

    # 尝试用 Word 标题样式识别章节
    heading_indices = [i for i, (_, is_h) in enumerate(paragraphs) if is_h]

    if len(heading_indices) >= 3:
        chapters = _build_chapters_from_indices(paragraphs, heading_indices)
    else:
        # 降级：用正则匹配查找章节标题
        full_text = "\n".join(t for t, _ in paragraphs)
        matches = list(_CHAPTER_PATTERN.finditer(full_text))

        if len(matches) >= 3:
            chapters = _split_by_matches(full_text, matches)
        else:
            chapters = [
                NovelChapter(
                    chapter_index=0,
                    chapter_title="全文",
                    raw_text=full_text.strip(),
                )
            ]

    return NovelText(title=title, chapters=chapters)


def _build_chapters_from_indices(
    paragraphs: list[tuple[str, bool]], heading_indices: list[int]
) -> list[NovelChapter]:
    """根据标题样式索引构建 NovelChapter 列表。"""
    chapters = []

    for i, idx in enumerate(heading_indices):
        chapter_title = paragraphs[idx][0]
        start = idx + 1
        end = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(paragraphs)
        raw_text = "\n".join(t for t, _ in paragraphs[start:end]).strip()

        chapters.append(
            NovelChapter(
                chapter_index=i,
                chapter_title=chapter_title,
                raw_text=raw_text,
            )
        )

    return chapters


def parse_file(file_path: str) -> NovelText:
    """统一的文件解析入口，根据扩展名分发到对应的解析器。

    支持格式: .txt, .text, .docx
    """
    suffix = Path(file_path).suffix.lower()
    if suffix in (".txt", ".text"):
        return parse_txt(file_path)
    elif suffix == ".docx":
        return parse_docx(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，支持: .txt, .docx")

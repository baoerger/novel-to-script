import re
from pathlib import Path

from docx import Document

from backend.app.models.input import NovelChapter, NovelText


# ═══════════════════════════════════════════════════════════════
# 章节标题正则 — 按优先级分为三级
# ═══════════════════════════════════════════════════════════════

# 中文数字字符集
_CN_NUM = "零一二三四五六七八九十百千万"
_CN_DIGIT = f"[{_CN_NUM}\\d]"

# ── Tier 1: 标准章节格式 ──
_TIER1_PATTERNS = [
    # 第X章 / 第X回 / 第X节 / 第X集 / 第X卷 / 第X部 / 第X篇
    re.compile(
        rf"^\s*第{_CN_DIGIT}+[章节回集卷部篇]\s*.*$",
        re.MULTILINE,
    ),
    # 【第X章】 / ［第X回］ 等括号包裹
    re.compile(
        rf"^\s*[【［\[]\s*第{_CN_DIGIT}+[章节回集卷部篇][^】］\]]*[】］\]]",
        re.MULTILINE,
    ),
    # Chapter X（英文）
    re.compile(
        r"^\s*Chapter\s+\d+.*$",
        re.MULTILINE | re.IGNORECASE,
    ),
]

# ── Tier 2: 宽泛格式 ──
_TIER2_PATTERNS = [
    # 纯数字开头短行（如 "123 某某标题"），限制长度避免误匹配正文行
    re.compile(
        r"^\s*\d{1,4}\s{1,3}\S.{0,40}$",
        re.MULTILINE,
    ),
    # X章 / X回 省略"第"字（如 "一、某某" 或 "十二 标题"）
    re.compile(
        rf"^\s*{_CN_DIGIT}{{1,4}}\s*[章节回集卷部篇].*$",
        re.MULTILINE,
    ),
    # 特殊符号分隔行：*** 章节标题 *** / --- 章节标题 --- 等
    re.compile(
        r"^\s*[*\-=]{2,}\s*.{1,40}\s*[*\-=]{2,}\s*$",
        re.MULTILINE,
    ),
]

# 编译所有正则到一个列表中（按优先级排序）
_ALL_PATTERNS = _TIER1_PATTERNS + _TIER2_PATTERNS

# 最小匹配数阈值
_MIN_MATCHES = 3

# 中文 TXT 文件常见编码，按优先级降序尝试
_TXT_ENCODINGS = ("utf-8", "gbk", "gb18030", "utf-8-sig", "latin-1")


# ═══════════════════════════════════════════════════════════════
# 编码处理
# ═══════════════════════════════════════════════════════════════

def _read_text_with_fallback(file_path: Path) -> str:
    """依次尝试多种编码读取文件，成功时返回内容。

    编码尝试顺序: UTF-8 → GBK → GB18030 → UTF-8-SIG → Latin-1（兜底）
    Latin-1 永远不会抛出解码错误，作为最终兜底。
    """
    for encoding in _TXT_ENCODINGS:
        try:
            return file_path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return file_path.read_text(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════
# 三级章节检测
# ═══════════════════════════════════════════════════════════════

def _try_regex_tiers(raw_text: str) -> list[re.Match] | None:
    """Tier 1 + Tier 2: 逐级尝试正则匹配。

    返回匹配列表（≥3 个时），全部失败返回 None。
    """
    for pattern in _ALL_PATTERNS:
        matches = list(pattern.finditer(raw_text))
        if len(matches) >= _MIN_MATCHES:
            return matches
    return None


def _try_texttiling(raw_text: str) -> list[tuple[int, int, str]] | None:
    """Tier 3: 基于字符 bigram 相似度的语义分割。

    将文本分成 ~500 字符的块，计算相邻块间的 bigram Jaccard 相似度。
    相似度骤降处（低于均值 - 0.5*标准差）标记为章节边界。

    返回 [(start_pos, end_pos, label), ...] 或 None。
    """
    if len(raw_text) < 3000:
        return None  # 文本太短无需分割

    block_size = 500
    blocks: list[str] = []
    pos = 0
    while pos < len(raw_text):
        end = min(pos + block_size, len(raw_text))
        # 尽量在换行处切断
        if end < len(raw_text):
            nl = raw_text.rfind("\n", pos, end)
            if nl > pos + block_size // 2:
                end = nl + 1
        blocks.append(raw_text[pos:end])
        pos = end

    if len(blocks) < 3:
        return None

    # 计算每块的 bigram 集合
    bigram_sets: list[set[str]] = []
    for block in blocks:
        bigrams = set()
        for i in range(len(block) - 1):
            bigrams.add(block[i : i + 2])
        bigram_sets.append(bigrams)

    # 计算相邻块间的 Jaccard 相似度
    similarities: list[float] = []
    for i in range(len(bigram_sets) - 1):
        a, b = bigram_sets[i], bigram_sets[i + 1]
        intersection = len(a & b)
        union = len(a | b)
        sim = intersection / union if union > 0 else 0.0
        similarities.append(sim)

    if not similarities:
        return None

    # 计算均值与标准差
    mean_sim = sum(similarities) / len(similarities)
    if len(similarities) < 2:
        return None
    variance = sum((s - mean_sim) ** 2 for s in similarities) / (len(similarities) - 1)
    stdev = variance ** 0.5

    # 相似度 < 均值 - 0.5*标准差 的位置标记为章节边界
    threshold = mean_sim - 0.5 * stdev
    boundaries: list[tuple[int, int, str]] = []

    start_pos = 0
    for i in range(len(blocks)):
        if i > 0 and similarities[i - 1] < threshold:
            # i-1 和 i 块之间相似度低 → 章节边界
            boundary_pos = start_pos
            boundaries.append((boundary_pos, i, f"第{len(boundaries) + 1}段"))
            start_pos = sum(len(b) for b in blocks[:i])
        if i == len(blocks) - 1:
            # 最后一段
            boundaries.append((start_pos, len(raw_text), f"第{len(boundaries) + 1}段"))

    if len(boundaries) < _MIN_MATCHES:
        return None

    return boundaries


# ═══════════════════════════════════════════════════════════════
# 解析入口
# ═══════════════════════════════════════════════════════════════

def parse_txt(file_path: str) -> NovelText:
    """从 .txt 文件中识别章节边界并分割为 NovelText。

    三级降级策略：
    1. Tier 1 — 标准正则（第X章/回/节/集/卷/部/篇 + bracket + Chapter）
    2. Tier 2 — 宽泛正则（纯数字短行 + 省略"第"字 + 符号分隔行）
    3. Tier 3 — 语义分割（基于 bigram 相似度骤降点检测）
    4. 兜底   — 全文作为单章

    自动探测文件编码（UTF-8/GBK/GB18030）。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.suffix.lower() not in (".txt", ".text"):
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 .txt")

    title = _infer_title(path)
    raw_text = _read_text_with_fallback(path)

    # Tier 1 + 2: 正则匹配
    matches = _try_regex_tiers(raw_text)
    if matches is not None:
        chapters = _split_by_matches(raw_text, matches)
        return NovelText(title=title, chapters=chapters)

    # Tier 3: 语义分割
    boundaries = _try_texttiling(raw_text)
    if boundaries is not None:
        chapters = _split_by_boundaries(raw_text, boundaries)
        return NovelText(title=title, chapters=chapters)

    # 兜底：全文作为单章
    chapters = [
        NovelChapter(
            chapter_index=0,
            chapter_title="全文",
            raw_text=raw_text.strip(),
        )
    ]
    return NovelText(title=title, chapters=chapters)


def parse_docx(file_path: str) -> NovelText:
    """从 .docx 文件中提取章节文本为 NovelText。

    优先使用 Word 标题样式识别章节边界，降级时回退到三级检测。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if path.suffix.lower() != ".docx":
        raise ValueError(f"不支持的文件格式: {path.suffix}，仅支持 .docx")

    title = _infer_title(path)
    doc = Document(file_path)

    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        is_heading = para.style.name.startswith("Heading") if para.style else False
        paragraphs.append((text, is_heading))

    if not paragraphs:
        return NovelText(title=title, chapters=[])

    # 优先：Word 标题样式
    heading_indices = [i for i, (_, is_h) in enumerate(paragraphs) if is_h]

    if len(heading_indices) >= _MIN_MATCHES:
        chapters = _build_chapters_from_indices(paragraphs, heading_indices)
        return NovelText(title=title, chapters=chapters)

    # 降级：对纯文本执行三级检测
    full_text = "\n".join(t for t, _ in paragraphs)
    return _parse_flat_text(title, full_text)


def _parse_flat_text(title: str, full_text: str) -> NovelText:
    """对无结构的纯文本执行三级章节检测。"""
    matches = _try_regex_tiers(full_text)
    if matches is not None:
        chapters = _split_by_matches(full_text, matches)
        return NovelText(title=title, chapters=chapters)

    boundaries = _try_texttiling(full_text)
    if boundaries is not None:
        chapters = _split_by_boundaries(full_text, boundaries)
        return NovelText(title=title, chapters=chapters)

    chapters = [
        NovelChapter(
            chapter_index=0,
            chapter_title="全文",
            raw_text=full_text.strip(),
        )
    ]
    return NovelText(title=title, chapters=chapters)


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════

def _infer_title(path: Path) -> str:
    """从文件名推断书名（去除扩展名）。"""
    return path.stem


def _split_by_matches(text: str, matches: list[re.Match]) -> list[NovelChapter]:
    """根据正则匹配位置分割正文为 NovelChapter 列表。"""
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


def _split_by_boundaries(
    text: str, boundaries: list[tuple[int, int, str]]
) -> list[NovelChapter]:
    """根据字节边界列表分割正文为 NovelChapter 列表。"""
    chapters = []
    for i, (start, end, label) in enumerate(boundaries):
        raw_text = text[start:end].strip()
        if not raw_text:
            continue
        chapters.append(
            NovelChapter(
                chapter_index=i,
                chapter_title=label,
                raw_text=raw_text,
            )
        )
    return chapters


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
    三级章节检测: 标准正则 → 宽泛正则 → 语义分割 → 全文单章兜底
    """
    suffix = Path(file_path).suffix.lower()
    if suffix in (".txt", ".text"):
        return parse_txt(file_path)
    elif suffix == ".docx":
        return parse_docx(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}，支持: .txt, .docx")

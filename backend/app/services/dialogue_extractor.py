import logging

from backend.app.models.input import NovelChapter
from backend.app.models.analysis import DialogueEntry
from backend.app.services.llm import structured_call

logger = logging.getLogger(__name__)


def extract_dialogues(chapter: NovelChapter) -> list[DialogueEntry]:
    """从单章文本中提取对白条目。

    使用 extract_dialogues.j2 模板，通过 LLM 结构化输出。
    将原文按段落编号后提交 LLM 识别对白及其归属。
    失败时记录错误并返回空列表（不阻塞流程）。
    """
    paragraphs = _split_paragraphs(chapter.raw_text)
    lines = [f"[{i}] {p}" for i, p in enumerate(paragraphs)]
    text_with_numbers = "\n".join(lines)

    variables = {
        "chapter_index": chapter.chapter_index,
        "chapter_title": chapter.chapter_title,
        "chapter_text_with_line_numbers": text_with_numbers,
    }

    try:
        result = structured_call(
            template_name="extract_dialogues.j2",
            variables=variables,
            output_model=list[DialogueEntry],
        )
        if isinstance(result, list):
            return result
        return list(result.root) if hasattr(result, "root") else []
    except Exception as e:
        logger.error(
            "对白提取失败 [第%d章 %s]: %s",
            chapter.chapter_index,
            chapter.chapter_title,
            e,
        )
        return []


def _split_paragraphs(text: str) -> list[str]:
    """将文本按空行分割为段落列表，过滤空段落。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]

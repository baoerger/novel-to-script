import logging

from backend.app.models.input import NovelChapter
from backend.app.models.analysis import ExtractedCharacter
from backend.app.services.llm import structured_call

logger = logging.getLogger(__name__)


def extract_characters(chapter: NovelChapter) -> list[ExtractedCharacter]:
    """从单章文本中提取角色信息。

    使用 extract_characters.j2 模板，通过 LLM 结构化输出。
    失败时记录错误并返回空列表（不阻塞流程）。
    """
    variables = {
        "chapter_index": chapter.chapter_index,
        "chapter_title": chapter.chapter_title,
        "chapter_text": chapter.raw_text,
    }

    try:
        result = structured_call(
            template_name="extract_characters.j2",
            variables=variables,
            output_model=list[ExtractedCharacter],
        )
        if isinstance(result, list):
            return result
        return list(result.root) if hasattr(result, "root") else []
    except Exception as e:
        logger.error(
            "角色提取失败 [第%d章 %s]: %s",
            chapter.chapter_index,
            chapter.chapter_title,
            e,
        )
        return []

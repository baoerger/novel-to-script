import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.input import NovelChapter
from app.models.analysis import ChapterAnalysis
from app.services.extractor import extract_characters
from app.services.scene_detector import detect_scenes
from app.services.dialogue_extractor import extract_dialogues

logger = logging.getLogger(__name__)


def analyze_chapter(chapter: NovelChapter) -> ChapterAnalysis:
    """对单章执行完整分析：并行提取角色、场景、对白，聚合为 ChapterAnalysis。

    三个提取器并行执行，各自失败不影响整体（返回空列表）。
    """
    results: dict[str, list] = {
        "characters": [],
        "scenes": [],
        "dialogues": [],
    }

    tasks = {
        "characters": extract_characters,
        "scenes": detect_scenes,
        "dialogues": extract_dialogues,
    }

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(fn, chapter): key
            for key, fn in tasks.items()
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                logger.error(
                    "提取器 %s 失败 [第%d章 %s]: %s",
                    key, chapter.chapter_index, chapter.chapter_title, e,
                )

    locations = list(dict.fromkeys(
        s.location for s in results["scenes"] if s.location and s.location != "未知"
    ))

    return ChapterAnalysis(
        chapter_index=chapter.chapter_index,
        characters=results["characters"],
        scenes=results["scenes"],
        dialogues=results["dialogues"],
        props=[],
        locations=locations,
    )

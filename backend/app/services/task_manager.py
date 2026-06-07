import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.models.input import NovelText
from app.models.task import TaskInfo, TaskStatus

logger = logging.getLogger(__name__)


class TaskManager:
    """内存中的异步任务管理器。

    管理转换任务的全生命周期：创建、进度更新、完成、失败、取消。
    线程安全（Lock 保护）。
    """

    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}
        self._chapters: dict[str, NovelText] = {}
        self._lock = threading.Lock()

    def create(self, filename: str) -> TaskInfo:
        """创建新任务并返回任务信息。"""
        task_id = uuid.uuid4().hex[:12]
        task = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            filename=filename,
        )
        with self._lock:
            self._tasks[task_id] = task
        logger.info("任务已创建: %s (%s)", task_id, filename)
        return task

    def get(self, task_id: str) -> Optional[TaskInfo]:
        """查询任务信息，不存在时返回 None。"""
        with self._lock:
            return self._tasks.get(task_id)

    def update_progress(self, task_id: str, progress: int, message: str = "") -> bool:
        """更新任务进度（0-100）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.progress = min(max(progress, 0), 100)
            task.status = TaskStatus.RUNNING
            task.message = message
            task.updated_at = datetime.now(timezone.utc)
            return True

    def set_running(self, task_id: str) -> bool:
        """标记任务为运行中。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.now(timezone.utc)
            return True

    def set_completed(self, task_id: str, result_path: str = "") -> bool:
        """标记任务为已完成。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.result_path = result_path
            task.message = "转换完成"
            task.updated_at = datetime.now(timezone.utc)
            return True

    def set_failed(self, task_id: str, error: str) -> bool:
        """标记任务为失败。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = TaskStatus.FAILED
            task.error = error
            task.message = error[:200]
            task.updated_at = datetime.now(timezone.utc)
            return True

    def cancel(self, task_id: str) -> bool:
        """取消任务（仅待处理或运行中的任务可取消）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.message = "任务已取消"
                task.updated_at = datetime.now(timezone.utc)
                return True
            return False

    def set_chapters(self, task_id: str, novel_text: NovelText) -> None:
        """存储解析后的章节数据，供 GET /chapters 端点查询。"""
        with self._lock:
            self._chapters[task_id] = novel_text

    def get_chapters(self, task_id: str) -> Optional[NovelText]:
        """获取已解析的章节数据，不存在时返回 None。"""
        with self._lock:
            return self._chapters.get(task_id)

    def list_all(self) -> list[TaskInfo]:
        """列出所有任务（按创建时间倒序）。"""
        with self._lock:
            tasks = list(self._tasks.values())
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)


# 全局单例
_task_manager: TaskManager | None = None


def get_task_manager() -> TaskManager:
    """获取全局 TaskManager 单例。"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager

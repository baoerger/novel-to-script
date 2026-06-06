from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """转换任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskInfo(BaseModel):
    """转换任务信息"""

    task_id: str = Field(min_length=1, description="任务唯一 ID（UUID）")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    filename: str = Field(default="", description="原始上传文件名")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比 0-100")
    message: str = Field(default="", description="当前状态描述")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result_path: str = Field(default="", description="输出文件路径")
    error: str = Field(default="", description="错误信息")

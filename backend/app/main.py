from pathlib import Path

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import app_config
from backend.app.models.task import TaskInfo
from backend.app.services.parser import parse_file
from backend.app.services.pipeline import run_conversion
from backend.app.services.task_manager import get_task_manager

app = FastAPI(
    title="AI 小说转剧本工具",
    description="将长篇小说文本自动转换为结构化的 YAML 格式剧本",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/convert", response_model=TaskInfo)
async def convert_novel(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(default=""),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in app_config.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}，仅支持: {', '.join(app_config.supported_extensions)}",
        )

    contents = await file.read()
    if len(contents) > app_config.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大: {len(contents)} bytes，上限 {app_config.max_upload_size} bytes",
        )

    task_manager = get_task_manager()
    task = task_manager.create(file.filename or "unknown")
    task_id = task.task_id

    task_dir = Path(app_config.projects_dir) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    file_path = task_dir / (file.filename or "upload")
    file_path.write_bytes(contents)

    try:
        novel_text = parse_file(str(file_path))
        if title:
            novel_text.title = title
    except Exception as e:
        task_manager.set_failed(task_id, str(e))
        raise HTTPException(status_code=400, detail=f"文件解析失败: {e}")

    background_tasks.add_task(
        run_conversion,
        novel_text=novel_text,
        task_manager=task_manager,
        task_id=task_id,
        output_dir=task_dir,
    )

    return task


@app.get("/health")
async def health_check():
    return {"status": "ok"}

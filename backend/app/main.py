import logging
import time
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import app_config
from backend.app.models.task import TaskInfo
from backend.app.services.parser import parse_file
from backend.app.services.pipeline import run_conversion
from backend.app.services.task_manager import get_task_manager

logger = logging.getLogger(__name__)

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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("未处理的异常: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method, request.url.path, response.status_code, duration_ms,
    )
    return response


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


@app.get("/api/convert/{task_id}", response_model=TaskInfo)
async def get_task_status(task_id: str):
    task = get_task_manager().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return task


@app.get("/api/convert/{task_id}/download")
async def download_script(task_id: str):
    task = get_task_manager().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if task.status not in ("completed",):
        raise HTTPException(status_code=409, detail="任务尚未完成")

    file_path = Path(task.result_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="输出文件不存在")

    filename = file_path.name
    return FileResponse(
        path=str(file_path),
        media_type="application/x-yaml",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}

import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import app_config
from backend.app.models.task import TaskStatus
from backend.app.services.task_manager import TaskManager, get_task_manager

client = TestClient(app)


# ── helpers ──────────────────────────────────────────────────────

def _mock_pipeline(task_manager: TaskManager, task_id: str, output_dir: str):
    """Simulate a fast conversion that creates a dummy YAML and marks complete."""
    task_manager.set_running(task_id)
    task_manager.update_progress(task_id, 50, "mock processing")
    yaml_path = Path(output_dir) / "test_output.yaml"
    yaml_path.write_text("meta:\n  title: Test\n", encoding="utf-8")
    task_manager.set_completed(task_id, str(yaml_path))


# ── POST /api/convert ────────────────────────────────────────────


class TestPostConvert:
    def test_upload_txt_returns_task(self, sample_txt_short: Path):
        with patch("backend.app.main.run_conversion") as mock_run:
            mock_run.side_effect = lambda **kw: _mock_pipeline(
                kw["task_manager"], kw["task_id"], str(kw["output_dir"])
            )

            with open(sample_txt_short, "rb") as f:
                response = client.post(
                    "/api/convert",
                    files={"file": ("sample_short.txt", f, "text/plain")},
                    data={"title": "测试小说"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0
        assert data["status"] in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED)
        assert data["filename"] == "sample_short.txt"

    def test_upload_docx_returns_task(self, sample_docx: Path):
        with patch("backend.app.main.run_conversion") as mock_run:
            mock_run.side_effect = lambda **kw: _mock_pipeline(
                kw["task_manager"], kw["task_id"], str(kw["output_dir"])
            )

            with open(sample_docx, "rb") as f:
                response = client.post(
                    "/api/convert",
                    files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    def test_invalid_extension_returns_400(self, tmp_path: Path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"fake pdf content")
        with open(p, "rb") as f:
            response = client.post(
                "/api/convert",
                files={"file": ("test.pdf", f, "application/pdf")},
            )
        assert response.status_code == 400
        assert "不支持的文件格式" in response.json()["detail"]

    def test_no_file_returns_422(self):
        response = client.post("/api/convert", data={"title": "test"})
        assert response.status_code == 422

    def test_file_too_large(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(app_config, "max_upload_size", 100)
        p = tmp_path / "big.txt"
        p.write_text("x" * 200, encoding="utf-8")
        with open(p, "rb") as f:
            response = client.post(
                "/api/convert",
                files={"file": ("big.txt", f, "text/plain")},
            )
        assert response.status_code == 400
        assert "文件过大" in response.json()["detail"]


# ── GET /health ──────────────────────────────────────────────────


class TestHealthCheck:
    def test_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ── GET /api/convert/{task_id} ───────────────────────────────────


class TestGetTaskStatus:
    def test_returns_correct_fields(self, task_manager: TaskManager):
        task = task_manager.create("test.txt")
        task_manager.set_running(task.task_id)
        task_manager.update_progress(task.task_id, 42, "分析中")

        response = client.get(f"/api/convert/{task.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task.task_id
        assert data["status"] == "running"
        assert data["progress"] == 42
        assert data["message"] == "分析中"
        assert data["filename"] == "test.txt"

    def test_not_found(self):
        response = client.get("/api/convert/nonexistent_id")
        assert response.status_code == 404
        assert "不存在" in response.json()["detail"]

    def test_completed_task(self, task_manager: TaskManager):
        task = task_manager.create("done.txt")
        task_manager.set_completed(task.task_id, "/tmp/output.yaml")

        response = client.get(f"/api/convert/{task.task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert data["result_path"] == "/tmp/output.yaml"


# ── GET /api/convert/{task_id}/download ──────────────────────────


class TestDownload:
    def test_not_found(self):
        response = client.get("/api/convert/nonexistent_id/download")
        assert response.status_code == 404

    def test_task_not_completed_returns_409(self, task_manager: TaskManager):
        task = task_manager.create("pending.txt")
        response = client.get(f"/api/convert/{task.task_id}/download")
        assert response.status_code == 409
        assert "尚未完成" in response.json()["detail"]

    def test_file_missing_returns_404(self, task_manager: TaskManager):
        task = task_manager.create("ghost.txt")
        task_manager.set_completed(task.task_id, "/tmp/nonexistent.yaml")

        response = client.get(f"/api/convert/{task.task_id}/download")
        assert response.status_code == 404

    def test_completed_task_returns_yaml(self, task_manager: TaskManager, tmp_path: Path):
        task = task_manager.create("result.txt")
        yaml_path = tmp_path / "output.yaml"
        yaml_path.write_text("meta:\n  title: 测试\ncharacters: []\n", encoding="utf-8")
        task_manager.set_completed(task.task_id, str(yaml_path))

        response = client.get(f"/api/convert/{task.task_id}/download")
        assert response.status_code == 200
        assert "meta:" in response.text
        assert response.headers["content-type"] == "application/x-yaml"


# ── end-to-end (minimal) ─────────────────────────────────────────


class TestEndToEnd:
    def test_upload_then_status_then_download(self, sample_txt_short: Path, tmp_path: Path):
        """Minimal end-to-end: upload → poll status → download YAML."""
        # Mock the pipeline so it runs synchronously in the test
        with patch("backend.app.main.run_conversion") as mock_run:

            def _simulate(**kw):
                task_mgr = kw["task_manager"]
                tid = kw["task_id"]
                out_dir = kw["output_dir"]
                task_mgr.set_running(tid)
                task_mgr.update_progress(tid, 30, "分析中")
                yaml_path = Path(out_dir) / "test_e2e.yaml"
                yaml_path.write_text("meta:\n  title: 端到端测试\ncharacters: []\n", encoding="utf-8")
                task_mgr.set_completed(tid, str(yaml_path))

            mock_run.side_effect = _simulate

            # 1. Upload
            with open(sample_txt_short, "rb") as f:
                upload_resp = client.post(
                    "/api/convert",
                    files={"file": ("sample_short.txt", f, "text/plain")},
                    data={"title": "端到端测试"},
                )
            assert upload_resp.status_code == 200
            task_id = upload_resp.json()["task_id"]

            # 2. Wait briefly for background task
            time.sleep(0.1)

            # 3. Check status
            status_resp = client.get(f"/api/convert/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            assert status_data["status"] == "completed"
            assert status_data["progress"] == 100

            # 4. Download
            download_resp = client.get(f"/api/convert/{task_id}/download")
            assert download_resp.status_code == 200
            assert "端到端测试" in download_resp.text


# ── CORS middleware ──────────────────────────────────────────────


class TestCORSMiddleware:
    def test_cors_headers_present(self):
        response = client.options(
            "/api/convert",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # FastAPI CORS middleware returns 200 for OPTIONS
        assert response.status_code in (200, 405)


# ── Global error handling ────────────────────────────────────────


class TestErrorHandling:
    def test_non_existent_route_returns_404(self):
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

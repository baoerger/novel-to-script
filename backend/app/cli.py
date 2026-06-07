import argparse
import shutil
import sys
import threading
import time
from pathlib import Path

from backend.app.services.parser import parse_file
from backend.app.services.pipeline import run_conversion
from backend.app.services.task_manager import TaskManager


def main():
    parser = argparse.ArgumentParser(
        description="AI 小说转剧本工具 — 将小说文本转换为 YAML 剧本",
    )
    parser.add_argument(
        "-i", "--input", required=True, help="输入小说文件路径 (.txt / .docx)"
    )
    parser.add_argument(
        "-o", "--output", default="./output.yaml", help="输出 YAML 文件路径"
    )
    parser.add_argument(
        "--title", default="", help="书名（默认从文件名推断）"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="显示详细进度"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在 — {args.input}")
        sys.exit(1)

    suffix = input_path.suffix.lower()
    if suffix not in (".txt", ".text", ".docx"):
        print(f"错误: 不支持的文件格式 — {suffix}，支持: .txt, .docx")
        sys.exit(1)

    print(f"解析文件: {input_path}")
    try:
        novel_text = parse_file(str(input_path))
    except Exception as e:
        print(f"错误: 文件解析失败 — {e}")
        sys.exit(1)

    if args.title:
        novel_text.title = args.title

    print(f"书名: {novel_text.title}")
    print(f"章节数: {len(novel_text.chapters)}")

    task_manager = TaskManager()
    task = task_manager.create(input_path.name)
    task_id = task.task_id

    output_path = Path(args.output).resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 中间结果目录：按书名命名（确定性，同一本书多次运行复用缓存）
    safe_title = novel_text.title.replace("/", "_").replace("\\", "_")[:50]
    task_dir = output_dir / f".checkpoints_{safe_title}"
    task_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.perf_counter()

    if args.verbose:

        def _run():
            run_conversion(
                novel_text=novel_text,
                task_manager=task_manager,
                task_id=task_id,
                output_dir=task_dir,
            )

        thread = threading.Thread(target=_run)
        thread.start()

        last_progress = -1
        while thread.is_alive():
            t = task_manager.get(task_id)
            if t and t.progress != last_progress:
                bar = "█" * (t.progress // 2) + "░" * (50 - t.progress // 2)
                print(f"\r[{bar}] {t.progress:3d}%  {t.message}", end="", flush=True)
                last_progress = t.progress
            time.sleep(0.2)
        thread.join()
        # Final update
        t = task_manager.get(task_id)
        if t:
            bar = "█" * (t.progress // 2) + "░" * (50 - t.progress // 2)
            print(f"\r[{bar}] {t.progress:3d}%  {t.message}")
    else:
        print("转换中...")
        run_conversion(
            novel_text=novel_text,
            task_manager=task_manager,
            task_id=task_id,
            output_dir=task_dir,
        )

    elapsed = time.perf_counter() - start_time
    task = task_manager.get(task_id)

    if task and task.status == "completed":
        actual = Path(task.result_path)
        if actual != output_path and actual.exists():
            shutil.move(str(actual), str(output_path))
            task.result_path = str(output_path)
        print(f"\n转换完成 ({elapsed:.1f}s)")
        print(f"输出: {output_path}")
    else:
        error = task.error if task else "未知错误"
        print(f"\n转换失败: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

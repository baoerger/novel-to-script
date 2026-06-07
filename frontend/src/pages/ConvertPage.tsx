import { useState, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import FileUpload from '../components/FileUpload'
import ProgressBar from '../components/ProgressBar'
import { uploadFile, getTaskStatus, getDownloadUrl, getReportUrl } from '../services/api'
import type { TaskInfo } from '../types'

export default function ConvertPage() {
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [chapterMarkers, setChapterMarkers] = useState('')
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval>>()

  const startPolling = useCallback((taskId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const info = await getTaskStatus(taskId)
        setTask(info)
        if (info.status === 'completed' || info.status === 'failed' || info.status === 'cancelled') {
          clearInterval(pollRef.current)
        }
      } catch {
        // ignore polling errors
      }
    }, 1500)
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const info = await uploadFile(file, title || undefined, chapterMarkers || undefined)
      setTask(info)
      startPolling(info.task_id)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '上传失败'
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  const isDone = task?.status === 'completed'
  const isFailed = task?.status === 'failed'

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">开始转换</h1>

      {!task && (
        <div className="space-y-4">
          <FileUpload onFile={setFile} />

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              书名（可选，覆盖自动检测）
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="留空则自动识别"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">
              章节标注（可选，JSON 格式）
            </label>
            <textarea
              value={chapterMarkers}
              onChange={(e) => setChapterMarkers(e.target.value)}
              placeholder='["第一章", "第二章", ...] 或 [{"start": 0, "end": 100, "title": "序章"}, ...]'
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full py-2.5 rounded-lg text-white font-medium bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? '上传中...' : '开始转换'}
          </button>

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}
        </div>
      )}

      {task && (
        <div className="space-y-6">
          <ProgressBar progress={task.progress} message={task.message} status={task.status} />

          <div className="text-sm text-gray-600 space-y-1">
            <p>文件: {task.filename}</p>
            <p>任务 ID: <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{task.task_id}</code></p>
          </div>

          {isDone && (
            <div className="flex gap-3">
              <a
                href={getDownloadUrl(task.task_id)}
                className="flex-1 text-center py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors"
              >
                下载 YAML
              </a>
              <a
                href={getReportUrl(task.task_id)}
                className="flex-1 text-center py-2 rounded-lg bg-gray-600 text-white font-medium hover:bg-gray-700 transition-colors"
              >
                下载报告
              </a>
              <Link
                to={`/preview/${task.task_id}`}
                className="flex-1 text-center py-2 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700 transition-colors"
              >
                在线预览
              </Link>
            </div>
          )}

          {isFailed && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700 font-medium">转换失败</p>
              <p className="text-sm text-red-600 mt-1">{task.error}</p>
            </div>
          )}

          <button
            onClick={() => {
              clearInterval(pollRef.current)
              setTask(null)
              setFile(null)
            }}
            className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            重新转换
          </button>
        </div>
      )}
    </div>
  )
}

interface Props {
  progress: number
  message: string
  status: string
}

const statusLabels: Record<string, string> = {
  pending: '等待中',
  running: '转换中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-200',
  running: 'bg-indigo-500',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-yellow-500',
}

export default function ProgressBar({ progress, message, status }: Props) {
  const isRunning = status === 'running' || status === 'pending'

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          {statusLabels[status] ?? status}
        </span>
        <span className="text-sm text-gray-500">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            statusColors[status] ?? 'bg-gray-400'
          } ${isRunning ? 'animate-pulse' : ''}`}
          style={{ width: `${progress}%` }}
        />
      </div>
      {message && (
        <p className="text-xs text-gray-500 mt-1.5 truncate">{message}</p>
      )}
    </div>
  )
}

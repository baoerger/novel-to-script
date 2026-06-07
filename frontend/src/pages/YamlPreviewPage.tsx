import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Editor, { type OnMount } from '@monaco-editor/react'
import * as yaml from 'js-yaml'
import { useTaskContext } from '../hooks/TaskContext'

interface OutlineItem {
  act: number
  actTitle: string
  sceneIndex: number
  sceneId: string
  heading: string
  line: number
}

function extractOutline(text: string): OutlineItem[] {
  const items: OutlineItem[] = []
  const lines = text.split('\n')
  let currentAct = -1
  let currentActTitle = ''
  let sceneIndex = 0

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    // Match acts like "- act_number: 0" or "  act_number: 0"
    const actMatch = line.match(/^\s{2}act_number:\s*(\d+)/)
    if (actMatch) {
      currentAct = parseInt(actMatch[1])
      currentActTitle = ''
      // try to get act_title from next line
      const titleMatch = lines[i + 1]?.match(/^\s{4}act_title:\s*(.+)/)
      if (titleMatch) currentActTitle = titleMatch[1].trim()
    }

    const headingMatch = line.match(/^\s{6}scene_heading:\s*(.+)/)
    if (headingMatch && currentAct >= 0) {
      const heading = headingMatch[1].trim()
      // get scene_id from previous few lines
      let sceneId = `scene_${sceneIndex}`
      for (let j = i - 1; j >= Math.max(0, i - 5); j--) {
        const idMatch = lines[j].match(/^\s{6}scene_id:\s*(.+)/)
        if (idMatch) { sceneId = idMatch[1].trim(); break }
      }
      items.push({
        act: currentAct,
        actTitle: currentActTitle,
        sceneIndex,
        sceneId,
        heading,
        line: i + 1,
      })
      sceneIndex++
    }
  }
  return items
}

export default function YamlPreviewPage() {
  const { taskId } = useParams<{ taskId?: string }>()
  const navigate = useNavigate()
  const { taskId: contextTaskId } = useTaskContext()

  const [inputId, setInputId] = useState(taskId ?? contextTaskId ?? '')
  const [yamlText, setYamlText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [outline, setOutline] = useState<OutlineItem[]>([])
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  const effectiveTaskId = taskId ?? inputId

  const loadYaml = useCallback(async (id: string) => {
    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`/api/convert/${id}/download`)
      if (!resp.ok) {
        const detail = resp.status === 404 ? '任务不存在' : resp.status === 409 ? '转换尚未完成' : `HTTP ${resp.status}`
        setError(detail)
        setYamlText('')
        setOutline([])
        return
      }
      const text = await resp.text()
      setYamlText(text)
      setOutline(extractOutline(text))
    } catch {
      setError('加载失败，请检查任务 ID 或网络连接')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (taskId) {
      setInputId(taskId)
      loadYaml(taskId)
    }
  }, [taskId, loadYaml])

  const handleLoad = () => {
    if (effectiveTaskId) {
      navigate(`/preview/${effectiveTaskId}`, { replace: true })
      loadYaml(effectiveTaskId)
    }
  }

  const handleEditorMount: OnMount = (editor) => {
    // scroll to line when outline item clicked
    editor.onDidChangeCursorPosition(() => {
      // no-op, outline → editor scrolling is one-way
    })
  }

  const scrollToLine = (line: number) => {
    // Monaco line numbers are 1-based
    const el = document.querySelector('.monaco-editor')
    if (el) {
      const editorInstance = (window as Record<string, unknown>).__monacoEditor as {
        revealLineInCenter?: (n: number) => void
      } | undefined
      editorInstance?.revealLineInCenter?.(line)
    }
  }

  const toggleCollapse = (key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  // Group outline items by act
  const groupedOutline = outline.reduce<Record<number, { title: string; scenes: OutlineItem[] }>>((acc, item) => {
    if (!acc[item.act]) acc[item.act] = { title: item.actTitle, scenes: [] }
    acc[item.act].scenes.push(item)
    return acc
  }, {})

  return (
    <div className="max-w-7xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">YAML 在线预览</h1>

      {!taskId && (
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={inputId}
            onChange={(e) => setInputId(e.target.value)}
            placeholder="输入任务 ID"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
          />
          <button
            onClick={handleLoad}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            加载
          </button>
        </div>
      )}

      {loading && <p className="text-sm text-gray-500">加载中...</p>}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {yamlText && (
        <div className="flex gap-4" style={{ height: 'calc(100vh - 200px)' }}>
          {/* Outline sidebar */}
          <aside className="w-64 flex-shrink-0 overflow-y-auto border border-gray-200 rounded-lg bg-white p-3">
            <h2 className="text-sm font-medium text-gray-700 mb-3">场景导航</h2>
            {Object.entries(groupedOutline).map(([actStr, { title, scenes }]) => {
              const actKey = `act-${actStr}`
              const isCollapsed = collapsed[actKey]
              return (
                <div key={actKey} className="mb-2">
                  <button
                    onClick={() => toggleCollapse(actKey)}
                    className="flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-800 w-full text-left py-0.5"
                  >
                    <span className="text-[10px]">{isCollapsed ? '▶' : '▼'}</span>
                    {title || `第${parseInt(actStr) + 1}幕`}
                  </button>
                  {!isCollapsed && (
                    <ul className="ml-3 mt-1 space-y-0.5">
                      {scenes.map((item) => (
                        <li key={item.sceneId}>
                          <button
                            onClick={() => scrollToLine(item.line)}
                            className="text-xs text-gray-500 hover:text-indigo-600 transition-colors text-left block truncate w-full"
                            title={item.heading}
                          >
                            {item.heading}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )
            })}
          </aside>

          {/* Editor */}
          <div className="flex-1 border border-gray-200 rounded-lg overflow-hidden">
            <Editor
              language="yaml"
              value={yamlText}
              theme="vs-light"
              onMount={(editor) => {
                ;(window as Record<string, unknown>).__monacoEditor = editor
                handleEditorMount(editor)
              }}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                lineNumbers: 'on',
                fontSize: 13,
                wordWrap: 'off',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

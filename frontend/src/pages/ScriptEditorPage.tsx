import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as yaml from 'js-yaml'
import type { Script, ScriptAct, ScriptScene, ContentElement, Setting } from '../types'

function newContent(): ContentElement {
  return { type: 'dialogue', character: '', text: '', delivery: '' }
}

export default function ScriptEditorPage() {
  const { taskId } = useParams<{ taskId?: string }>()
  const navigate = useNavigate()

  const [inputId, setInputId] = useState(taskId ?? '')
  const [script, setScript] = useState<Script | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const loadScript = useCallback(async (id: string) => {
    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`/api/convert/${id}/download`)
      if (!resp.ok) {
        setError(resp.status === 404 ? '任务不存在' : resp.status === 409 ? '转换尚未完成' : `HTTP ${resp.status}`)
        return
      }
      const text = await resp.text()
      setScript(yaml.load(text) as Script)
    } catch {
      setError('加载失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (taskId) {
      setInputId(taskId)
      loadScript(taskId)
    }
  }, [taskId, loadScript])

  const handleLoad = () => {
    if (inputId) {
      navigate(`/editor/${inputId}`, { replace: true })
      loadScript(inputId)
    }
  }

  const toggleExpand = (key: string) => {
    setExpanded((p) => ({ ...p, [key]: !p[key] }))
  }

  const updateScene = (actIdx: number, sceneIdx: number, patch: Partial<ScriptScene>) => {
    if (!script) return
    const acts = [...script.acts]
    const scenes = [...acts[actIdx].scenes]
    scenes[sceneIdx] = { ...scenes[sceneIdx], ...patch }
    acts[actIdx] = { ...acts[actIdx], scenes }
    setScript({ ...script, acts })
  }

  const updateSetting = (actIdx: number, sceneIdx: number, patch: Partial<Setting>) => {
    if (!script) return
    const scene = script.acts[actIdx].scenes[sceneIdx]
    updateScene(actIdx, sceneIdx, { setting: { ...scene.setting, ...patch } })
  }

  const updateContent = (actIdx: number, sceneIdx: number, ci: number, patch: Partial<ContentElement>) => {
    if (!script) return
    const scene = script.acts[actIdx].scenes[sceneIdx]
    const content = [...scene.content]
    content[ci] = { ...content[ci], ...patch }
    updateScene(actIdx, sceneIdx, { content })
  }

  const addContent = (actIdx: number, sceneIdx: number) => {
    if (!script) return
    const scene = script.acts[actIdx].scenes[sceneIdx]
    updateScene(actIdx, sceneIdx, { content: [...scene.content, newContent()] })
  }

  const removeContent = (actIdx: number, sceneIdx: number, ci: number) => {
    if (!script) return
    const scene = script.acts[actIdx].scenes[sceneIdx]
    updateScene(actIdx, sceneIdx, { content: scene.content.filter((_, i) => i !== ci) })
  }

  const handleDownload = () => {
    if (!script) return
    const yamlStr = yaml.dump(script, { indent: 2, lineWidth: -1, noRefs: true })
    const blob = new Blob([yamlStr], { type: 'application/x-yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${script.meta?.title || 'script'}_edited.yaml`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">剧本编辑器</h1>
        {script && (
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            下载修改后的 YAML
          </button>
        )}
      </div>

      {!taskId && (
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={inputId}
            onChange={(e) => setInputId(e.target.value)}
            placeholder="输入任务 ID"
            className="flex-1 max-w-sm border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
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

      {script && (
        <div className="space-y-2">
          {script.acts.map((act: ScriptAct, ai: number) => (
            <div key={ai} className="border border-gray-200 rounded-lg bg-white">
              <button
                onClick={() => toggleExpand(`act-${ai}`)}
                className="w-full px-4 py-3 text-left flex items-center gap-2 hover:bg-gray-50 transition-colors rounded-lg"
              >
                <span className="text-xs">{expanded[`act-${ai}`] ? '▼' : '▶'}</span>
                <span className="text-sm font-medium text-gray-700">{act.act_title || `第${ai + 1}幕`}</span>
                <span className="text-xs text-gray-400">({act.scenes.length} 场)</span>
              </button>

              {expanded[`act-${ai}`] && (
                <div className="border-t border-gray-100 px-4 py-3 space-y-4">
                  {act.scenes.map((scene: ScriptScene, si: number) => (
                    <div key={scene.scene_id} className="border border-gray-100 rounded-lg p-3 space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-0.5">场景标题</label>
                          <input
                            type="text"
                            value={scene.scene_heading}
                            onChange={(e) => updateScene(ai, si, { scene_heading: e.target.value })}
                            className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-0.5">在场角色 (逗号分隔)</label>
                          <input
                            type="text"
                            value={scene.characters_present.join(', ')}
                            onChange={(e) =>
                              updateScene(ai, si, {
                                characters_present: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                              })
                            }
                            className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-0.5">地点</label>
                          <input
                            type="text"
                            value={scene.setting.location}
                            onChange={(e) => updateSetting(ai, si, { location: e.target.value })}
                            className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-0.5">时间</label>
                          <input
                            type="text"
                            value={scene.setting.time}
                            onChange={(e) => updateSetting(ai, si, { time: e.target.value })}
                            className="w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
                          />
                        </div>
                      </div>

                      {/* Content elements */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-xs font-medium text-gray-500">内容元素</label>
                          <button
                            onClick={() => addContent(ai, si)}
                            className="text-xs text-indigo-600 hover:text-indigo-800 transition-colors"
                          >
                            + 添加
                          </button>
                        </div>
                        <div className="space-y-2">
                          {scene.content.map((el: ContentElement, ci: number) => (
                            <div key={ci} className="flex gap-2 items-start">
                              <select
                                value={el.type}
                                onChange={(e) => updateContent(ai, si, ci, { type: e.target.value as ContentElement['type'] })}
                                className="w-28 border border-gray-200 rounded px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400"
                              >
                                <option value="dialogue">对白</option>
                                <option value="voiceover">旁白</option>
                                <option value="stage_direction">舞台指示</option>
                                <option value="transition">转场</option>
                              </select>
                              {(el.type === 'dialogue' || el.type === 'voiceover') && (
                                <input
                                  type="text"
                                  value={el.character}
                                  onChange={(e) => updateContent(ai, si, ci, { character: e.target.value })}
                                  placeholder="角色"
                                  className="w-20 border border-gray-200 rounded px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400"
                                />
                              )}
                              <input
                                type="text"
                                value={el.text}
                                onChange={(e) => updateContent(ai, si, ci, { text: e.target.value })}
                                placeholder="文本内容"
                                className="flex-1 border border-gray-200 rounded px-1.5 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400"
                              />
                              <button
                                onClick={() => removeContent(ai, si, ci)}
                                className="text-xs text-red-400 hover:text-red-600 transition-colors shrink-0 mt-1"
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                          {scene.content.length === 0 && (
                            <p className="text-xs text-gray-400">暂无内容元素</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

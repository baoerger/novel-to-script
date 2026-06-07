import { useState, useEffect, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as yaml from 'js-yaml'
import type { Script, ScriptCharacter } from '../types'

type SortKey = 'name' | 'role' | 'archetype'

export default function CharactersPage() {
  const { taskId } = useParams<{ taskId?: string }>()
  const navigate = useNavigate()

  const [inputId, setInputId] = useState(taskId ?? '')
  const [characters, setCharacters] = useState<ScriptCharacter[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortAsc, setSortAsc] = useState(true)

  const loadCharacters = useCallback(async (id: string) => {
    setLoading(true)
    setError('')
    try {
      const resp = await fetch(`/api/convert/${id}/download`)
      if (!resp.ok) {
        setError(resp.status === 404 ? '任务不存在' : resp.status === 409 ? '转换尚未完成' : `HTTP ${resp.status}`)
        setCharacters([])
        return
      }
      const text = await resp.text()
      const script = yaml.load(text) as Script
      setCharacters(script.characters ?? [])
    } catch {
      setError('加载失败，请检查任务 ID 或网络连接')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (taskId) {
      setInputId(taskId)
      loadCharacters(taskId)
    }
  }, [taskId, loadCharacters])

  const handleLoad = () => {
    if (inputId) {
      navigate(`/characters/${inputId}`, { replace: true })
      loadCharacters(inputId)
    }
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc((v) => !v)
    } else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    let list = characters
    if (q) {
      list = list.filter((c) =>
        c.name.toLowerCase().includes(q) ||
        c.aliases.some((a) => a.toLowerCase().includes(q)) ||
        c.role.toLowerCase().includes(q) ||
        c.archetype.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q)
      )
    }
    return [...list].sort((a, b) => {
      const aVal = (a[sortKey] ?? '').toLowerCase()
      const bVal = (b[sortKey] ?? '').toLowerCase()
      return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    })
  }, [characters, search, sortKey, sortAsc])

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span className="text-gray-300 ml-1">&#8597;</span>
    return <span className="ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">角色表格</h1>

      {!taskId && (
        <div className="flex gap-2 mb-4">
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

      {characters.length > 0 && (
        <>
          <div className="mb-4">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索姓名、别名、角色、原型..."
              className="w-full max-w-sm border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th
                      className="px-4 py-3 text-left cursor-pointer select-none hover:bg-gray-100 transition-colors"
                      onClick={() => handleSort('name')}
                    >
                      姓名 <SortIcon col="name" />
                    </th>
                    <th className="px-4 py-3 text-left">别名</th>
                    <th
                      className="px-4 py-3 text-left cursor-pointer select-none hover:bg-gray-100 transition-colors"
                      onClick={() => handleSort('role')}
                    >
                      角色 <SortIcon col="role" />
                    </th>
                    <th
                      className="px-4 py-3 text-left cursor-pointer select-none hover:bg-gray-100 transition-colors"
                      onClick={() => handleSort('archetype')}
                    >
                      原型 <SortIcon col="archetype" />
                    </th>
                    <th className="px-4 py-3 text-left">描述</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-800">{c.name}</td>
                      <td className="px-4 py-3 text-gray-500">
                        {c.aliases.length > 0 ? c.aliases.join('、') : '-'}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          c.role === 'protagonist' ? 'bg-blue-100 text-blue-700' :
                          c.role === 'antagonist' ? 'bg-red-100 text-red-700' :
                          c.role === 'supporting' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {c.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{c.archetype || '-'}</td>
                      <td className="px-4 py-3 text-gray-500 max-w-xs truncate" title={c.description}>
                        {c.description || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-xs text-gray-400 mt-2">
            共 {characters.length} 个角色{search ? `，筛选结果 ${filtered.length} 个` : ''}
          </p>
        </>
      )}

      {!loading && !error && characters.length === 0 && (taskId || inputId) && (
        <p className="text-sm text-gray-400">无角色数据</p>
      )}
    </div>
  )
}

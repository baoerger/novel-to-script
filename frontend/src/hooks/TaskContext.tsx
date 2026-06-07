import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'
import type { TaskInfo } from '../types'

interface TaskContextValue {
  taskId: string | null
  task: TaskInfo | null
  setCurrentTask: (t: TaskInfo) => void
  updateTask: (t: TaskInfo) => void
  clearTask: () => void
}

const TaskContext = createContext<TaskContextValue | null>(null)

export function TaskProvider({ children }: { children: ReactNode }) {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<TaskInfo | null>(null)

  const setCurrentTask = useCallback((t: TaskInfo) => {
    setTaskId(t.task_id)
    setTask(t)
  }, [])

  const updateTask = useCallback((t: TaskInfo) => {
    setTask(t)
  }, [])

  const clearTask = useCallback(() => {
    setTaskId(null)
    setTask(null)
  }, [])

  return (
    <TaskContext.Provider value={{ taskId, task, setCurrentTask, updateTask, clearTask }}>
      {children}
    </TaskContext.Provider>
  )
}

export function useTaskContext() {
  const ctx = useContext(TaskContext)
  if (!ctx) throw new Error('useTaskContext must be used within TaskProvider')
  return ctx
}

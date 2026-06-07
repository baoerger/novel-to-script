import axios from 'axios'
import type { TaskInfo, ChapterListResponse } from '../types'

const client = axios.create({ baseURL: '/api' })

export async function uploadFile(
  file: File,
  title?: string,
  chapterMarkers?: string,
): Promise<TaskInfo> {
  const form = new FormData()
  form.append('file', file)
  if (title) form.append('title', title)
  if (chapterMarkers) form.append('chapter_markers', chapterMarkers)
  const { data } = await client.post<TaskInfo>('/convert', form)
  return data
}

export async function getTaskStatus(taskId: string): Promise<TaskInfo> {
  const { data } = await client.get<TaskInfo>(`/convert/${taskId}`)
  return data
}

export async function getChapters(taskId: string): Promise<ChapterListResponse> {
  const { data } = await client.get<ChapterListResponse>(`/convert/${taskId}/chapters`)
  return data
}

export function getDownloadUrl(taskId: string): string {
  return `/api/convert/${taskId}/download`
}

export function getReportUrl(taskId: string): string {
  return `/api/convert/${taskId}/report`
}

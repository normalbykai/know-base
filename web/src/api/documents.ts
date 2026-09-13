import type { Document, ParseTask } from '../types/document'

// 开发环境允许覆盖后端地址，生产环境由部署平台注入该变量。
const API = import.meta.env.VITE_DOCUMENT_API ?? 'http://localhost:8000/api/v1'
// 所有请求统一处理非 2xx 响应，页面不需要重复编写错误分支。
const request = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API}${path}`, init)
  if (!response.ok) throw new Error(await response.text())
  return response.json() as Promise<T>
}
// 上传只创建文档；解析必须由用户显式触发，符合异步状态机设计。
export const uploadDocument = (file: File) => { const data = new FormData(); data.append('file', file); return request<Document>('/documents', { method: 'POST', body: data }) }
export const listDocuments = () => request<Document[]>('/documents')
export const parseDocument = (id: string) => request<ParseTask>(`/documents/${id}/parse`, { method: 'POST' })
export const getParseStatus = (id: string) => request<ParseTask>(`/documents/${id}/parse-status`)
export const retryParse = (id: string) => request<ParseTask>(`/documents/${id}/retry`, { method: 'POST' })
// Markdown 为纯文本响应，因此不能复用默认 JSON 请求函数。
export const getMarkdown = async (id: string) => { const response = await fetch(`${API}/documents/${id}/markdown`); if (!response.ok) throw new Error(await response.text()); return response.text() }

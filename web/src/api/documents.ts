import type { BatchOperation, Document, DocumentChunk, DocumentContent, DocumentPage, DocumentVersion, KnowledgeBase, ParseTask, Tag } from '../types/document'

// 开发环境允许覆盖后端地址，生产环境由部署平台注入该变量。
const API = import.meta.env.VITE_DOCUMENT_API ?? 'http://localhost:8000/api/v1'
// 所有请求统一处理非 2xx 响应，页面不需要重复编写错误分支。
const request = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`${API}${path}`, init)
  if (!response.ok) throw new Error(await response.text())
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
// 上传只创建文档；解析必须由用户显式触发，符合异步状态机设计。
export const uploadDocument = (file: File, knowledgeBaseId?: string) => { const data = new FormData(); data.append('file', file); if (knowledgeBaseId) data.append('knowledge_base_id', knowledgeBaseId); return request<Document>('/documents', { method: 'POST', body: data }) }
export const listDocuments = (params: { page: number; pageSize: number; keyword?: string; status?: string; knowledgeBaseId?: string }) => {
  const query = new URLSearchParams({ page: String(params.page), page_size: String(params.pageSize) })
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.status) query.set('status', params.status)
  if (params.knowledgeBaseId) query.set('knowledge_base_id', params.knowledgeBaseId)
  return request<DocumentPage>(`/documents?${query}`)
}
export const parseDocument = (id: string) => request<ParseTask>(`/documents/${id}/parse`, { method: 'POST' })
export const getParseStatus = (id: string) => request<ParseTask>(`/documents/${id}/parse-status`)
export const listParseTasks = (id: string) => request<ParseTask[]>(`/documents/${id}/tasks`)
export const retryParse = (id: string) => request<ParseTask>(`/documents/${id}/retry`, { method: 'POST' })
export const batchParse = (document_ids: string[]) => request<BatchOperation>('/documents/batch/parse', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ document_ids }) })
export const batchRetry = (document_ids: string[]) => request<BatchOperation>('/documents/batch/retry', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ document_ids }) })
export const deleteDocument = (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' })
export const batchDelete = (document_ids: string[]) => request<BatchOperation>('/documents/batch', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ document_ids }) })
export const listKnowledgeBases = () => request<KnowledgeBase[]>('/knowledge-bases')
export const createKnowledgeBase = (name: string) => request<KnowledgeBase>('/knowledge-bases', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
export const assignKnowledgeBase = (id: string, knowledge_base_id?: string) => request<Document>(`/documents/${id}/knowledge-base`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ knowledge_base_id: knowledge_base_id ?? null }) })
export const listTags = () => request<Tag[]>('/tags')
export const createTag = (name: string) => request<Tag>('/tags', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
export const getDocumentTags = (id: string) => request<Tag[]>(`/documents/${id}/tags`)
export const replaceDocumentTags = (id: string, tag_ids: string[]) => request<Tag[]>(`/documents/${id}/tags`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tag_ids }) })
// Markdown 为纯文本响应，因此不能复用默认 JSON 请求函数。
export const listVersions = (id: string) => request<DocumentVersion[]>(`/documents/${id}/versions`)
export const listChunks = (id: string, version?: number) => request<DocumentChunk[]>(`/documents/${id}/chunks${version ? `?version=${version}` : ''}`)
export const getMarkdown = async (id: string, version?: number) => { const query = version ? `?version=${version}` : ''; const response = await fetch(`${API}/documents/${id}/markdown${query}`); if (!response.ok) throw new Error(await response.text()); return response.text() }
export const getContent = (id: string, version?: number) => request<DocumentContent>(`/documents/${id}/content${version ? `?version=${version}` : ''}`)
// 原始文件走浏览器原生预览，避免把大文件重复读入前端内存。
export const getSourceUrl = (id: string) => `${API}/documents/${id}/source`

export type Document = { id: string; filename: string; content_type: string; file_size: number; status: string; created_at: string }
export type ParseTask = { task_id: string; document_id: string; status: string; retry_count: number; error_message?: string }
export type DocumentBlock = { id: string; type: string; page?: number; level?: number; text?: string; content?: string }
export type DocumentContent = { document_id: string; title: string; metadata: Record<string, unknown>; blocks: DocumentBlock[] }

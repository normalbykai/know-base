export type Document = { id: string; filename: string; content_type: string; file_size: number; status: string; created_at: string }
export type ParseTask = { task_id: string; document_id: string; status: string; retry_count: number; error_message?: string }

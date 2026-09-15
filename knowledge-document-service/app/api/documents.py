from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.parse_task import ParseTask
from app.schemas.knowledge_base import DocumentKnowledgeBaseUpdate, DocumentTagsUpdate, TagOut
from app.schemas.document import BatchOperationOut, DocumentChunkOut, DocumentIdsRequest, DocumentListOut, DocumentModel, DocumentOut, DocumentVersionOut, ParseTaskOut
from app.services.document_service import DocumentService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.storage_service import StorageService
from app.workers.parse_worker import parse_document
from urllib.parse import quote

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

SUPPORTED_UPLOAD_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".webp": {"image/webp"},
}


def validate_upload(filename: str, content_type: str) -> None:
    """限制为当前默认解析链路实际支持的格式，避免用户上传后才得到必然失败。"""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if content_type not in SUPPORTED_UPLOAD_TYPES.get(f".{suffix}", set()):
        raise HTTPException(415, "仅支持 PDF、PNG、JPG/JPEG 和 WEBP 格式的文件")


def task_out(task) -> ParseTaskOut:
    """将 ORM 任务转换为 API 契约，避免响应泄漏内部字段。"""
    return ParseTaskOut(task_id=task.id, document_id=task.document_id, status=task.status.value, retry_count=task.retry_count, error_code=task.error_code, error_message=task.error_message, parser=task.parser, started_at=task.started_at, finished_at=task.finished_at, created_at=task.created_at)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), knowledge_base_id: str | None = Form(default=None), db: Session = Depends(get_db)):
    """接收文件并立即创建文档；不在 HTTP 请求内执行耗时解析。"""
    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"
    validate_upload(filename, content_type)
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty files cannot be uploaded")
    if len(data) > get_settings().max_upload_bytes:
        raise HTTPException(413, "File exceeds MAX_UPLOAD_BYTES")
    if knowledge_base_id and not db.get(KnowledgeBase, knowledge_base_id):
        raise HTTPException(404, "目标知识库不存在")
    document = DocumentService(db).create_document(filename, content_type, data, knowledge_base_id=knowledge_base_id)
    return document


@router.get("", response_model=DocumentListOut)
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, max_length=200),
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    knowledge_base_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """按名称、状态筛选并分页返回文档，避免管理页在数据增长后全量加载。"""
    statement = select(Document)
    count_statement = select(func.count()).select_from(Document)
    if keyword:
        condition = Document.filename.ilike(f"%{keyword.strip()}%")
        statement, count_statement = statement.where(condition), count_statement.where(condition)
    if document_status:
        statement, count_statement = statement.where(Document.status == document_status), count_statement.where(Document.status == document_status)
    if knowledge_base_id:
        statement, count_statement = statement.where(Document.knowledge_base_id == knowledge_base_id), count_statement.where(Document.knowledge_base_id == knowledge_base_id)
    total = db.scalar(count_statement) or 0
    items = list(db.scalars(statement.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return DocumentListOut(items=items, total=total, page=page, page_size=page_size)


@router.post("/batch/parse", response_model=BatchOperationOut, status_code=status.HTTP_202_ACCEPTED)
def batch_parse(payload: DocumentIdsRequest, db: Session = Depends(get_db)):
    """批量提交未解析文档；处理中或不存在的项明确返回跳过原因。"""
    result = BatchOperationOut()
    service = DocumentService(db)
    documents = {item.id: item for item in db.scalars(select(Document).where(Document.id.in_(payload.document_ids)))}
    for document_id in payload.document_ids:
        document = documents.get(document_id)
        if not document:
            result.skipped[document_id] = "文档不存在"
        elif document.status != DocumentStatus.UPLOADED:
            result.skipped[document_id] = "仅已上传且未解析的文档可开始解析"
        else:
            task = service.queue_parse(document)
            parse_document.send(task.id)
            result.processed_ids.append(document_id)
    return result


@router.post("/batch/retry", response_model=BatchOperationOut, status_code=status.HTTP_202_ACCEPTED)
def batch_retry(payload: DocumentIdsRequest, db: Session = Depends(get_db)):
    """批量重试失败文档，保留每份文档的重试计数。"""
    result = BatchOperationOut()
    service = DocumentService(db)
    documents = {item.id: item for item in db.scalars(select(Document).where(Document.id.in_(payload.document_ids)))}
    for document_id in payload.document_ids:
        document = documents.get(document_id)
        if not document:
            result.skipped[document_id] = "文档不存在"
        elif document.status != DocumentStatus.FAILED:
            result.skipped[document_id] = "仅失败文档可重新解析"
        else:
            task = service.queue_parse(document, retry=True)
            parse_document.send(task.id)
            result.processed_ids.append(document_id)
    return result


@router.delete("/batch", response_model=BatchOperationOut)
def batch_delete(payload: DocumentIdsRequest, db: Session = Depends(get_db)):
    """批量清理文档及其对象；处理中项不删除，防止与 Worker 写入竞争。"""
    result = BatchOperationOut()
    service = DocumentService(db)
    documents = {item.id: item for item in db.scalars(select(Document).where(Document.id.in_(payload.document_ids)))}
    for document_id in payload.document_ids:
        document = documents.get(document_id)
        if not document:
            result.skipped[document_id] = "文档不存在"
            continue
        try:
            service.delete_document(document)
            result.processed_ids.append(document_id)
        except ValueError as exc:
            result.skipped[document_id] = str(exc)
    return result


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """读取单一文档的当前状态与元数据。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    return document


@router.put("/{document_id}/knowledge-base", response_model=DocumentOut)
def assign_knowledge_base(document_id: str, payload: DocumentKnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """显式变更文档归属，未归档文档可传空值回到公共待整理区。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    try:
        KnowledgeBaseService(db).assign_document(document, payload.knowledge_base_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return document


@router.get("/{document_id}/tags", response_model=list[TagOut])
def document_tags(document_id: str, db: Session = Depends(get_db)):
    """读取文档当前标签，供管理端编辑与检索筛选使用。"""
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")
    return KnowledgeBaseService(db).document_tags(document_id)


@router.put("/{document_id}/tags", response_model=list[TagOut])
def replace_document_tags(document_id: str, payload: DocumentTagsUpdate, db: Session = Depends(get_db)):
    """整体替换文档标签；拒绝不存在标签保证关联数据完整。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    try:
        return KnowledgeBaseService(db).replace_document_tags(document, payload.tag_ids)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """删除单份非活动文档及所有解析产物，不保留孤儿对象。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    try:
        DocumentService(db).delete_document(document)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{document_id}/source")
def source_document(document_id: str, db: Session = Depends(get_db)):
    """以内联响应返回原始文件，供浏览器预览；对象存储路径不暴露给前端。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    return Response(
        StorageService().get_bytes(document.storage_path),
        media_type=document.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(document.filename)}"},
    )


@router.post("/{document_id}/parse", response_model=ParseTaskOut, status_code=status.HTTP_202_ACCEPTED)
def create_parse_task(document_id: str, db: Session = Depends(get_db)):
    """将文档置为 QUEUED 并投递轻量级后台任务。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    try:
        task = DocumentService(db).queue_parse(document)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    parse_document.send(task.id)
    return task_out(task)


@router.get("/{document_id}/parse-status", response_model=ParseTaskOut)
def parse_status(document_id: str, db: Session = Depends(get_db)):
    """返回最新任务状态，供前端轮询而非长连接等待。"""
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")
    task = DocumentService(db).latest_task(document_id)
    if not task:
        raise HTTPException(404, "No parse task exists for this document")
    return task_out(task)


@router.get("/{document_id}/tasks", response_model=list[ParseTaskOut])
def list_parse_tasks(document_id: str, db: Session = Depends(get_db)):
    """返回解析任务时间线，让管理端能审查重试、解析器与失败原因。"""
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")
    tasks = db.scalars(select(ParseTask).where(ParseTask.document_id == document_id).order_by(ParseTask.created_at.desc()))
    return [task_out(task) for task in tasks]


@router.post("/{document_id}/retry", response_model=ParseTaskOut, status_code=status.HTTP_202_ACCEPTED)
def retry_parse(document_id: str, db: Session = Depends(get_db)):
    """仅允许失败文档重试，保留并递增历史重试计数。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    if document.status != DocumentStatus.FAILED:
        raise HTTPException(409, "Only failed documents can be retried")
    task = DocumentService(db).queue_parse(document, retry=True)
    parse_document.send(task.id)
    return task_out(task)


def latest_version(document_id: str, db: Session, version: int | None = None) -> DocumentVersion:
    """获取最新成功版本；未解析完成时明确拒绝内容预览。"""
    statement = select(DocumentVersion).where(DocumentVersion.document_id == document_id)
    if version is not None:
        statement = statement.where(DocumentVersion.version == version)
    document_version = db.scalar(statement.order_by(DocumentVersion.version.desc()))
    if not document_version:
        raise HTTPException(409, "Document has no parsed version")
    return document_version


@router.get("/{document_id}/versions", response_model=list[DocumentVersionOut])
def list_versions(document_id: str, db: Session = Depends(get_db)):
    """按版本倒序列出成功解析历史，供人工比较和回溯。"""
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")
    return list(db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.desc())))


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkOut])
def list_chunks(document_id: str, version: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    """返回指定解析版本的稳定分块，用于人工验收和后续检索调试。"""
    document_version = latest_version(document_id, db, version)
    return list(db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_version_id == document_version.id).order_by(DocumentChunk.chunk_index)
    ))


@router.get("/{document_id}/content", response_model=DocumentModel)
def content(document_id: str, version: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    """返回后续检索链路唯一应消费的标准化 JSON。"""
    document_version = latest_version(document_id, db, version)
    return JSONResponse(content=__import__("json").loads(StorageService().get_bytes(document_version.json_path)))


@router.get("/{document_id}/markdown", response_class=PlainTextResponse)
def markdown(document_id: str, version: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    """返回标准 Markdown，用于前端预览及人工质量检查。"""
    document_version = latest_version(document_id, db, version)
    return StorageService().get_bytes(document_version.markdown_path).decode("utf-8")

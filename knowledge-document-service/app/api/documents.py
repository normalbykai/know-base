from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.document import Document, DocumentStatus, DocumentVersion
from app.schemas.document import DocumentModel, DocumentOut, ParseTaskOut
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService
from app.workers.parse_worker import parse_document

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def task_out(task) -> ParseTaskOut:
    """将 ORM 任务转换为 API 契约，避免响应泄漏内部字段。"""
    return ParseTaskOut(task_id=task.id, document_id=task.document_id, status=task.status.value, retry_count=task.retry_count, error_code=task.error_code, error_message=task.error_message)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """接收文件并立即创建文档；不在 HTTP 请求内执行耗时解析。"""
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty files cannot be uploaded")
    if len(data) > get_settings().max_upload_bytes:
        raise HTTPException(413, "File exceeds MAX_UPLOAD_BYTES")
    document = DocumentService(db).create_document(file.filename or "unnamed", file.content_type or "application/octet-stream", data)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    """按创建时间倒序返回文档列表，供第一阶段管理页使用。"""
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """读取单一文档的当前状态与元数据。"""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    return document


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


def latest_version(document_id: str, db: Session) -> DocumentVersion:
    """获取最新成功版本；未解析完成时明确拒绝内容预览。"""
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.desc()))
    if not version:
        raise HTTPException(409, "Document has no parsed version")
    return version


@router.get("/{document_id}/content", response_model=DocumentModel)
def content(document_id: str, db: Session = Depends(get_db)):
    """返回后续检索链路唯一应消费的标准化 JSON。"""
    version = latest_version(document_id, db)
    return JSONResponse(content=__import__("json").loads(StorageService().get_bytes(version.json_path)))


@router.get("/{document_id}/markdown", response_class=PlainTextResponse)
def markdown(document_id: str, db: Session = Depends(get_db)):
    """返回标准 Markdown，用于前端预览及人工质量检查。"""
    version = latest_version(document_id, db)
    return StorageService().get_bytes(version.markdown_path).decode("utf-8")

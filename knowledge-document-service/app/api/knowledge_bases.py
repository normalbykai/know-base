from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.models.tag import Tag
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeBaseUpdate, TagCreate, TagOut
from app.services.knowledge_base_service import KnowledgeBaseService


router = APIRouter(prefix="/api/v1", tags=["knowledge-management"])


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut])
def list_knowledge_bases(db: Session = Depends(get_db)):
    """列出可作为文档归属和未来检索范围的全部知识库。"""
    return list(db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())))


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(payload: KnowledgeBaseCreate, db: Session = Depends(get_db)):
    """创建知识库；名称重复时返回明确冲突而非数据库内部错误。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "知识库名称不能为空")
    knowledge_base = KnowledgeBase(name=name, description=payload.description.strip() if payload.description else None)
    db.add(knowledge_base)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from exc
    db.refresh(knowledge_base)
    return knowledge_base


@router.patch("/knowledge-bases/{knowledge_base_id}", response_model=KnowledgeBaseOut)
def update_knowledge_base(knowledge_base_id: str, payload: KnowledgeBaseUpdate, db: Session = Depends(get_db)):
    """只更新明确提交的字段，description 可置空以清除说明。"""
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(404, "Knowledge base not found")
    if "name" in payload.model_fields_set:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(422, "知识库名称不能为空")
        knowledge_base.name = name
    if "description" in payload.model_fields_set:
        knowledge_base.description = payload.description.strip() if payload.description else None
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "知识库名称已存在") from exc
    db.refresh(knowledge_base)
    return knowledge_base


@router.delete("/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(knowledge_base_id: str, db: Session = Depends(get_db)):
    """仅允许删除空知识库，文档迁移由管理员显式完成。"""
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(404, "Knowledge base not found")
    try:
        KnowledgeBaseService(db).delete_knowledge_base(knowledge_base)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    """标签按名称排序，便于文档编辑时选择现有分类。"""
    return list(db.scalars(select(Tag).order_by(Tag.name)))


@router.post("/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagCreate, db: Session = Depends(get_db)):
    """创建可复用标签；重复名称以冲突响应提示管理员复用现有标签。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "标签名称不能为空")
    tag = Tag(name=name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "标签名称已存在") from exc
    db.refresh(tag)
    return tag

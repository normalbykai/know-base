from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas.search import SearchResponse
from app.services.search_service import KeywordSearchService


router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def keyword_search(
    knowledge_base_id: str,
    q: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tag_ids: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """执行知识库内关键词检索；知识库是强制边界，禁止无范围的全库搜索。"""
    if not db.get(KnowledgeBase, knowledge_base_id):
        raise HTTPException(404, "Knowledge base not found")
    if not q.strip():
        raise HTTPException(422, "搜索词不能为空")
    return KeywordSearchService(db).search(knowledge_base_id, q, page, page_size, tag_ids)

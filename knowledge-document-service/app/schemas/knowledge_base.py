from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """创建知识库时的最小信息，名称作为管理端可见标识。"""
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class KnowledgeBaseUpdate(BaseModel):
    """知识库允许按需修改名称和说明，不影响已归属文档。"""
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)


class KnowledgeBaseOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    """标签名称在当前单租户范围内唯一，避免近义重复标签。"""
    name: str = Field(min_length=1, max_length=64)


class TagOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentKnowledgeBaseUpdate(BaseModel):
    """文档可归档至知识库，传 null 可移回未归档列表。"""
    knowledge_base_id: str | None = None


class DocumentTagsUpdate(BaseModel):
    """用完整标签集合替换当前文档标签，最多 30 个以控制管理复杂度。"""
    tag_ids: list[str] = Field(default_factory=list, max_length=30)

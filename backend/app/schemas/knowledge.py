from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    title: str
    source: str
    article: str
    version: str
    category: str
    effective_date: str | None
    content: str
    metadata: dict[str, object]
    status: str
    created_at: datetime


class KnowledgeDocumentCreate(BaseModel):
    title: str
    source: str
    version: str = "MVP"
    article: str = ""
    category: str
    effective_date: str | None = None
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)


class KnowledgeSearchResult(BaseModel):
    id: str = ""
    document_id: str
    title: str = ""
    source: str
    article: str
    category: str = ""
    content: str
    version: str = ""
    effective_date: str | None = None
    score: float
    metadata: dict[str, object] = Field(default_factory=dict)


class KnowledgeChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    project_id: str | None = None
    use_llm: bool | None = None


class KnowledgeChatResult(BaseModel):
    question: str
    mode: str  # rag_only | rag_llm
    description: str
    answer: str
    citations: list[dict[str, object]]
    retrieval: dict[str, object]
    llm: dict[str, object]

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source: str
    version: str
    category: str
    content: str
    status: str
    created_at: datetime


class KnowledgeDocumentCreate(BaseModel):
    title: str
    source: str
    version: str = "MVP"
    category: str
    content: str

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError
from app.models import KnowledgeDocument, User
from app.schemas.knowledge import KnowledgeDocumentCreate
from app.utils.ids import new_id


class KnowledgeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[KnowledgeDocument]:
        return self.db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "active").order_by(KnowledgeDocument.category, KnowledgeDocument.title).all()

    def search(self, query: str) -> list[KnowledgeDocument]:
        if not query.strip():
            return self.list()
        like = f"%{query.strip()}%"
        return self.db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "active", or_(KnowledgeDocument.title.like(like), KnowledgeDocument.category.like(like), KnowledgeDocument.source.like(like), KnowledgeDocument.content.like(like))).order_by(KnowledgeDocument.category, KnowledgeDocument.title).all()

    def create(self, request: KnowledgeDocumentCreate, actor: User) -> KnowledgeDocument:
        if actor.role != "admin":
            raise ForbiddenError("只有管理员可以上传规范文档")
        document = KnowledgeDocument(id=new_id("KNO"), title=request.title, source=request.source, version=request.version, category=request.category, content=request.content, created_by=actor.id, status="active")
        self.db.add(document)
        self.db.commit()
        return document

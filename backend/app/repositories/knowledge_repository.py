from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.knowledge.types import KnowledgeClause
from app.models import KnowledgeDocument


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[KnowledgeDocument]:
        return self.db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "active").order_by(KnowledgeDocument.category, KnowledgeDocument.title).all()

    def upsert_clause(self, clause: KnowledgeClause, *, created_by: str | None = None) -> KnowledgeDocument:
        row_id = clause.document_id
        document = self.db.get(KnowledgeDocument, row_id)
        if document and (document.article != clause.article or document.content != clause.content):
            suffix = hashlib.sha256(clause.article.encode("utf-8")).hexdigest()[:12]
            row_id = f"{clause.document_id}:{suffix}"
            document = self.db.get(KnowledgeDocument, row_id)
        metadata = dict(clause.metadata)
        metadata.setdefault("document_id", clause.document_id)
        if document is None:
            document = KnowledgeDocument(id=row_id, created_by=created_by)
            self.db.add(document)
        document.title = clause.title
        document.source = clause.source
        document.version = clause.version or "MVP"
        document.article = clause.article
        document.category = clause.category
        document.effective_date = clause.effective_date
        document.content = clause.content
        document.metadata_json = metadata
        document.status = "active"
        return document

    def active_documents(self) -> list[KnowledgeDocument]:
        return self.list()

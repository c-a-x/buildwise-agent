from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError
from app.knowledge.parsers import KnowledgeParseError, parse_knowledge_file
from app.knowledge.types import KnowledgeClause
from app.models import KnowledgeDocument, User
from app.providers.factory import build_retrieval_provider
from app.providers.retrieval.chroma import ChromaRetrievalProvider
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.knowledge import KnowledgeDocumentCreate
from app.utils.ids import new_id


class KnowledgeService:
    def __init__(self, db: Session, runtime_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = runtime_settings or default_settings
        self.repository = KnowledgeRepository(db)

    def list(self) -> list[KnowledgeDocument]:
        return self.repository.list()

    def search(self, query: str) -> list[dict[str, object]]:
        if not query.strip():
            return [document_payload(document) for document in self.list()]
        provider = build_retrieval_provider(self.settings)
        return provider.search(query, {}, top_k=20)

    def create(self, request: KnowledgeDocumentCreate, actor: User) -> KnowledgeDocument:
        if actor.role != "admin":
            from app.core.exceptions import ForbiddenError

            raise ForbiddenError("只有管理员可以上传规范文档")
        document_id = new_id("KNO")
        metadata = {**request.metadata, "document_id": document_id}
        document = KnowledgeDocument(
            id=document_id,
            title=request.title,
            source=request.source,
            version=request.version,
            article=request.article,
            category=request.category,
            effective_date=request.effective_date,
            content=request.content,
            metadata_json=metadata,
            created_by=actor.id,
            status="active",
        )
        self.db.add(document)
        self.db.commit()
        if self.settings.retrieval_provider == "chroma":
            provider = self._chroma_provider()
            provider.index.upsert([self._clause_from_document(document)])
        return document

    def index_status(self) -> dict[str, object]:
        provider = build_retrieval_provider(self.settings)
        if isinstance(provider, ChromaRetrievalProvider):
            stats = provider.index.stats()
            return {
                "provider": provider.name,
                "indexed": stats["clause_count"] > 0,
                "document_count": stats["document_count"],
                "clause_count": stats["clause_count"],
                "directory": str(provider.directory),
                "collection": provider.index.collection.name,
            }
        if isinstance(provider, LocalKeywordRetrievalProvider):
            stats = provider.stats()
            return {
                "provider": provider.name,
                "indexed": stats["clause_count"] > 0,
                "document_count": stats["document_count"],
                "clause_count": stats["clause_count"],
                "directory": None,
                "collection": None,
            }
        return {
            "provider": self.settings.retrieval_provider,
            "indexed": False,
            "document_count": 0,
            "clause_count": 0,
            "directory": None,
            "collection": None,
        }

    def reindex(self) -> dict[str, object]:
        if self.settings.retrieval_provider != "chroma":
            return self.index_status()
        path = self.settings.knowledge_json_path
        if not path.exists():
            raise AppError(f"知识库源文件不存在: {path}", "KNOWLEDGE_SOURCE_NOT_FOUND", 400)
        try:
            clauses = parse_knowledge_file(path)
        except KnowledgeParseError as exc:
            raise AppError(str(exc), "KNOWLEDGE_PARSE_ERROR", 400) from exc
        return self.ingest_clauses(clauses, clear=True)

    def ingest_clauses(self, clauses: Iterable[KnowledgeClause], *, clear: bool = False) -> dict[str, object]:
        records = list(clauses)
        for clause in records:
            self.repository.upsert_clause(clause)
        self.db.commit()
        if self.settings.retrieval_provider == "chroma":
            provider = self._chroma_provider()
            if clear:
                provider.index.clear()
            operation = provider.index.upsert(records)
            return {"provider": provider.name, **operation, **provider.index.stats()}
        return {"provider": self.settings.retrieval_provider, **self.index_status()}

    def clear_index(self) -> dict[str, object]:
        if self.settings.retrieval_provider == "chroma":
            provider = self._chroma_provider()
            provider.index.clear()
        return self.index_status()

    def _chroma_provider(self) -> ChromaRetrievalProvider:
        provider = build_retrieval_provider(self.settings)
        if not isinstance(provider, ChromaRetrievalProvider):
            raise AppError("当前检索 Provider 不是 Chroma", "PROVIDER_NOT_SUPPORTED", 500)
        return provider

    @staticmethod
    def _clause_from_document(document: KnowledgeDocument) -> KnowledgeClause:
        metadata = document.metadata_json if isinstance(document.metadata_json, dict) else {}
        return KnowledgeClause(
            document_id=document.id,
            source=document.source,
            title=document.title,
            article=document.article,
            category=document.category,
            content=document.content,
            version=document.version,
            effective_date=document.effective_date,
            metadata=metadata,
        )


def document_payload(document: KnowledgeDocument) -> dict[str, object]:
    metadata = document.metadata_json if isinstance(document.metadata_json, dict) else {}
    return {
        "id": document.id,
        "document_id": document.id,
        "title": document.title,
        "source": document.source,
        "article": document.article,
        "version": document.version,
        "category": document.category,
        "effective_date": document.effective_date,
        "content": document.content,
        "metadata": metadata,
        "status": document.status,
        "created_at": document.created_at,
    }

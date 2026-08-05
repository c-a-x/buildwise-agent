from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError
from app.knowledge.parsers import KnowledgeParseError, parse_knowledge_file
from app.knowledge.types import KnowledgeClause
from app.models import Incident, KnowledgeDocument, User, WorkOrder
from app.providers.factory import build_retrieval_provider, build_text_provider
from app.providers.retrieval.chroma import ChromaRetrievalProvider
from app.providers.retrieval.local_keyword import LocalKeywordRetrievalProvider
from app.repositories.knowledge_repository import KnowledgeRepository
from app.rules.risk_rules import RISK_RULES
from app.schemas.knowledge import KnowledgeChatResult, KnowledgeDocumentCreate
from app.utils.ids import new_id


# 知识问答风险提示关键词表：命中则追加整改提示（责任人/时限取自 risk_rules）。
_RISK_KEYWORDS: dict[str, tuple[str, list[str]]] = {
    "no_helmet": ("未佩戴安全帽", ["安全帽", "帽"]),
    "missing_guardrail": ("临边防护缺失", ["临边", "防护栏", "洞口", "护栏"]),
    "no_safety_vest": ("未穿反光背心", ["背心", "反光"]),
    "crack": ("墙体裂缝", ["裂缝", "开裂"]),
    "leakage": ("渗漏", ["渗漏", "漏水", "渗水"]),
    "abscission": ("剥落", ["剥落", "掉块"]),
    "corrosion": ("锈蚀", ["锈蚀", "生锈"]),
    "bulge": ("鼓包", ["鼓包", "空鼓"]),
}


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

    def chat(self, *, question: str, project_id: str | None = None, use_llm: bool | None = None) -> KnowledgeChatResult:
        """统一 RAG 回答组装：规范条文 + 风险提示 + 现场概况，LLM 可选总结。"""
        provider = build_retrieval_provider(self.settings)
        hits = provider.search(question, {}, top_k=8)

        # 一、规范与标准条文
        if hits:
            answer_parts = [
                "【一、规范与标准条文】",
                *[
                    f"{index}. 《{item['source']}》{item.get('article') or ''} · {item.get('title') or ''} — {item['content']}（相似度 {float(item['score']):.2f}）"
                    for index, item in enumerate(hits, start=1)
                ],
            ]
            citations = [
                {
                    "type": "clause",
                    "document_id": item["document_id"],
                    "source": item["source"],
                    "article": item.get("article", ""),
                    "title": item.get("title", ""),
                    "score": float(item["score"]),
                }
                for item in hits
            ]
        else:
            answer_parts = ["【一、规范与标准条文】", "未检索到与该问题直接匹配的条款，请补充关键词或查阅知识库完整清单。"]
            citations = []

        # 二、相关风险提示
        matched_types = [
            hazard_type
            for hazard_type, (_name, keywords) in _RISK_KEYWORDS.items()
            if any(keyword in question for keyword in keywords)
        ]
        risk_lines: list[str] = []
        for hazard_type in matched_types:
            name = _RISK_KEYWORDS[hazard_type][0]
            rule = RISK_RULES.get(hazard_type) if isinstance(RISK_RULES.get(hazard_type), dict) else None
            if rule and rule.get("assignee_role"):
                risk_lines.append(f"命中风险类型「{name}」（{hazard_type}），建议落实责任角色 {rule['assignee_role']}，在 {rule['deadline_hours']} 小时内闭环整改。")
            else:
                risk_lines.append(f"命中风险类型「{name}」（{hazard_type}），建议按规范完成整改并由项目人员复查。")
        if risk_lines:
            answer_parts.append("【二、相关风险提示】")
            answer_parts.extend(risk_lines)

        # 三、现场概况（传 project_id 时）
        site_parts: list[str] = []
        if project_id:
            site_parts = self._site_summary(project_id)
            answer_parts.append("【三、现场概况】")
            answer_parts.extend(site_parts)

        answer = "\n".join(answer_parts)
        retrieval = {
            "clauses": {"ready": bool(hits), "count": len(hits)},
            "risk_tip": {"included": bool(risk_lines), "hazard_types": matched_types},
            "site": {"included": bool(project_id), "project_id": project_id},
        }

        # LLM 可选总结：仅配置齐全时才调用，任何异常降级为离线拼装
        llm = {"used": False, "model": None, "error": None}
        mode = "rag_only"
        description = "离线检索拼装"
        if use_llm is not False and self._llm_ready():
            try:
                text_provider = build_text_provider(self.settings)
                llm_answer = text_provider.generate_report({"question": question, "sections": answer, "citations": citations})
                answer = str(llm_answer).strip()
                llm = {"used": True, "model": self.settings.llm_model, "error": None}
                mode = "rag_llm"
                description = "检索拼装 + LLM 总结"
            except Exception as exc:  # LLM 调用失败不阻断问答
                llm["error"] = str(exc)
        elif use_llm:
            llm["error"] = "LLM 未配置，自动使用离线检索拼装"

        return KnowledgeChatResult(
            question=question,
            mode=mode,
            description=description,
            answer=answer,
            citations=citations,
            retrieval=retrieval,
            llm=llm,
        )

    def _site_summary(self, project_id: str) -> list[str]:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        incidents = (
            self.db.query(Incident)
            .filter(Incident.project_id == project_id, Incident.created_at >= since)
            .all()
        )
        safety_count = 0
        quality_count = 0
        risk_counts: dict[str, int] = {}
        for incident in incidents:
            metadata = incident.metadata_json if isinstance(incident.metadata_json, dict) else {}
            if metadata.get("module") == "quality":
                quality_count += 1
            else:
                safety_count += 1
            risk_counts[incident.risk_level] = risk_counts.get(incident.risk_level, 0) + 1
        open_orders = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.project_id == project_id, WorkOrder.status != "closed")
            .count()
        )
        lines = [f"近 7 天共记录 {len(incidents)} 条隐患/缺陷（安全 {safety_count} 条、质量 {quality_count} 条）。"]
        if risk_counts:
            levels = "、".join(f"{level} {count} 条" for level, count in sorted(risk_counts.items(), key=lambda item: -item[1]))
            lines.append(f"风险等级分布：{levels}。")
        lines.append(f"当前未闭环整改工单 {open_orders} 个。")
        return lines

    def _llm_ready(self) -> bool:
        return (
            self.settings.text_provider == "openai_compatible"
            and bool(self.settings.llm_base_url)
            and bool(self.settings.llm_api_key)
            and bool(self.settings.llm_model)
        )

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

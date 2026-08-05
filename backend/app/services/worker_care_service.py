from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError, ForbiddenError
from app.models import ProjectMember, User, WorkerMessage
from app.providers.factory import build_retrieval_provider, build_speech_provider
from app.providers.text.template import TemplateTextProvider
from app.rules.risk_rules import RISK_RULES
from app.utils.ids import new_id

_HIGH_RISK_LEVELS = {"high", "critical"}


class WorkerCareService:
    def __init__(self, db: Session, runtime_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = runtime_settings or default_settings
        self.template = TemplateTextProvider()

    def chat(self, project_id: str, question: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            raise ForbiddenError("无权访问该项目")
        try:
            provider = build_retrieval_provider(self.settings)
            hits = provider.search(question, {}, top_k=3)
        except AppError:
            hits = []
        if hits:
            answer, answer_source, is_simulated = self._rag_answer(hits)
            citations = [
                {
                    "source": str(hit.get("source", "")),
                    "article": str(hit.get("article", "")),
                    "title": str(hit.get("title", "")),
                    "score": float(hit.get("score", 0.0)),
                }
                for hit in hits
            ]
        else:
            answer = self.template.generate_worker_message(
                {"risk_level": "medium", "hazard_name": question, "requirements": ["先确认作业区域和个人防护用品符合要求"]}
            )
            answer_source = "template"
            is_simulated = True
            citations = []
        message = WorkerMessage(id=new_id("MSG"), project_id=project_id, user_id=actor.id, question=question, answer=answer, answer_source=answer_source, is_simulated=is_simulated)
        self.db.add(message)
        self.db.commit()
        return {"id": message.id, "question": question, "answer": answer, "answer_source": answer_source, "is_simulated": is_simulated, "citations": citations, "created_at": message.created_at.isoformat()}

    def _rag_answer(self, hits: list[dict[str, object]]) -> tuple[str, str, bool]:
        """把检索到的规范条款转成简短工友友好提醒：内嵌《来源·条款》，高风险项提示暂停作业。"""
        top = hits[0]
        source = f"《{top.get('source', '')}》{top.get('article', '') or ''}"
        requirement = str(top.get("content", ""))
        metadata = top.get("metadata")
        hazard_types = [str(item) for item in metadata.get("hazard_types", [])] if isinstance(metadata, dict) else []
        high_risk = any(
            isinstance(RISK_RULES.get(item), dict) and RISK_RULES[item].get("risk_level") in _HIGH_RISK_LEVELS
            for item in hazard_types
        )
        if high_risk:
            return f"师傅，按{source}：{requirement}。这是高风险项，请先暂停作业，待安全员确认后再继续施工。", "rag", False
        return f"师傅，按{source}：{requirement}。请按要求完成整改，完成后请联系安全员复查。", "rag", False

    def transcribe(self, project_id: str, audio_bytes: bytes, mime: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            raise ForbiddenError("无权访问该项目")
        try:
            provider = build_speech_provider(self.settings)
        except AppError as exc:
            return {"available": False, "reason": str(exc), "text": "", "provider": self.settings.speech_provider}
        text = provider.transcribe(audio_bytes, mime)
        return {"available": True, "reason": None, "text": text, "provider": provider.name}

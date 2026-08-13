from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError, ForbiddenError
from app.models import ProjectMember, User, WorkerMessage
from app.providers.factory import build_retrieval_provider, build_speech_provider, build_text_provider
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
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == actor.id,
        ).first():
            raise ForbiddenError("无权访问该项目")

        try:
            provider = build_retrieval_provider(self.settings)
            hits = provider.search(question, {}, top_k=3)
        except AppError:
            hits = []

        citations = [
            {
                "source": str(hit.get("source", "")),
                "article": str(hit.get("article", "")),
                "title": str(hit.get("title", "")),
                "score": float(hit.get("score", 0.0)),
            }
            for hit in hits
        ]

        if hits:
            answer, answer_source, is_simulated = self._grounded_answer(question, hits)
        else:
            answer, answer_source, is_simulated = self._ungrounded_answer(question)

        message = WorkerMessage(
            id=new_id("MSG"),
            project_id=project_id,
            user_id=actor.id,
            question=question,
            answer=answer,
            answer_source=answer_source,
            is_simulated=is_simulated,
        )
        self.db.add(message)
        self.db.commit()
        return {
            "id": message.id,
            "question": question,
            "answer": answer,
            "answer_source": answer_source,
            "is_simulated": is_simulated,
            "citations": citations,
            "created_at": message.created_at.isoformat(),
        }

    def _llm_ready(self) -> bool:
        """文本 LLM 是否可用（OpenAI 兼容 + 三件套齐备），复用 /knowledge/chat 的判断。"""
        return (
            self.settings.text_provider == "openai_compatible"
            and bool(self.settings.llm_base_url)
            and bool(self.settings.llm_api_key)
            and bool(self.settings.llm_model)
        )

    def _grounded_answer(self, question: str, hits: list[dict[str, object]]) -> tuple[str, str, bool]:
        """检索 + LLM 自然回答；LLM 未配置或失败时降级到规则模板。"""
        if self._llm_ready():
            try:
                text_provider = build_text_provider(self.settings)
                clauses = [
                    {
                        "source": str(hit.get("source", "")),
                        "article": str(hit.get("article", "")),
                        "content": str(hit.get("content", "")),
                    }
                    for hit in hits
                ]
                answer = str(text_provider.generate_worker_answer({"question": question, "clauses": clauses})).strip()
                if answer:
                    return answer, "rag_llm", False
            except Exception:
                pass
        return self._rag_answer(hits)

    def _ungrounded_answer(self, question: str) -> tuple[str, str, bool]:
        """未检索到条款：LLM 可用则给一般性安全建议，否则诚实提示不编造规范。"""
        if self._llm_ready():
            try:
                text_provider = build_text_provider(self.settings)
                answer = str(text_provider.generate_worker_answer({"question": question, "clauses": []})).strip()
                if answer:
                    return answer, "llm_general", True
            except Exception:
                pass
        answer = self.template.generate_worker_message(
            {
                "risk_level": "medium",
                "hazard_name": question,
                "requirements": ["先确认作业区域和个人防护用品符合要求"],
            }
        )
        return answer, "template", True

    def _rag_answer(self, hits: list[dict[str, object]]) -> tuple[str, str, bool]:
        """离线兜底：把检索到的规范条款转成简短工友友好提醒，内嵌《来源·条款》。"""
        top = hits[0]
        source = f"《{top.get('source', '')}》{top.get('article') or ''}"
        requirement = str(top.get("content", "")).strip().rstrip("。")
        metadata = top.get("metadata")
        hazard_types = [str(item) for item in metadata.get("hazard_types", [])] if isinstance(metadata, dict) else []
        high_risk = any(
            isinstance(RISK_RULES.get(item), dict)
            and RISK_RULES[item].get("risk_level") in _HIGH_RISK_LEVELS
            for item in hazard_types
        )
        if high_risk:
            return (
                f"师傅，按{source}：{requirement}。这是高风险事项，请先暂停作业，待安全员确认后再继续施工。",
                "rag",
                False,
            )
        return f"师傅，按{source}：{requirement}。请按要求完成整改，完成后联系安全员复查。", "rag", False

    def transcribe(self, project_id: str, audio_bytes: bytes, mime: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == actor.id,
        ).first():
            raise ForbiddenError("无权访问该项目")
        try:
            provider = build_speech_provider(self.settings)
        except AppError as exc:
            return {
                "available": False,
                "reason": str(exc),
                "text": "",
                "provider": self.settings.speech_provider,
            }
        text = provider.transcribe(audio_bytes, mime)
        return {"available": True, "reason": None, "text": text, "provider": provider.name}

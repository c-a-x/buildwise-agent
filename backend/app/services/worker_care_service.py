from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, settings as default_settings
from app.core.exceptions import AppError, ForbiddenError
from app.models import ProjectMember, User, WorkerMessage
from app.providers.factory import build_speech_provider
from app.providers.text.template import TemplateTextProvider
from app.utils.ids import new_id


class WorkerCareService:
    def __init__(self, db: Session, runtime_settings: Settings | None = None) -> None:
        self.db = db
        self.settings = runtime_settings or default_settings
        self.provider = TemplateTextProvider()

    def chat(self, project_id: str, question: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            raise ForbiddenError("无权访问该项目")
        answer = self.provider.generate_worker_message({"risk_level": "medium", "hazard_name": question, "requirements": ["先确认作业区域和个人防护用品符合要求"]})
        message = WorkerMessage(id=new_id("MSG"), project_id=project_id, user_id=actor.id, question=question, answer=answer, answer_source="template", is_simulated=True)
        self.db.add(message)
        self.db.commit()
        return {"id": message.id, "question": question, "answer": answer, "answer_source": "template", "is_simulated": True, "created_at": message.created_at.isoformat()}

    def transcribe(self, project_id: str, audio_bytes: bytes, mime: str, actor: User) -> dict[str, object]:
        if actor.role != "admin" and not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first():
            raise ForbiddenError("无权访问该项目")
        try:
            provider = build_speech_provider(self.settings)
        except AppError as exc:
            return {"available": False, "reason": str(exc), "text": "", "provider": self.settings.speech_provider}
        text = provider.transcribe(audio_bytes, mime)
        return {"available": True, "reason": None, "text": text, "provider": provider.name}

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.services.worker_care_service import WorkerCareService

_WORKER_CARE_ROLES = ("admin", "project_manager", "safety_officer", "worker")


class ChatRequest(BaseModel):
    project_id: str
    question: str = Field(min_length=1, max_length=500)


router = APIRouter(prefix="/worker-care", tags=["工友助手"])


@router.post("/chat")
def chat(request: ChatRequest, http_request: Request, user: User = Depends(require_roles(*_WORKER_CARE_ROLES)), db: Session = Depends(get_db)):
    data = WorkerCareService(db).chat(request.project_id, request.question, user)
    return ok(data, http_request, "已生成模板回答")


@router.post("/transcribe")
def transcribe(
    http_request: Request,
    project_id: str = Form(...),
    audio: UploadFile = File(...),
    user: User = Depends(require_roles(*_WORKER_CARE_ROLES)),
    db: Session = Depends(get_db),
):
    data = WorkerCareService(db).transcribe(project_id, audio.file.read(), audio.content_type or "audio/webm", user)
    return ok(data, http_request, "语音转写完成" if data["available"] else "语音转写未配置")

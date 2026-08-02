from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models import User
from app.services.worker_care_service import WorkerCareService


class ChatRequest(BaseModel):
    project_id: str
    question: str = Field(min_length=1, max_length=500)


class TranscribeRequest(BaseModel):
    project_id: str


router = APIRouter(prefix="/worker-care", tags=["工友助手"])


@router.post("/chat")
def chat(request: ChatRequest, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = WorkerCareService(db).chat(request.project_id, request.question, user)
    return ok(data, http_request, "已生成模板回答")


@router.post("/transcribe")
def transcribe(request: TranscribeRequest, http_request: Request, user: User = Depends(get_current_user)):
    raise AppError("语音转写将在后续版本接入", "MODULE_NOT_IMPLEMENTED", 501)

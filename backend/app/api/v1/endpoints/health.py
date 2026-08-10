from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.response import ok
from app.core.config import settings
from app.db.session import get_db
from app.services.runtime_service import RuntimeService, provider_capabilities


router = APIRouter(tags=["系统"])


@router.get("/health")
def health(http_request: Request, db: Session = Depends(get_db)):
    runtime = RuntimeService(db)
    database = runtime.database_status()
    return ok({"status": "ok", "app": settings.app_name, "environment": settings.app_env, "providers": {"vision": settings.vision_provider, "retrieval": settings.retrieval_provider, "text": settings.text_provider}, "capabilities": provider_capabilities(settings), "database": database}, http_request)

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeDocumentRead, KnowledgeSearchResult
from app.services.knowledge_service import KnowledgeService, document_payload


router = APIRouter(prefix="/knowledge", tags=["知识库"])


@router.get("/documents")
def documents(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok([KnowledgeDocumentRead.model_validate(document_payload(item)).model_dump() for item in KnowledgeService(db).list()], http_request)


@router.get("/search")
def search(http_request: Request, q: str = Query(""), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = KnowledgeService(db)
    results = service.search(q)
    if not q.strip():
        return ok([KnowledgeDocumentRead.model_validate(item).model_dump() for item in results], http_request)
    return ok([KnowledgeSearchResult.model_validate(item).model_dump() for item in results], http_request)


@router.post("/documents")
def create(request: KnowledgeDocumentCreate, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = KnowledgeService(db).create(request, user)
    return ok(KnowledgeDocumentRead.model_validate(document_payload(item)).model_dump(), http_request, "规范文档已加入知识库")


@router.post("/reindex")
def reindex(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(KnowledgeService(db).reindex(), http_request, "知识库索引已重建")


@router.get("/index/status")
def index_status(http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(KnowledgeService(db).index_status(), http_request)

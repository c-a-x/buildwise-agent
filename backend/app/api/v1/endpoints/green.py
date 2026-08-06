from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.providers.carbon import reference_library
from app.schemas.green import GreenAnalyzeForm, GreenReference, ReferenceGroupRead, ReferenceMetricRead
from app.services.carbon_service import CarbonService
from app.services.project_service import ProjectService


router = APIRouter(prefix="/green", tags=["绿色建造"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(get_current_user)):
    return ok({"key": "green", "name": "绿色建造分析", "agent_name": "GreenAgent", "status": "available", "description": "碳排核算核心：GB/T 51366-2019 因子法计算施工阶段 A1-A3/A4/A5 分阶段碳排放。", "planned_inputs": ["材料清单与用量", "运输记录", "施工能耗"], "planned_outputs": ["阶段碳排统计", "面积强度", "减排建议", "报告预览"], "available_endpoints": ["POST /api/v1/green/analyze", "GET /api/v1/green/analyses", "GET /api/v1/green/factors", "GET /api/v1/green/reference"]}, http_request)


@router.post("/analyze")
def analyze(form: GreenAnalyzeForm, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = CarbonService(db).analyze(project_id=form.project_id, area_m2=form.area_m2, scope=form.scope, materials=form.materials, transport=form.transport, energy=form.energy, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "碳排核算完成")


@router.get("/analyses")
def list_analyses(http_request: Request, project_id: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
        return ok([item.model_dump(mode="json") for item in CarbonService(db).list_analyses(project_id)], http_request)
    project_ids = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    result = []
    service = CarbonService(db)
    for visible_project_id in project_ids:
        result.extend([item.model_dump(mode="json") for item in service.list_analyses(visible_project_id)])
    return ok(result, http_request)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = CarbonService(db).get_analysis(analysis_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/analyses/{analysis_id}/report")
def get_analysis_report(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    body, filename, media_type, project_id = CarbonService(db).get_report(analysis_id)
    ensure_project_access(project_id, user, db)
    return Response(content=body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/benchmark")
def benchmark(http_request: Request, project_id: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
    pool = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    return ok(CarbonService(db).benchmark(pool, current_project_id=project_id).model_dump(mode="json"), http_request)


@router.get("/factors")
def factors(http_request: Request, user: User = Depends(get_current_user)):
    return ok([factor.model_dump(mode="json") for factor in CarbonService.factors()], http_request)


@router.get("/reference")
def reference(http_request: Request, user: User = Depends(get_current_user)):
    """中国建筑等公开披露的真实数据参考库（来源可核验），供对标参考、不参与本项目 z-score。"""
    library = reference_library()
    groups = [
        ReferenceGroupRead(
            category=group.category,
            name=group.name,
            items=[ReferenceMetricRead(**item.__dict__) for item in group.items],
        )
        for group in library.groups
    ]
    payload = GreenReference(version=library.version, updated_at=library.updated_at, source_note=library.source_note, groups=groups)
    return ok(payload.model_dump(mode="json"), http_request)

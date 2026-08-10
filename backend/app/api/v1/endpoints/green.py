from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, require_roles
from app.api.response import ok
from app.db.session import get_db
from app.models import User
from app.providers.carbon import reference_library
from app.schemas.green import GreenAdviceForm, GreenAnalyzeForm, GreenAssessmentForm, GreenEnvRecordForm, GreenReference, GreenTargetForm, ReferenceGroupRead, ReferenceMetricRead
from app.services.carbon_service import CarbonService
from app.services.green_advice_service import GreenAdviceService
from app.services.green_assessment_service import GreenAssessmentService
from app.services.green_env_service import GreenEnvService
from app.services.green_trend_service import GreenTrendService
from app.services.project_service import ProjectService

_GREEN_ROLES = ("admin", "project_manager", "safety_officer")


router = APIRouter(prefix="/green", tags=["绿色建造"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES))):
    return ok({"key": "green", "name": "绿色建造分析", "agent_name": "GreenAgent", "status": "available", "description": "碳排核算核心：GB/T 51366-2019 因子法计算施工阶段 A1-A3/A4/A5 分阶段碳排放。", "planned_inputs": ["材料清单与用量", "运输记录", "施工能耗"], "planned_outputs": ["阶段碳排统计", "面积强度", "减排建议", "报告预览"], "available_endpoints": ["POST /api/v1/green/analyze", "GET /api/v1/green/analyses", "GET /api/v1/green/factors", "GET /api/v1/green/reference"]}, http_request)


@router.post("/analyze")
def analyze(form: GreenAnalyzeForm, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = CarbonService(db).analyze(project_id=form.project_id, area_m2=form.area_m2, scope=form.scope, materials=form.materials, transport=form.transport, energy=form.energy, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "碳排核算完成")


@router.get("/analyses")
def list_analyses(http_request: Request, project_id: str | None = Query(None), user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
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
def get_analysis(analysis_id: str, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    data = CarbonService(db).get_analysis(analysis_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/analyses/{analysis_id}/report")
def get_analysis_report(analysis_id: str, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    body, filename, media_type, project_id = CarbonService(db).get_report(analysis_id)
    ensure_project_access(project_id, user, db)
    return Response(content=body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/benchmark")
def benchmark(http_request: Request, project_id: str | None = Query(None), user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
    pool = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    return ok(CarbonService(db).benchmark(pool, current_project_id=project_id).model_dump(mode="json"), http_request)


@router.get("/factors")
def factors(http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES))):
    return ok([factor.model_dump(mode="json") for factor in CarbonService.factors()], http_request)


@router.get("/reference")
def reference(http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES))):
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


# ---------- 四节一环保评估 ----------


@router.post("/assessments")
def create_assessment(form: GreenAssessmentForm, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = GreenAssessmentService(db).evaluate(form=form, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "四节一环保评估完成")


@router.get("/assessments")
def list_assessments(http_request: Request, project_id: str | None = Query(None), user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
        return ok([item.model_dump(mode="json") for item in GreenAssessmentService(db).list_assessments(project_id)], http_request)
    project_ids = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    result = []
    service = GreenAssessmentService(db)
    for visible_project_id in project_ids:
        result.extend([item.model_dump(mode="json") for item in service.list_assessments(visible_project_id)])
    return ok(result, http_request)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    data = GreenAssessmentService(db).get_assessment(assessment_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/assessments/{assessment_id}/report")
def get_assessment_report(assessment_id: str, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    body, filename, media_type, project_id = GreenAssessmentService(db).get_report(assessment_id)
    ensure_project_access(project_id, user, db)
    return Response(content=body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------- 环保监测台账 ----------


@router.get("/env-records/thresholds")
def env_thresholds(http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES))):
    return ok([item.model_dump(mode="json") for item in GreenEnvService.thresholds()], http_request)


@router.post("/env-records")
def upsert_env_record(form: GreenEnvRecordForm, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = GreenEnvService(db).upsert_record(form=form, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "环保监测记录已保存" + ("，存在超标项" if data.has_alerts else ""))


@router.get("/env-records")
def list_env_records(
    http_request: Request,
    project_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    alert_only: bool = Query(False),
    user: User = Depends(require_roles(*_GREEN_ROLES)),
    db: Session = Depends(get_db),
):
    if project_id:
        ensure_project_access(project_id, user, db)
    return ok(
        [item.model_dump(mode="json") for item in GreenEnvService(db).list_records(project_id=project_id, start_date=start_date, end_date=end_date, alert_only=alert_only)],
        http_request,
    )


@router.get("/env-records/{record_id}")
def get_env_record(record_id: str, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    data = GreenEnvService(db).get_record(record_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)


# ---------- 碳排趋势与目标 ----------


@router.get("/trend")
def trend(http_request: Request, project_id: str, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(project_id, user, db)
    data = GreenTrendService(db).trend(project_id)
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/target")
def get_target(http_request: Request, project_id: str, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(project_id, user, db)
    data = GreenTrendService(db).get_target(project_id)
    return ok(data.model_dump(mode="json"), http_request)


@router.put("/target")
def set_target(form: GreenTargetForm, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = GreenTrendService(db).set_target(form=form, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "碳排强度目标已保存")


# ---------- AI 优化建议 ----------


@router.post("/advice")
def generate_advice(form: GreenAdviceForm, http_request: Request, user: User = Depends(require_roles(*_GREEN_ROLES)), db: Session = Depends(get_db)):
    ensure_project_access(form.project_id, user, db)
    data = GreenAdviceService(db).generate(form)
    return ok(data.model_dump(mode="json"), http_request, "绿色施工优化建议已生成")

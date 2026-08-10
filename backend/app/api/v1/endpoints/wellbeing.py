from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user
from app.api.response import ok
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.schemas.wellbeing import WellbeingAnalyzeForm, WeatherSourceRead
from app.services import care_scheduler
from app.services.broadcast_service import broadcast_text_alert
from app.services.project_service import ProjectService
from app.services.wellbeing_service import WellbeingService, broadcast_message


router = APIRouter(prefix="/care", tags=["工友关怀"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(get_current_user)):
    schedule_city = settings.care_schedule_city or settings.weather_city
    last = care_scheduler.last_run
    return ok(
        {
            "key": "care",
            "name": "工友关怀",
            "agent_name": "CareAgent",
            "status": "available",
            "description": "天气/环境输入 → 高温分级 + 中暑风险 + 温馨提醒，为工友幸福服务。",
            "planned_inputs": ["温度", "湿度", "天气现象", "现场说明"],
            "planned_outputs": ["高温等级", "中暑风险指数", "作业限制", "温馨提醒", "急救知识", "福利设施"],
            "available_endpoints": [
                "POST /api/v1/care/analyze",
                "GET /api/v1/care/records",
                "GET /api/v1/care/weather",
                "GET /api/v1/care/tips",
                "GET /api/v1/care/cities",
            ],
            "schedule": {
                "enabled": settings.care_schedule_enabled,
                "time": settings.care_schedule_time,
                "city": schedule_city,
                "last_run_at": f"{last.get('date', '')} {last.get('time', '')}".strip() or None,
                "last_result": last.get("reason") or (f"{last.get('heat_level')} 高温预警" if last.get("heat_level") else None),
            },
        },
        http_request,
    )


@router.post("/analyze")
def analyze(
    form: WellbeingAnalyzeForm,
    http_request: Request,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """工友关怀分析：手动输入天气/环境 → 高温等级 + 中暑风险 + 温馨提醒。红色高温联动语音广播。"""
    ensure_project_access(form.project_id, user, db)
    data = WellbeingService(db).analyze(
        project_id=form.project_id,
        temperature_c=form.temperature_c,
        humidity_pct=form.humidity_pct,
        condition=form.condition,
        description=form.description,
        requested_by=user.id,
        weather_source=WeatherSourceRead(city=form.city, provider=None, observed_at=None) if form.city else None,
    )
    # 高温达到播报档位（默认红色）且配置了 webhook 时，后台推送关怀播报到网络音响/PA，失败静默不阻塞
    if data.broadcast and settings.broadcast_webhook_url:
        background_tasks.add_task(broadcast_text_alert, broadcast_message(data), settings)
        data.broadcast = True
    else:
        data.broadcast = False
    return ok(data.model_dump(mode="json"), http_request, "关怀分析完成")


@router.get("/records")
def list_records(
    http_request: Request,
    project_id: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if project_id:
        ensure_project_access(project_id, user, db)
        return ok([item.model_dump(mode="json") for item in WellbeingService(db).list_records(project_id)], http_request)
    project_ids = [project.id for project in ProjectService(db).list_for_user(user.id, user.role)]
    result = []
    service = WellbeingService(db)
    for visible_project_id in project_ids:
        result.extend([item.model_dump(mode="json") for item in service.list_records(visible_project_id)])
    return ok(result, http_request)


@router.get("/records/{record_id}")
def get_record(record_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = WellbeingService(db).get_record(record_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/weather")
def weather(http_request: Request, city: str | None = Query(None), user: User = Depends(get_current_user)):
    """实时天气查询（可选）：未配置天气 API 时返回 available=false，前端回退手动输入。"""
    data = WellbeingService(db=None, runtime_settings=settings).weather(city)  # weather() 不访问数据库
    return ok(data.model_dump(mode="json"), http_request)


@router.get("/cities")
def cities(http_request: Request, user: User = Depends(get_current_user)):
    """城市下拉候选（实时天气联动）：qweather 内置中文城市 + 配置的 WEATHER_CITY。"""
    return ok({"cities": [item.model_dump(mode="json") for item in WellbeingService(None).cities()]}, http_request)


@router.get("/tips")
def tips(http_request: Request, user: User = Depends(get_current_user)):
    return ok(WellbeingService(None).tips().model_dump(mode="json"), http_request)

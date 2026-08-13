import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, require_roles
from app.api.response import ok
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.providers.vision.mapping import compute_risk_level
from app.providers.vision.yolo import YOLODetector, last_error
from app.schemas.safety import DetectFrameHazard, DetectFrameResponse
from app.services.alert_service import notify_hard_alert
from app.services.broadcast_service import broadcast_voice_alert, send_test_broadcast
from app.services.safety_service import SafetyService
from app.utils.files import validate_upload
from app.utils.ids import new_id


router = APIRouter(prefix="/safety", tags=["安全分析"])

_SAFETY_ROLES = ("admin", "project_manager", "safety_officer")
_SAFETY_VIEW_ROLES = ("admin", "project_manager", "safety_officer", "quality_inspector")


@router.post("/detect-frame")
def detect_frame(
    http_request: Request,
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(require_roles(*_SAFETY_ROLES)),
):
    """实时单帧检测：只跑 YOLO，不落库、不建工单、不跑 LLM。

    供实时监控页轮询；未配置 YOLO 模型时返回 available=false 而非 500。
    """
    content = image.file.read()
    suffix = validate_upload(image.content_type, len(content), settings.max_upload_mb)
    detector = YOLODetector(str(settings.yolo_model_path), settings.yolo_conf_threshold)
    if not detector.available:
        return ok(
            DetectFrameResponse(
                available=False,
                provider="safety_hybrid:yolo",
                is_simulated=True,
                risk_level="normal",
                hazards=[],
                message=f"模型不可用：{last_error()}",
            ).model_dump(mode="json"),
            http_request,
            "实时检测模型不可用",
        )
    # 临时文件写 backend/storage/tmp（ASCII 路径），避免 Windows 中文 TEMP 让 OpenCV 读图失败
    tmp_dir = settings.storage_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"frame-{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(content)
    started = time.perf_counter()
    try:
        raw_hazards = detector.detect(str(tmp_path))
    finally:
        tmp_path.unlink(missing_ok=True)
    latency_ms = int((time.perf_counter() - started) * 1000)
    hazards = [
        DetectFrameHazard(
            id=new_id("HZ"),
            hazard_type=str(item.get("hazard_type", "unknown")),
            hazard_name=str(item.get("hazard_name", "现场隐患")),
            description=str(item.get("description", "")),
            confidence=float(item.get("confidence", 0.0)),
            risk_level=str(item.get("risk_level", "medium")),
            bbox=item.get("bbox"),
            source=item.get("source"),
        )
        for item in raw_hazards
    ]
    risk_level = compute_risk_level(raw_hazards)
    # ESP32 硬报警（预留）：高危且配置了 webhook 时后台通知，默认空禁用
    if risk_level in ("high", "critical"):
        if settings.alert_webhook_url:
            background_tasks.add_task(notify_hard_alert, raw_hazards, settings.alert_webhook_url)
        # 网络音响/PA 语音广播（预留）：高危时后台推送文字 + 可选音频，默认空禁用
        if settings.broadcast_webhook_url:
            background_tasks.add_task(broadcast_voice_alert, raw_hazards, settings)
    return ok(
        DetectFrameResponse(
            available=True,
            provider="safety_hybrid:yolo",
            is_simulated=False,
            risk_level=risk_level,
            hazards=hazards,
            latency_ms=latency_ms,
        ).model_dump(mode="json"),
        http_request,
        "实时检测完成",
    )


@router.post("/broadcast-test")
def broadcast_test(http_request: Request, user: User = Depends(require_roles(*_SAFETY_ROLES))):
    """手动触发一次语音广播测试，返回送达与 TTS 状态，用于接线验证。"""
    result = send_test_broadcast(settings)
    if result["delivered"]:
        return ok(result, http_request, "测试广播已送达")
    return ok(result, http_request, result["reason"] or "测试广播未送达")


@router.post("/analyze")
async def analyze(
    http_request: Request,
    image: UploadFile = File(...),
    project_id: str = Form(...),
    location: str = Form(...),
    work_type: str = Form(...),
    description: str = Form(""),
    demo_scenario: str | None = Form(None),
    user: User = Depends(require_roles(*_SAFETY_ROLES)),
    db: Session = Depends(get_db),
):
    ensure_project_access(project_id, user, db)
    content = await image.read()
    data = SafetyService(db).analyze(image_bytes=content, original_name=image.filename or "upload.jpg", content_type=image.content_type or "", project_id=project_id, location=location, work_type=work_type, description=description, demo_scenario=demo_scenario, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "安全分析完成")


@router.get("/tasks")
def list_tasks(http_request: Request, project_id: str | None = Query(None), user: User = Depends(require_roles(*_SAFETY_VIEW_ROLES)), db: Session = Depends(get_db)):
    if project_id:
        ensure_project_access(project_id, user, db)
    else:
        project_ids = [project.id for project in __import__("app.services.project_service", fromlist=["ProjectService"]).ProjectService(db).list_for_user(user.id, user.role)]
        # The service query accepts an optional project; merge visible tasks for non-admin users.
        result = []
        service = SafetyService(db)
        for visible_project_id in project_ids:
            result.extend(service.list_tasks(visible_project_id))
        return ok(result, http_request)
    return ok(SafetyService(db).list_tasks(project_id), http_request)


@router.get("/tasks/{task_id}")
def get_task(task_id: str, http_request: Request, user: User = Depends(require_roles(*_SAFETY_VIEW_ROLES)), db: Session = Depends(get_db)):
    data = SafetyService(db).get_task(task_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)

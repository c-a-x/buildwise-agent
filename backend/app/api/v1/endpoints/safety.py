import ipaddress
import socket
import time
import urllib.parse
import uuid
from collections.abc import Iterator

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_project_access, get_current_user, get_current_user_query_token
from app.api.response import ok
from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.providers.vision.mapping import compute_risk_level
from app.providers.vision.yolo import YOLODetector, last_error
from app.schemas.safety import DetectFrameHazard, DetectFrameResponse
from app.services.alert_service import notify_hard_alert
from app.services.safety_service import SafetyService
from app.utils.files import validate_upload
from app.utils.ids import new_id


router = APIRouter(prefix="/safety", tags=["安全分析"])


@router.post("/detect-frame")
def detect_frame(
    http_request: Request,
    image: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
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
    if risk_level in ("high", "critical") and settings.alert_webhook_url:
        background_tasks.add_task(notify_hard_alert, raw_hazards, settings.alert_webhook_url)
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


def _is_allowed_proxy_url(url: str) -> bool:
    """只放行本机/内网的 http(s) 视频流地址，防止 SSRF 打到公网或内网探测。"""
    if not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        ip = None
    if ip is not None:
        return ip.is_loopback or ip.is_private
    if hostname in ("localhost", "localhost.localdomain"):
        return True
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or 80)
    except OSError:
        return False
    return any(
        ipaddress.ip_address(info[4][0]).is_loopback or ipaddress.ip_address(info[4][0]).is_private
        for info in infos
    )


@router.get("/mjpeg-proxy")
def mjpeg_proxy(
    http_request: Request,
    url: str = Query(...),
    user: User = Depends(get_current_user_query_token),
):
    """透传 ESP32-CAM 的 MJPG 视频流并补上 CORS 头。

    浏览器 `<img>` 直接加载 ESP32 MJPG 流可显示，但 canvas.toBlob 抓帧会因
    缺 `Access-Control-Allow-Origin` 抛 SecurityError；本代理透传流并返回
    `ACAO: *`，配合前端 `crossorigin="anonymous"` 才能抓帧检测。
    token 走 query（`<img>` 标签带不了 Authorization header），仅本地演示场景。
    """
    if not _is_allowed_proxy_url(url):
        raise HTTPException(status_code=400, detail="仅支持本机/内网的 http(s) 视频流地址")

    def stream() -> Iterator[bytes]:
        try:
            with httpx.stream("GET", url, timeout=httpx.Timeout(30.0, connect=5.0)) as upstream:
                if upstream.status_code != 200:
                    return
                for chunk in upstream.iter_bytes(8192):
                    yield chunk
        except (httpx.HTTPError, OSError):
            return

    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace",
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "no-cache"},
    )


@router.post("/analyze")
async def analyze(
    http_request: Request,
    image: UploadFile = File(...),
    project_id: str = Form(...),
    location: str = Form(...),
    work_type: str = Form(...),
    description: str = Form(""),
    demo_scenario: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ensure_project_access(project_id, user, db)
    content = await image.read()
    data = SafetyService(db).analyze(image_bytes=content, original_name=image.filename or "upload.jpg", content_type=image.content_type or "", project_id=project_id, location=location, work_type=work_type, description=description, demo_scenario=demo_scenario, requested_by=user.id)
    return ok(data.model_dump(mode="json"), http_request, "安全分析完成")


@router.get("/tasks")
def list_tasks(http_request: Request, project_id: str | None = Query(None), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
def get_task(task_id: str, http_request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = SafetyService(db).get_task(task_id)
    ensure_project_access(data.project_id, user, db)
    return ok(data.model_dump(mode="json"), http_request)

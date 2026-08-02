from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.exceptions import AppError
from app.models import User


router = APIRouter(prefix="/quality", tags=["质量巡检"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(get_current_user)):
    return ok({"key": "quality", "name": "工程质量巡检", "agent_name": "QualityAgent", "status": "planned", "description": "质量缺陷识别、分部分项验收和复检闭环正在规划中。", "planned_inputs": ["质量巡检图片", "验收记录"], "planned_outputs": ["缺陷清单", "复检任务"], "available_endpoints": ["GET /api/v1/quality/status"]}, http_request)


@router.post("/analyze")
def analyze(http_request: Request, user: User = Depends(get_current_user)):
    raise AppError("质量分析模块尚未实现", "MODULE_NOT_IMPLEMENTED", 501)

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_current_user
from app.api.response import ok
from app.core.exceptions import AppError
from app.models import User


router = APIRouter(prefix="/green", tags=["绿色建造"])


@router.get("/status")
def status(http_request: Request, user: User = Depends(get_current_user)):
    return ok({"key": "green", "name": "绿色建造分析", "agent_name": "GreenAgent", "status": "planned", "description": "材料清单、碳排估算和绿色施工建议正在规划中。", "planned_inputs": ["材料清单", "机械能耗", "运输记录"], "planned_outputs": ["碳排统计", "减排建议"], "available_endpoints": ["GET /api/v1/green/status"]}, http_request)


@router.post("/analyze")
def analyze(http_request: Request, user: User = Depends(get_current_user)):
    raise AppError("绿色建造分析模块尚未实现", "MODULE_NOT_IMPLEMENTED", 501)

from fastapi import APIRouter, Request

from app.api.response import ok
from app.core.config import settings


router = APIRouter(tags=["系统"])


@router.get("/health")
def health(http_request: Request):
    return ok({"status": "ok", "app": settings.app_name, "environment": settings.app_env, "providers": {"vision": settings.vision_provider, "retrieval": settings.retrieval_provider, "text": settings.text_provider}}, http_request)


@router.get("/modules")
def modules(http_request: Request):
    return ok([
        {"key": "safety", "name": "现场安全分析", "agent_name": "SafetyAgent → ReportAgent", "status": "available", "description": "离线五节点安全闭环。", "planned_inputs": ["现场图片", "位置", "作业类型"], "planned_outputs": ["隐患", "依据", "工单草稿", "日报预览"], "available_endpoints": ["POST /api/v1/safety/analyze"]},
        {"key": "quality", "name": "工程质量巡检", "agent_name": "QualityAgent", "status": "planned", "description": "占位模块。", "planned_inputs": ["巡检图片"], "planned_outputs": ["缺陷清单"], "available_endpoints": ["GET /api/v1/quality/status"]},
        {"key": "green", "name": "绿色建造分析", "agent_name": "GreenAgent", "status": "planned", "description": "占位模块。", "planned_inputs": ["材料清单"], "planned_outputs": ["碳排统计"], "available_endpoints": ["GET /api/v1/green/status"]},
    ], http_request)

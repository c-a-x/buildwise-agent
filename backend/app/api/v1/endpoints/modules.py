from fastapi import APIRouter, Request

from app.api.response import ok


router = APIRouter(tags=["系统"])


@router.get("/modules")
def modules(http_request: Request):
    return ok(
        [
            {
                "key": "safety",
                "name": "现场安全分析",
                "agent_name": "SafetyAgent → ReportAgent",
                "status": "available",
                "description": "离线五节点安全闭环。",
                "planned_inputs": ["现场图片", "位置", "作业类型"],
                "planned_outputs": ["隐患", "依据", "工单草稿", "日报预览"],
                "available_endpoints": ["POST /api/v1/safety/analyze"],
            },
            {
                "key": "quality",
                "name": "工程质量巡检",
                "agent_name": "QualityAgent → ReportAgent",
                "status": "available",
                "description": "离线五节点质量闭环（裂缝/渗漏/剥落/锈蚀/鼓包）。",
                "planned_inputs": ["巡检图片", "位置", "作业类型"],
                "planned_outputs": ["缺陷", "依据", "工单草稿", "日报预览"],
                "available_endpoints": ["POST /api/v1/quality/analyze", "GET /api/v1/quality/tasks"],
            },
            {
                "key": "green",
                "name": "绿色建造分析",
                "agent_name": "GreenAgent",
                "status": "available",
                "description": "碳排核算核心（GB/T 51366-2019 因子法）。",
                "planned_inputs": ["材料清单", "运输记录", "施工能耗"],
                "planned_outputs": ["碳排统计", "减排建议"],
                "available_endpoints": ["POST /api/v1/green/analyze", "GET /api/v1/green/analyses", "GET /api/v1/green/factors"],
            },
            {
                "key": "care",
                "name": "工友关怀",
                "agent_name": "CareAgent",
                "status": "available",
                "description": "高温分级 + 中暑风险 + 温馨提醒（《防暑降温措施管理办法》）。",
                "planned_inputs": ["温度", "湿度", "天气现象"],
                "planned_outputs": ["高温等级", "中暑风险指数", "作业限制", "温馨提醒", "急救知识", "福利设施"],
                "available_endpoints": ["POST /api/v1/care/analyze", "GET /api/v1/care/records", "GET /api/v1/care/weather", "GET /api/v1/care/tips"],
            },
        ],
        http_request,
    )


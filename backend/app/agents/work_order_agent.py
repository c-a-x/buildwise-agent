from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.workflow.state import WorkflowState


RULES: dict[str, dict[str, object]] = {
    "no_helmet": {"assignee_role": "safety_officer", "deadline_hours": 4, "requirements": ["正确佩戴安全帽并扣紧下颌带"]},
    "missing_guardrail": {"assignee_role": "project_manager", "deadline_hours": 2, "requirements": ["立即设置连续稳固的临边防护栏杆和挡脚板"]},
    "no_safety_vest": {"assignee_role": "safety_officer", "deadline_hours": 24, "requirements": ["穿戴符合要求的反光安全背心"]},
}


class WorkOrderAgent:
    name = "WorkOrderAgent"

    def run(self, state: WorkflowState) -> dict[str, object]:
        hazard = (state.get("hazards") or [{}])[0]
        rule = RULES.get(str(hazard.get("hazard_type", "")), {"assignee_role": "safety_officer", "deadline_hours": 24, "requirements": ["按安全员要求完成整改"]})
        now = datetime.now(timezone.utc)
        requirements = [str(item) for item in rule.get("requirements", [])]
        risk_level = str(hazard.get("risk_level", state.get("risk_level", "medium")))
        draft = {
            "task_id": state.get("task_id", ""),
            "incident_id": "",
            "title": f"整改：{hazard.get('hazard_name', '现场安全隐患')}",
            "problem_description": str(hazard.get("description", "请根据现场情况完成整改")),
            "risk_level": risk_level,
            "location": state.get("location", ""),
            "deadline": (now + timedelta(hours=int(rule.get("deadline_hours", 24)))).isoformat(),
            "assignee_role": str(rule.get("assignee_role", "safety_officer")),
            "rectification_requirements": requirements,
            "review_requirements": ["整改完成后上传现场照片并由安全员复查"],
            "worker_message": "",
            "ai_generated": True,
            "confirmed_by_human": False,
            "review_required": True,
            "is_simulated": True,
        }
        trace = {
            "agent": self.name,
            "status": "completed",
            "message": "已生成待人工确认的工单草稿",
            "started_at": now.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 3,
        }
        return {"work_order_draft": draft, "agent_trace": [trace]}

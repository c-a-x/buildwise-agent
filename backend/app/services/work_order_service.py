from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.models import AgentRun, AuditLog, Incident, IncidentEvidence, Project, ProjectMember, Upload, User, WorkOrder, WorkOrderEvent
from app.repositories.work_order_repository import WorkOrderRepository
from app.schemas.work_order import WorkOrderCreate, WorkOrderStatusUpdate
from app.utils.ids import new_id


ALLOWED_MUTATORS = {"admin", "project_manager", "safety_officer", "quality_inspector"}
VALID_TRANSITIONS = {
    "pending": {"in_progress"},
    "in_progress": {"pending_review"},
    "pending_review": {"in_progress", "closed"},
    "closed": set(),
}


class WorkOrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = WorkOrderRepository(db)

    def create(self, request: WorkOrderCreate, actor: User, ip_address: str | None = None) -> WorkOrder:
        if actor.role not in ALLOWED_MUTATORS:
            raise ForbiddenError("当前角色不能确认或创建工单")
        task = self.db.get(AgentRun, request.task_id)
        if not task or task.status != "completed":
            raise NotFoundError("分析任务不存在或尚未完成", "SAFETY_TASK_NOT_FOUND")
        self._ensure_project_access(task.project_id, actor)
        if not request.confirm_ai_draft:
            raise AppError("必须先确认 AI 工单草稿", "WORK_ORDER_DRAFT_NOT_CONFIRMED", 400)
        incident = self.db.query(Incident).filter(Incident.agent_run_id == task.id).first()
        if not incident:
            raise AppError("该分析没有可创建工单的隐患", "WORK_ORDER_NO_INCIDENT", 400)
        existing = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.incident_id == incident.id, WorkOrder.status != "closed")
            .first()
        )
        if existing:
            return existing
        # 人工确认的是 AI 工单草稿本身：优先采用草稿内容（质量/安全语义均由对应
        # WorkOrderAgent 规则生成），草稿缺失时才回退到安全侧兜底规则。
        result_json = task.result_json if isinstance(task.result_json, dict) else {}
        draft = result_json.get("work_order_draft") if isinstance(result_json.get("work_order_draft"), dict) else {}
        assignee = self._resolve_assignee(task.project_id, request.assignee_user_id, actor)
        deadline = request.deadline or self._default_deadline(incident.risk_level)
        requirements = draft.get("rectification_requirements") or self._requirements(incident.hazard_type)
        review_requirements = draft.get("review_requirements") or ["整改完成后上传现场照片并由安全员复查"]
        worker_message = draft.get("worker_message") or result_json.get("worker_message") or self._worker_message(incident.risk_level, incident.hazard_name, requirements)
        order = WorkOrder(
            id=new_id("WO"),
            project_id=task.project_id,
            incident_id=incident.id,
            source_task_id=task.id,
            title=f"整改：{incident.hazard_name}",
            problem_description=incident.description,
            risk_level=incident.risk_level,
            location=task.location,
            assignee_user_id=assignee.id,
            created_by=actor.id,
            deadline=deadline,
            status="pending",
            rectification_requirements_json=requirements,
            review_requirements_json=review_requirements,
            worker_message=worker_message,
            ai_generated=True,
            confirmed_by_human=True,
        )
        self.db.add(order)
        self.db.flush()
        self.db.add(WorkOrderEvent(id=new_id("WEO"), work_order_id=order.id, actor_user_id=actor.id, event_type="created", from_status=None, to_status="pending", note="人工确认 AI 工单草稿"))
        self.db.add(AuditLog(id=new_id("AUD"), user_id=actor.id, action="confirm_work_order", resource_type="work_order", resource_id=order.id, detail_json={"task_id": task.id}, ip_address=ip_address))
        self.db.commit()
        return order

    def list(
        self,
        actor: User,
        project_id: str | None = None,
        status: str | None = None,
        risk_level: str | None = None,
        assignee_user_id: str | None = None,
        deadline_from: datetime | None = None,
        deadline_to: datetime | None = None,
    ) -> list[WorkOrder]:
        project_ids = self._accessible_project_ids(actor)
        query = self.db.query(WorkOrder)
        if project_id:
            if project_id not in project_ids and actor.role != "admin":
                raise ForbiddenError("无权访问该项目")
            query = query.filter(WorkOrder.project_id == project_id)
        elif actor.role != "admin":
            query = query.filter(WorkOrder.project_id.in_(project_ids or ["__none__"]))
        if status:
            query = query.filter(WorkOrder.status == status)
        if risk_level:
            query = query.filter(WorkOrder.risk_level == risk_level)
        if assignee_user_id:
            query = query.filter(WorkOrder.assignee_user_id == assignee_user_id)
        if deadline_from:
            query = query.filter(WorkOrder.deadline >= deadline_from)
        if deadline_to:
            query = query.filter(WorkOrder.deadline <= deadline_to)
        return query.order_by(WorkOrder.deadline.asc()).all()

    def get(self, order_id: str, actor: User) -> WorkOrder:
        order = self.orders.get(order_id)
        if not order:
            raise NotFoundError("工单不存在", "WORK_ORDER_NOT_FOUND")
        self._ensure_project_access(order.project_id, actor)
        return order

    def update_status(self, order_id: str, request: WorkOrderStatusUpdate, actor: User, ip_address: str | None = None) -> WorkOrder:
        if actor.role not in ALLOWED_MUTATORS:
            raise ForbiddenError("当前角色不能变更工单状态")
        order = self.get(order_id, actor)
        allowed = VALID_TRANSITIONS.get(order.status, set())
        if request.status not in allowed:
            raise AppError(f"不允许从 {order.status} 流转到 {request.status}", "WORK_ORDER_INVALID_TRANSITION", 400)
        if request.status == "closed" and not request.note.strip():
            raise AppError("关闭工单必须填写复查备注", "WORK_ORDER_REVIEW_NOTE_REQUIRED", 400)
        old_status = order.status
        order.status = request.status
        if request.status == "closed":
            order.closed_at = datetime.now(timezone.utc)
        self.db.add(WorkOrderEvent(id=new_id("WEO"), work_order_id=order.id, actor_user_id=actor.id, event_type="status_changed", from_status=old_status, to_status=request.status, note=request.note))
        self.db.add(AuditLog(id=new_id("AUD"), user_id=actor.id, action="change_work_order_status", resource_type="work_order", resource_id=order.id, detail_json={"from": old_status, "to": request.status}, ip_address=ip_address))
        self.db.commit()
        return order

    def events(self, order_id: str) -> list[WorkOrderEvent]:
        return self.db.query(WorkOrderEvent).filter(WorkOrderEvent.work_order_id == order_id).order_by(WorkOrderEvent.created_at.asc()).all()

    def serialize(self, order: WorkOrder) -> dict[str, object]:
        incident = self.db.get(Incident, order.incident_id)
        upload = self.db.get(Upload, incident.upload_id) if incident else None
        evidence = self.db.query(IncidentEvidence).filter(IncidentEvidence.incident_id == order.incident_id).all()
        assignee = self.db.get(User, order.assignee_user_id) if order.assignee_user_id else None
        return work_order_dict(order, self.events(order.id), upload, evidence, assignee_name=assignee.real_name if assignee else None)

    def _resolve_assignee(self, project_id: str, assignee_user_id: str | None, actor: User) -> User:
        if assignee_user_id:
            user = self.db.get(User, assignee_user_id)
            if not user:
                raise NotFoundError("责任人不存在", "USER_NOT_FOUND")
            if not self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id).first() and user.role != "admin":
                raise AppError("责任人不是该项目成员", "PROJECT_ACCESS_DENIED", 403)
            return user
        manager_id = self.db.get(Project, project_id).manager_user_id
        return self.db.get(User, manager_id) or actor

    def _ensure_project_access(self, project_id: str, actor: User) -> None:
        if actor.role == "admin":
            return
        member = self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == actor.id).first()
        project = self.db.get(Project, project_id)
        if not project or (not member and project.manager_user_id != actor.id):
            raise ForbiddenError("无权访问该项目")

    def _accessible_project_ids(self, actor: User) -> list[str]:
        if actor.role == "admin":
            return [row.id for row in self.db.query(Project.id).all()]
        managed = [row.id for row in self.db.query(Project.id).filter(Project.manager_user_id == actor.id).all()]
        member = [row.project_id for row in self.db.query(ProjectMember).filter(ProjectMember.user_id == actor.id).all()]
        return list(dict.fromkeys(managed + member))

    @staticmethod
    def _default_deadline(risk_level: str) -> datetime:
        hours = {"critical": 2, "high": 4, "medium": 24, "low": 48, "normal": 72}.get(risk_level, 24)
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    @staticmethod
    def _requirements(hazard_type: str) -> list[str]:
        return {
            "no_helmet": ["正确佩戴安全帽并扣紧下颌带"],
            "missing_guardrail": ["立即设置连续稳固的临边防护栏杆和挡脚板"],
            "no_safety_vest": ["穿戴符合要求的反光安全背心"],
        }.get(hazard_type, ["按安全员要求完成整改"])

    @staticmethod
    def _worker_message(risk_level: str, hazard_name: str, requirements: list[str]) -> str:
        prefix = "师傅，请先暂停作业。" if risk_level in {"high", "critical"} else "师傅，请注意现场安全。"
        return f"{prefix}发现{hazard_name}，{requirements[0]}，完成后请联系安全员复查。"


def work_order_dict(order: WorkOrder, events: list[WorkOrderEvent], upload: Upload | None = None, evidence: list[IncidentEvidence] | None = None, assignee_name: str | None = None) -> dict[str, object]:
    file_url = f"/storage/{upload.relative_path}" if upload else None
    annotated_url = None
    if upload and "." in upload.stored_name:
        stem, suffix = upload.stored_name.rsplit(".", 1)
        annotated_url = f"/storage/annotated/{stem}-annotated.{suffix}"
    return {
        "id": order.id,
        "project_id": order.project_id,
        "incident_id": order.incident_id,
        "source_task_id": order.source_task_id,
        "title": order.title,
        "problem_description": order.problem_description,
        "risk_level": order.risk_level,
        "location": order.location,
        "assignee_user_id": order.assignee_user_id,
        "assignee_name": assignee_name,
        "created_by": order.created_by,
        "deadline": order.deadline,
        "status": order.status,
        "rectification_requirements": order.rectification_requirements_json or [],
        "review_requirements": order.review_requirements_json or [],
        "worker_message": order.worker_message,
        "ai_generated": order.ai_generated,
        "confirmed_by_human": order.confirmed_by_human,
        "closed_at": order.closed_at,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "from_status": event.from_status,
                "to_status": event.to_status,
                "note": event.note,
                "actor_user_id": event.actor_user_id,
                "created_at": event.created_at,
            }
            for event in events
        ],
        "file_url": file_url,
        "annotated_url": annotated_url,
        "evidence": [
            {
                "id": item.id,
                "source": item.source,
                "article": item.article,
                "content": item.content,
                "score": item.score,
            }
            for item in (evidence or [])
        ],
    }

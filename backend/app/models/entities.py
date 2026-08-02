from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db.base import Base
from app.utils.ids import new_id


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: new_id("USR"))
    username = Column(String(32), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, index=True)
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(64), primary_key=True, default=lambda: new_id("PRJ"))
    code = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    address = Column(String(255), nullable=False)
    description = Column(Text, default="", nullable=False)
    status = Column(String(32), default="active", nullable=False)
    manager_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"), Index("ix_project_members_project_user", "project_id", "user_id"))

    id = Column(String(64), primary_key=True, default=lambda: new_id("MEM"))
    project_id = Column(String(64), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_role = Column(String(32), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(String(64), primary_key=True, default=lambda: new_id("UPL"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False, index=True)
    uploaded_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    relative_path = Column(String(512), nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_project_created", "project_id", "created_at"),)

    id = Column(String(64), primary_key=True, default=lambda: new_id("TASK"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    upload_id = Column(String(64), ForeignKey("uploads.id"), nullable=False)
    requested_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    location = Column(String(255), nullable=False)
    work_type = Column(String(128), nullable=False)
    description = Column(Text, default="", nullable=False)
    risk_level = Column(String(32), default="normal", nullable=False)
    status = Column(String(32), default="running", nullable=False)
    is_simulated = Column(Boolean, default=True, nullable=False)
    provider_info_json = Column(JSON, default=dict, nullable=False)
    trace_json = Column(JSON, default=list, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_project_risk_created", "project_id", "risk_level", "created_at"),)

    id = Column(String(64), primary_key=True, default=lambda: new_id("INC"))
    agent_run_id = Column(String(64), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    upload_id = Column(String(64), ForeignKey("uploads.id"), nullable=False)
    hazard_type = Column(String(64), nullable=False)
    hazard_name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_level = Column(String(32), nullable=False)
    bbox_json = Column(JSON, nullable=True)
    review_required = Column(Boolean, default=True, nullable=False)
    reviewed_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class IncidentEvidence(Base):
    __tablename__ = "incident_evidences"

    id = Column(String(64), primary_key=True, default=lambda: new_id("EVD"))
    incident_id = Column(String(64), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(255), nullable=False)
    article = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    score = Column(Float, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (Index("ix_work_orders_project_status_deadline", "project_id", "status", "deadline"),)

    id = Column(String(64), primary_key=True, default=lambda: new_id("WO"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    incident_id = Column(String(64), ForeignKey("incidents.id"), nullable=False)
    source_task_id = Column(String(64), ForeignKey("agent_runs.id"), nullable=False)
    title = Column(String(255), nullable=False)
    problem_description = Column(Text, nullable=False)
    risk_level = Column(String(32), nullable=False)
    location = Column(String(255), nullable=False)
    assignee_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    rectification_requirements_json = Column(JSON, default=list, nullable=False)
    review_requirements_json = Column(JSON, default=list, nullable=False)
    worker_message = Column(Text, default="", nullable=False)
    ai_generated = Column(Boolean, default=True, nullable=False)
    confirmed_by_human = Column(Boolean, default=False, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class WorkOrderEvent(Base):
    __tablename__ = "work_order_events"

    id = Column(String(64), primary_key=True, default=lambda: new_id("WEO"))
    work_order_id = Column(String(64), ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    actor_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=True)
    note = Column(Text, default="", nullable=False)
    attachment_upload_id = Column(String(64), ForeignKey("uploads.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint("project_id", "report_date", name="uq_daily_report_project_date"), Index("ix_daily_reports_project_date", "project_id", "report_date"))

    id = Column(String(64), primary_key=True, default=lambda: new_id("RPT"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    statistics_json = Column(JSON, default=dict, nullable=False)
    content = Column(Text, nullable=False)
    generated_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    is_ai_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class WorkerMessage(Base):
    __tablename__ = "worker_messages"

    id = Column(String(64), primary_key=True, default=lambda: new_id("MSG"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    answer_source = Column(String(64), default="template", nullable=False)
    is_simulated = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(64), primary_key=True, default=lambda: new_id("KNO"))
    title = Column(String(255), nullable=False)
    source = Column(String(255), nullable=False)
    version = Column(String(64), default="MVP", nullable=False)
    category = Column(String(128), nullable=False)
    file_path = Column(String(512), nullable=True)
    status = Column(String(32), default="active", nullable=False)
    content = Column(Text, default="", nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class QualityInspection(Base):
    __tablename__ = "quality_inspections"

    id = Column(String(64), primary_key=True, default=lambda: new_id("QIN"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    upload_id = Column(String(64), ForeignKey("uploads.id"), nullable=True)
    defect_type = Column(String(128), nullable=True)
    severity = Column(String(32), nullable=True)
    result_json = Column(JSON, default=dict, nullable=False)
    status = Column(String(32), default="planned", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class CarbonAnalysis(Base):
    __tablename__ = "carbon_analyses"

    id = Column(String(64), primary_key=True, default=lambda: new_id("CAR"))
    project_id = Column(String(64), ForeignKey("projects.id"), nullable=False)
    source_upload_id = Column(String(64), ForeignKey("uploads.id"), nullable=True)
    total_emission = Column(Float, nullable=True)
    result_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_user_created", "user_id", "created_at"),)

    id = Column(String(64), primary_key=True, default=lambda: new_id("AUD"))
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True)
    detail_json = Column(JSON, default=dict, nullable=False)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

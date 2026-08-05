from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.models import AgentRun, Incident, IncidentEvidence, Upload
from app.schemas.quality import QualityAnalysisResponse
from app.utils.files import save_upload
from app.utils.images import create_annotated_copy
from app.utils.ids import new_id
from app.workflow.graph import build_workflow


class QualityService:
    """质量巡检分析：与 SafetyService 同构，但走 quality 模块五 agent + 独立规范知识库。"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.workflow = build_workflow(settings.quality_knowledge_json_path, settings, module="quality")

    def analyze(
        self,
        *,
        image_bytes: bytes,
        original_name: str,
        content_type: str,
        project_id: str,
        location: str,
        work_type: str,
        description: str,
        demo_scenario: str | None,
        requested_by: str,
    ) -> QualityAnalysisResponse:
        stored_name, sha256, size_bytes = save_upload(
            image_bytes, content_type, settings.upload_dir, settings.max_upload_mb
        )
        upload = Upload(
            id=new_id("UPL"),
            project_id=project_id,
            uploaded_by=requested_by,
            original_name=Path(original_name).name,
            stored_name=stored_name,
            mime_type=content_type,
            size_bytes=size_bytes,
            relative_path=f"uploads/{stored_name}",
            sha256=sha256,
        )
        self.db.add(upload)
        self.db.flush()
        task = AgentRun(
            id=new_id("TASK"),
            module="quality",
            project_id=project_id,
            upload_id=upload.id,
            requested_by=requested_by,
            location=location,
            work_type=work_type,
            description=description,
            status="running",
            is_simulated=True,
        )
        self.db.add(task)
        self.db.flush()
        try:
            physical_path = settings.upload_dir / stored_name
            state = self.workflow.run(
                {
                    "task_id": task.id,
                    "project_id": project_id,
                    "upload_id": upload.id,
                    "image_path": str(physical_path),
                    "location": location,
                    "work_type": work_type,
                    "description": description,
                    "requested_by": requested_by,
                    "demo_scenario": demo_scenario or "crack",
                }
            )
            incidents: list[Incident] = []
            for hazard in state.get("hazards", []):
                incident = Incident(
                    id=new_id("INC"),
                    agent_run_id=task.id,
                    project_id=project_id,
                    upload_id=upload.id,
                    hazard_type=str(hazard.get("hazard_type", "unknown")),
                    hazard_name=str(hazard.get("hazard_name", "质量缺陷")),
                    description=str(hazard.get("description", "")),
                    confidence=float(hazard.get("confidence", 0.0)),
                    risk_level=str(hazard.get("risk_level", state.get("risk_level", "medium"))),
                    bbox_json=hazard.get("bbox"),
                    metadata_json={
                        "module": "quality",
                        "source": hazard.get("source"),
                        "regulation": hazard.get("regulation"),
                        "suggestion": hazard.get("suggestion"),
                        "is_major": hazard.get("is_major"),
                        "major_basis": hazard.get("major_basis"),
                    },
                    review_required=True,
                )
                self.db.add(incident)
                incidents.append(incident)
            self.db.flush()
            evidence = state.get("evidence", [])
            if incidents:
                for item in evidence:
                    self.db.add(
                        IncidentEvidence(
                            id=new_id("EVD"),
                            incident_id=incidents[0].id,
                            source=str(item.get("source", "")),
                            article=str(item.get("article", "")),
                            content=str(item.get("content", "")),
                            score=float(item.get("score", 0.0)),
                            metadata_json=item.get("metadata", {}),
                        )
                    )
            draft = state.get("work_order_draft")
            if isinstance(draft, dict) and incidents:
                draft["incident_id"] = incidents[0].id
            task.result_json = {
                "work_order_draft": draft,
                "worker_message": str(state.get("worker_message", "")),
                "report_preview": str(state.get("report_preview", "")),
            }
            task.risk_level = str(state.get("risk_level", "normal"))
            task.status = "completed"
            task.is_simulated = bool(state.get("is_simulated", True))
            task.provider_info_json = state.get("provider_info", {})
            task.trace_json = state.get("agent_trace", [])
            task.finished_at = datetime.now(timezone.utc)
            self.db.commit()
            annotated_name = f"{Path(stored_name).stem}-annotated{Path(stored_name).suffix}"
            create_annotated_copy(settings.upload_dir / stored_name, settings.annotated_dir, annotated_name)
            return self._response(task, upload, incidents, state, annotated_name)
        except Exception as exc:
            self.db.rollback()
            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = datetime.now(timezone.utc)
            self.db.add(task)
            self.db.commit()
            raise AppError("质量分析执行失败", "QUALITY_ANALYSIS_FAILED", 500) from exc

    def list_tasks(self, project_id: str | None = None) -> list[dict[str, object]]:
        query = self.db.query(AgentRun).filter(AgentRun.module == "quality")
        if project_id:
            query = query.filter(AgentRun.project_id == project_id)
        tasks = query.order_by(AgentRun.created_at.desc()).all()
        return [
            {
                "task_id": task.id,
                "project_id": task.project_id,
                "location": task.location,
                "work_type": task.work_type,
                "risk_level": task.risk_level,
                "status": task.status,
                "incident_count": self.db.query(Incident).filter(Incident.agent_run_id == task.id).count(),
                "is_simulated": task.is_simulated,
                "created_at": task.created_at.isoformat(),
            }
            for task in tasks
        ]

    def get_task(self, task_id: str) -> QualityAnalysisResponse:
        task = self.db.get(AgentRun, task_id)
        if not task or task.module != "quality":
            raise NotFoundError("分析任务不存在", "QUALITY_TASK_NOT_FOUND")
        upload = self.db.get(Upload, task.upload_id)
        if not upload:
            raise NotFoundError("上传文件不存在", "UPLOAD_NOT_FOUND")
        incidents = self.db.query(Incident).filter(Incident.agent_run_id == task.id).all()
        evidence = self.db.query(IncidentEvidence).filter(IncidentEvidence.incident_id.in_([item.id for item in incidents])).all() if incidents else []
        result_json = task.result_json if isinstance(task.result_json, dict) else {}
        state = {
            "risk_level": task.risk_level,
            "hazards": [self._hazard_dict(item) for item in incidents],
            "evidence": [self._evidence_dict(item) for item in evidence],
            "work_order_draft": result_json.get("work_order_draft"),
            "worker_message": result_json.get("worker_message", ""),
            "report_preview": result_json.get("report_preview", ""),
            "agent_trace": task.trace_json or [],
            "review_required": True,
            "is_simulated": task.is_simulated,
            "provider_info": task.provider_info_json or {},
        }
        return self._response(task, upload, incidents, state, None)

    def _response(self, task, upload, incidents, state, annotated_name: str | None) -> QualityAnalysisResponse:
        defects = [self._hazard_dict(item) for item in incidents]
        evidence_ids = [item.id for item in incidents]
        evidence_rows = self.db.query(IncidentEvidence).filter(IncidentEvidence.incident_id.in_(evidence_ids)).all() if evidence_ids else []
        draft = state.get("work_order_draft")
        return QualityAnalysisResponse(
            task_id=task.id,
            project_id=task.project_id,
            upload_id=upload.id,
            file_url=f"/storage/{upload.relative_path}",
            annotated_url=f"/storage/annotated/{annotated_name}" if annotated_name else None,
            location=task.location,
            work_type=task.work_type,
            risk_level=task.risk_level,
            defects=defects,
            evidence=[self._evidence_dict(item) for item in evidence_rows],
            work_order_draft=draft,
            worker_message=str(state.get("worker_message", "")),
            report_preview=str(state.get("report_preview", "")),
            agent_trace=state.get("agent_trace", []),
            review_required=True,
            is_simulated=bool(state.get("is_simulated", True)),
            provider_info={str(k): str(v) for k, v in dict(state.get("provider_info", {})).items()},
        )

    @staticmethod
    def _hazard_dict(incident: Incident) -> dict[str, object]:
        metadata = incident.metadata_json if isinstance(incident.metadata_json, dict) else {}
        return {
            "id": incident.id,
            "hazard_type": incident.hazard_type,
            "hazard_name": incident.hazard_name,
            "description": incident.description,
            "confidence": incident.confidence,
            "risk_level": incident.risk_level,
            "bbox": incident.bbox_json,
            "review_required": incident.review_required,
            "source": metadata.get("source"),
            "regulation": metadata.get("regulation"),
            "suggestion": metadata.get("suggestion"),
            "is_major": metadata.get("is_major"),
            "major_basis": metadata.get("major_basis"),
        }

    @staticmethod
    def _evidence_dict(item: IncidentEvidence) -> dict[str, object]:
        return {
            "id": item.id,
            "source": item.source,
            "article": item.article,
            "content": item.content,
            "score": item.score,
        }

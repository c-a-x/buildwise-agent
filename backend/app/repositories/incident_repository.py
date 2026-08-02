from sqlalchemy.orm import Session

from app.models import Incident


class IncidentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_run(self, task_id: str) -> list[Incident]:
        return self.db.query(Incident).filter(Incident.agent_run_id == task_id).all()

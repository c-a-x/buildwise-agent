from sqlalchemy.orm import Session

from app.models import WorkOrder


class WorkOrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, work_order_id: str) -> WorkOrder | None:
        return self.db.get(WorkOrder, work_order_id)

    def list(self, project_id: str | None = None, status: str | None = None) -> list[WorkOrder]:
        query = self.db.query(WorkOrder)
        if project_id:
            query = query.filter(WorkOrder.project_id == project_id)
        if status:
            query = query.filter(WorkOrder.status == status)
        return query.order_by(WorkOrder.deadline.asc()).all()

from datetime import date

from sqlalchemy.orm import Session

from app.models import DailyReport


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_date(self, project_id: str, report_date: date) -> DailyReport | None:
        return (
            self.db.query(DailyReport)
            .filter(DailyReport.project_id == project_id, DailyReport.report_date == report_date)
            .first()
        )

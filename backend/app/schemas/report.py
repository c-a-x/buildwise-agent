from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyReportGenerate(BaseModel):
    project_id: str
    report_date: date


class DailyReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    report_date: date
    statistics: dict[str, object]
    content: str
    generated_by: str
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime

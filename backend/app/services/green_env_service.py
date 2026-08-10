"""环保监测台账：扬尘/噪声/污水/固废日常读数 + 超标提醒。

阈值（GB 12523-2011 施工场界噪声、GB/T 51186-2016 等常用施工环保控制值）：
- 扬尘：PM10≤150、PM2.5≤75、TSP≤300（μg/m³）
- 噪声：昼≤70、夜≤55（dB(A)）
- 污水：COD≤100、SS≤70（mg/L），pH 6~9
- 固废：只记录不设阈值

超标判定：above 规则 value>limit 告警；range 规则越界（<min 或 >max）告警。
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import GreenEnvRecord, Project
from app.schemas.green import EnvAlertRead, EnvRecordRead, EnvThresholdRead, GreenEnvRecordForm
from app.utils.ids import new_id

THRESHOLDS: dict[str, dict[str, object]] = {
    "pm25": {"name": "PM2.5", "unit": "μg/m³", "rule": "above", "limit": 75},
    "pm10": {"name": "PM10", "unit": "μg/m³", "rule": "above", "limit": 150},
    "tsp": {"name": "TSP", "unit": "μg/m³", "rule": "above", "limit": 300},
    "noise_day_db": {"name": "昼间噪声", "unit": "dB(A)", "rule": "above", "limit": 70},
    "noise_night_db": {"name": "夜间噪声", "unit": "dB(A)", "rule": "above", "limit": 55},
    "cod_mg": {"name": "污水 COD", "unit": "mg/L", "rule": "above", "limit": 100},
    "ss_mg": {"name": "污水 SS", "unit": "mg/L", "rule": "above", "limit": 70},
    "ph": {"name": "pH 值", "unit": "", "rule": "range", "min": 6, "max": 9},
}


def threshold_read(key: str, threshold: dict[str, object]) -> EnvThresholdRead:
    return EnvThresholdRead(
        key=key,
        name=str(threshold["name"]),
        unit=str(threshold["unit"]),
        rule=str(threshold["rule"]),
        limit=threshold.get("limit"),
        min=threshold.get("min"),
        max=threshold.get("max"),
    )


def check_alerts(values: dict[str, float | None]) -> list[EnvAlertRead]:
    """按阈值判定超标指标，返回告警列表（无超标则空）。"""
    alerts: list[EnvAlertRead] = []
    for key, threshold in THRESHOLDS.items():
        value = values.get(key)
        if value is None:
            continue
        rule = str(threshold["rule"])
        if rule == "above":
            if value > threshold["limit"]:
                alerts.append(
                    EnvAlertRead(
                        key=key,
                        name=str(threshold["name"]),
                        value=value,
                        rule=rule,
                        limit=threshold["limit"],
                    )
                )
        elif rule == "range":
            if value < threshold["min"] or value > threshold["max"]:
                alerts.append(
                    EnvAlertRead(
                        key=key,
                        name=str(threshold["name"]),
                        value=value,
                        rule=rule,
                        min=threshold["min"],
                        max=threshold["max"],
                    )
                )
    return alerts


class GreenEnvService:
    METRIC_KEYS = ("pm25", "pm10", "tsp", "noise_day_db", "noise_night_db", "cod_mg", "ss_mg", "ph", "solid_waste_t")

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def thresholds() -> list[EnvThresholdRead]:
        return [threshold_read(key, threshold) for key, threshold in THRESHOLDS.items()]

    def upsert_record(self, form: GreenEnvRecordForm, requested_by: str) -> EnvRecordRead:
        values = {key: getattr(form, key) for key in self.METRIC_KEYS}
        alerts = check_alerts(values)
        record = (
            self.db.query(GreenEnvRecord)
            .filter(GreenEnvRecord.project_id == form.project_id, GreenEnvRecord.record_date == form.record_date)
            .one_or_none()
        )
        if record is None:
            record = GreenEnvRecord(id=new_id("ENV"), project_id=form.project_id, requested_by=requested_by, record_date=form.record_date)
            self.db.add(record)
        for key in self.METRIC_KEYS:
            setattr(record, key, values[key])
        record.alerts_json = [alert.model_dump() for alert in alerts]
        record.has_alerts = bool(alerts)
        record.result_json = {"thresholds": [threshold_read(key, threshold).model_dump() for key, threshold in THRESHOLDS.items()]}
        self.db.commit()
        self.db.refresh(record)
        return self._read(record)

    def list_records(
        self,
        *,
        project_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        alert_only: bool = False,
    ) -> list[EnvRecordRead]:
        query = self.db.query(GreenEnvRecord)
        if project_id:
            query = query.filter(GreenEnvRecord.project_id == project_id)
        if start_date:
            query = query.filter(GreenEnvRecord.record_date >= start_date)
        if end_date:
            query = query.filter(GreenEnvRecord.record_date <= end_date)
        if alert_only:
            query = query.filter(GreenEnvRecord.has_alerts.is_(True))
        rows = query.order_by(GreenEnvRecord.record_date.desc()).all()
        return [self._read(row) for row in rows]

    def get_record(self, record_id: str) -> EnvRecordRead:
        record = self.db.get(GreenEnvRecord, record_id)
        if not record:
            raise NotFoundError("环保监测记录不存在", "GREEN_ENV_RECORD_NOT_FOUND")
        return self._read(record)

    def _read(self, record: GreenEnvRecord) -> EnvRecordRead:
        alerts_json = record.alerts_json if isinstance(record.alerts_json, list) else []
        return EnvRecordRead(
            record_id=record.id,
            project_id=record.project_id,
            project_name=self._project_name(record.project_id),
            record_date=record.record_date.isoformat(),
            pm25=record.pm25,
            pm10=record.pm10,
            tsp=record.tsp,
            noise_day_db=record.noise_day_db,
            noise_night_db=record.noise_night_db,
            cod_mg=record.cod_mg,
            ss_mg=record.ss_mg,
            ph=record.ph,
            solid_waste_t=record.solid_waste_t,
            has_alerts=record.has_alerts,
            alerts=[EnvAlertRead(**item) for item in alerts_json],
            created_at=record.created_at.isoformat(),
        )

    def _project_name(self, project_id: str) -> str:
        project = self.db.get(Project, project_id)
        return project.name if project else project_id

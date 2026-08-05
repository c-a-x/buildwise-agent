"""跨模块通用统计服务。

借鉴 `_ext_src/building-energy-esg-fm` 的 `stats_service.py::anomaly_analysis`：
对按天聚合的计数序列做 z-score，标记超出阈值的异常日。纯 Python `statistics`，
不引入 numpy/pandas。质量缺陷复用 `Incident` 表（`metadata_json.module="quality"`），
按 module 在 Python 侧分拣。
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Incident

_MODULES = ("safety", "quality")


class StatsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def anomaly_detection(
        self,
        *,
        project_id: str,
        module: str = "safety",
        days: int = 30,
        z_threshold: float = 2.5,
    ) -> dict[str, object]:
        """近 N 天按天 Incident 计数的 z-score 异常检测。

        返回样本按日期升序；`available=False` 表示无数据可判。
        """
        days = max(3, min(90, int(days)))
        z_threshold = max(0.1, min(10.0, float(z_threshold)))
        if module not in _MODULES:
            module = "safety"

        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=days - 1)
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)

        incidents = (
            self.db.query(Incident)
            .filter(Incident.project_id == project_id, Incident.created_at >= start_dt)
            .all()
        )

        day_keys = sorted((start + timedelta(days=i)).isoformat() for i in range(days))
        counts: dict[str, int] = {day: 0 for day in day_keys}
        for incident in incidents:
            metadata = incident.metadata_json if isinstance(incident.metadata_json, dict) else {}
            incident_module = metadata.get("module")
            if module == "quality":
                if incident_module != "quality":
                    continue
            elif incident_module not in (None, "", "safety"):
                continue
            day = incident.created_at.astimezone().date().isoformat()
            if day in counts:
                counts[day] += 1

        values = [counts[day] for day in day_keys]
        if sum(values) == 0:
            return {
                "available": False,
                "reason": "该时间段内没有记录",
                "project_id": project_id,
                "module": module,
                "days": days,
                "z_threshold": z_threshold,
                "total_days": days,
                "mean": 0.0,
                "std": 0.0,
                "anomaly_days": 0,
                "ratio": 0.0,
                "samples": [],
            }

        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.0

        if std == 0:
            return {
                "available": True,
                "project_id": project_id,
                "module": module,
                "days": days,
                "z_threshold": z_threshold,
                "total_days": days,
                "mean": round(mean, 4),
                "std": 0.0,
                "anomaly_days": 0,
                "ratio": 0.0,
                "samples": [
                    {"date": day, "count": counts[day], "z": 0.0, "anomaly": False}
                    for day in day_keys
                ],
            }

        samples: list[dict[str, object]] = []
        anomaly_days = 0
        for day in day_keys:
            count = counts[day]
            z = (count - mean) / std
            is_anomaly = z > z_threshold
            if is_anomaly:
                anomaly_days += 1
            samples.append({"date": day, "count": count, "z": round(z, 3), "anomaly": is_anomaly})

        return {
            "available": True,
            "project_id": project_id,
            "module": module,
            "days": days,
            "z_threshold": z_threshold,
            "total_days": days,
            "mean": round(mean, 4),
            "std": round(std, 4),
            "anomaly_days": anomaly_days,
            "ratio": round(anomaly_days / days, 3),
            "samples": samples,
        }

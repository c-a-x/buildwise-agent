from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


# 阶段定义：GB/T 51366-2019 施工相关生命周期阶段。
STAGE_NAMES = {"A1-A3": "建材生产", "A4": "建材运输", "A5": "施工过程"}
CATEGORY_STAGE = {"material": "A1-A3", "energy": "A5", "transport": "A4"}


@dataclass(frozen=True)
class CarbonFactor:
    code: str
    category: str  # material | energy | transport
    name: str
    unit: str
    factor: float  # tCO2e / 单位
    factor_unit: str
    source: str
    year: int | None = None
    verified: bool = False
    note: str = ""


@dataclass(frozen=True)
class FactorLibrary:
    version: str
    factors: tuple[CarbonFactor, ...]
    load_error: str = ""

    def get(self, code: str) -> CarbonFactor | None:
        for factor in self.factors:
            if factor.code == code:
                return factor
        return None

    def list(self, category: str | None = None) -> list[CarbonFactor]:
        if category is None:
            return list(self.factors)
        return [factor for factor in self.factors if factor.category == category]


def load_factor_library(path: Path | None = None) -> FactorLibrary:
    """读取并校验排放因子库。文件缺失或解析失败时返回空库并记录错误，不抛异常。"""
    factor_path = path or settings.green_factors_path
    if not factor_path.exists():
        return FactorLibrary(version="", factors=(), load_error=f"因子库文件不存在：{factor_path}")
    try:
        raw = json.loads(factor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return FactorLibrary(version="", factors=(), load_error=f"因子库解析失败：{exc}")

    factors: list[CarbonFactor] = []
    for category in ("materials", "energy", "transport"):
        for item in raw.get(category, []):
            if not isinstance(item, dict) or "code" not in item:
                continue
            factors.append(
                CarbonFactor(
                    code=str(item["code"]),
                    category=category,
                    name=str(item.get("name", item["code"])),
                    unit=str(item.get("unit", "")),
                    factor=float(item["factor"]),
                    factor_unit=str(item.get("factor_unit", "tCO2e")),
                    source=str(item.get("source", "")),
                    year=item.get("year"),
                    verified=bool(item.get("verified", False)),
                    note=str(item.get("note", "")),
                )
            )
    return FactorLibrary(version=str(raw.get("version", "")), factors=tuple(factors))


@lru_cache(maxsize=1)
def factor_library() -> FactorLibrary:
    """进程级缓存。修改因子库文件后需重启后端生效。"""
    return load_factor_library()

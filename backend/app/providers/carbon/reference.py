from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class ReferenceMetric:
    """单条真实公开数据（如中国建筑 2024 ESG/年报披露的数值）。value 为可直接展示的字符串。"""

    code: str
    group: str  # category，如 carbon/energy/green/environment/scale
    name: str
    value: str
    unit: str
    year: int | None = None
    source: str = ""
    note: str = ""


@dataclass(frozen=True)
class ReferenceGroup:
    category: str
    name: str
    items: tuple[ReferenceMetric, ...]


@dataclass(frozen=True)
class ReferenceLibrary:
    version: str
    updated_at: str
    source_note: str
    groups: tuple[ReferenceGroup, ...]
    load_error: str = ""

    def grouped(self) -> list[ReferenceGroup]:
        return list(self.groups)

    def get(self, code: str) -> ReferenceMetric | None:
        for group in self.groups:
            for item in group.items:
                if item.code == code:
                    return item
        return None


def load_reference_library(path: Path | None = None) -> ReferenceLibrary:
    """读取并校验真实公开数据参考库。文件缺失或解析失败时返回空库并记录错误，不抛异常。"""
    reference_path = path or settings.green_reference_path
    if not reference_path.exists():
        return ReferenceLibrary(version="", updated_at="", source_note="", groups=(), load_error=f"参考数据文件不存在：{reference_path}")
    try:
        raw = json.loads(reference_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ReferenceLibrary(version="", updated_at="", source_note="", groups=(), load_error=f"参考数据解析失败：{exc}")

    groups: list[ReferenceGroup] = []
    for group in raw.get("groups", []):
        if not isinstance(group, dict) or "category" not in group:
            continue
        items = tuple(
            ReferenceMetric(
                code=str(item["code"]),
                group=str(group["category"]),
                name=str(item.get("name", item["code"])),
                value=str(item.get("value", "")),
                unit=str(item.get("unit", "")),
                year=item.get("year"),
                source=str(item.get("source", "")),
                note=str(item.get("note", "")),
            )
            for item in group.get("items", [])
            if isinstance(item, dict) and "code" in item
        )
        groups.append(ReferenceGroup(category=str(group["category"]), name=str(group.get("name", group["category"])), items=items))
    return ReferenceLibrary(
        version=str(raw.get("version", "")),
        updated_at=str(raw.get("updated_at", "")),
        source_note=str(raw.get("source_note", "")),
        groups=tuple(groups),
    )


@lru_cache(maxsize=1)
def reference_library() -> ReferenceLibrary:
    """进程级缓存。修改参考数据文件后需重启后端生效。"""
    return load_reference_library()

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class HeatLevel:
    level: str  # none | yellow | orange | red
    min_c: float
    name: str
    advice: str = ""


@dataclass(frozen=True)
class WellbeingTip:
    id: str
    trigger: str  # always | yellow+ | orange+ | red+
    text: str


@dataclass(frozen=True)
class FirstAidStage:
    stage: str
    symptoms: str
    action: str


@dataclass(frozen=True)
class Facility:
    name: str
    location: str
    hours: str
    note: str


@dataclass(frozen=True)
class WellbeingRules:
    version: str
    source: str
    heat_levels: tuple[HeatLevel, ...]
    restriction: dict[str, str]
    special_groups: str
    allowance: str
    condition_uv: dict[str, str]
    tips: tuple[WellbeingTip, ...]
    first_aid: tuple[FirstAidStage, ...]
    facilities: tuple[Facility, ...]
    load_error: str = ""

    def heat_level_for(self, temperature_c: float) -> HeatLevel:
        """按温度返回对应高温等级；低于最低档（35℃）返回 none。"""
        current = self.heat_levels[0]
        for level in self.heat_levels:
            if temperature_c >= level.min_c:
                current = level
        return current

    def tips_for(self, heat_level: str) -> list[WellbeingTip]:
        """按触发条件过滤温馨提醒：always 恒显示；`X+` 表示 heat_level 达到该档或以上。"""
        order = {"none": 0, "yellow": 1, "orange": 2, "red": 3}
        current = order.get(heat_level, 0)
        result: list[WellbeingTip] = []
        for tip in self.tips:
            trigger = tip.trigger
            if trigger == "always":
                result.append(tip)
            elif trigger.endswith("+") and current >= order.get(trigger[:-1], 0):
                result.append(tip)
        return result


def _fallback_rules() -> WellbeingRules:
    """内置最小兜底规则：rules.json 缺失/解析失败时保证 analyze 不崩溃。"""
    return WellbeingRules(
        version="",
        source="内置兜底规则",
        heat_levels=(
            HeatLevel("none", 0, "无高温"),
            HeatLevel("yellow", 35, "黄色预警"),
            HeatLevel("orange", 37, "橙色预警"),
            HeatLevel("red", 40, "红色预警"),
        ),
        restriction={
            "yellow": "日最高气温≥35℃：采取换班轮休等方式缩短连续作业时间，不得安排室外露天作业劳动者加班。",
            "orange": "日最高气温≥37℃：全天室外露天作业累计不超过6小时，气温最高时段3小时内不得安排室外露天作业。",
            "red": "日最高气温≥40℃：应当停止当日室外露天作业。",
        },
        special_groups="不得安排怀孕女职工和未成年工在35℃以上高温天气期间从事室外露天作业。",
        allowance="35℃以上高温天气从事室外露天作业应发放高温津贴。",
        condition_uv={"晴": "强", "多云": "中", "阴": "中", "小雨": "弱", "中雨": "弱", "雷阵雨": "弱"},
        tips=(
            WellbeingTip("hydration", "always", "记得少量多次补水，喝淡盐水或盐汽水更佳。"),
            WellbeingTip("body_signal", "yellow+", "出现头晕、大汗、四肢无力可能是先兆中暑，请立即到阴凉处休息。"),
            WellbeingTip("stop_work", "red+", "已达红色高温，请停止当日室外露天作业，转移到阴凉通风处休息。"),
        ),
        first_aid=(FirstAidStage("先兆中暑", "头晕、大汗、四肢无力", "立即转移到阴凉通风处休息，补充水分盐分。"),),
        facilities=(),
        load_error="",
    )


def load_wellbeing_rules(path: Path | None = None) -> WellbeingRules:
    """读取并校验工友关怀规则库。文件缺失或解析失败时返回兜底规则并记录错误，不抛异常。"""
    rule_path = path or settings.wellbeing_rules_path
    if not rule_path.exists():
        return replace(_fallback_rules(), load_error=f"规则文件不存在：{rule_path}")
    try:
        raw = json.loads(rule_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return replace(_fallback_rules(), load_error=f"规则文件解析失败：{exc}")

    fallback = _fallback_rules()
    heat_levels = tuple(
        HeatLevel(
            level=str(item.get("level", "")),
            min_c=float(item.get("min_c", 0)),
            name=str(item.get("name", "")),
            advice=str(item.get("advice", "")),
        )
        for item in raw.get("heat_levels", [])
        if isinstance(item, dict) and item.get("level")
    )
    if not heat_levels:
        heat_levels = fallback.heat_levels

    return WellbeingRules(
        version=str(raw.get("version", "")),
        source=str(raw.get("source", "")),
        heat_levels=heat_levels,
        restriction={str(k): str(v) for k, v in raw.get("restriction", {}).items() if v},
        special_groups=str(raw.get("special_groups", "")),
        allowance=str(raw.get("allowance", "")),
        condition_uv={str(k): str(v) for k, v in raw.get("condition_uv", {}).items() if v},
        tips=tuple(
            WellbeingTip(
                id=str(item.get("id", "")),
                trigger=str(item.get("trigger", "always")),
                text=str(item.get("text", "")),
            )
            for item in raw.get("tips", [])
            if isinstance(item, dict) and item.get("id")
        ),
        first_aid=tuple(
            FirstAidStage(
                stage=str(item.get("stage", "")),
                symptoms=str(item.get("symptoms", "")),
                action=str(item.get("action", "")),
            )
            for item in raw.get("first_aid", [])
            if isinstance(item, dict) and item.get("stage")
        ),
        facilities=tuple(
            Facility(
                name=str(item.get("name", "")),
                location=str(item.get("location", "")),
                hours=str(item.get("hours", "")),
                note=str(item.get("note", "")),
            )
            for item in raw.get("facilities", [])
            if isinstance(item, dict) and item.get("name")
        ),
    )


@lru_cache(maxsize=1)
def wellbeing_rules() -> WellbeingRules:
    """进程级缓存。修改规则文件后需重启后端生效。"""
    return load_wellbeing_rules()

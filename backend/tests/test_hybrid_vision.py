"""safety_hybrid 视觉 Provider 的映射、合并、降级逻辑单元测试。"""

from __future__ import annotations

from app.core.config import Settings
from app.providers.vision.hybrid import SafetyHybridVisionProvider
from app.providers.vision.mapping import (
    _normalize_risk,
    class_to_hazard,
    compute_risk_level,
    llm_finding_to_hazard,
    merge_hazards,
)


def test_class_to_hazard_safehat_violations():
    hazard = class_to_hazard("NO-Hardhat", 0.93, [0.1, 0.1, 0.5, 0.7])
    assert hazard is not None
    assert hazard["hazard_type"] == "no_helmet"
    assert hazard["risk_level"] == "high"
    assert hazard["bbox"] == [0.1, 0.1, 0.5, 0.7]
    assert hazard["confidence"] == 0.93

    vest = class_to_hazard("NO-Safety Vest", 0.81, [0.2, 0.2, 0.6, 0.8])
    assert vest is not None and vest["hazard_type"] == "no_safety_vest"


def test_class_to_hazard_coco_person():
    hazard = class_to_hazard("person", 0.9, [0.0, 0.0, 1.0, 1.0])
    assert hazard is not None
    assert hazard["hazard_type"] == "person_present"
    assert hazard["risk_level"] == "low"


def test_class_to_hazard_compliance_ignored():
    for label in ("Hardhat", "Mask", "Safety Vest", "Safety Cone", "car", "unknown"):
        assert class_to_hazard(label, 0.9, [0, 0, 1, 1]) is None


def test_llm_finding_to_hazard_merges_regulation_and_suggestion():
    hazard = llm_finding_to_hazard(
        {
            "category_code": "H1",
            "category_name": "高处坠落",
            "description": "临边作业未系安全带",
            "severity": "high",
            "regulation": "《建筑施工高处作业安全技术规范》JGJ80-2016 第4.1.1条",
            "suggestion": "立即停止作业并系挂安全带",
            "confidence": 0.95,
            "is_major": True,
            "major_basis": "临边高度超过2m",
        }
    )
    assert hazard["hazard_type"] == "llm_h1"
    assert hazard["risk_level"] == "high"
    assert "规范依据" in hazard["description"]
    assert "整改建议" in hazard["description"]
    assert "重大事故隐患判定" in hazard["description"]
    assert hazard["bbox"] is None


def test_merge_hazards_dedupes_same_detection():
    yolo = [class_to_hazard("NO-Hardhat", 0.9, [0.1, 0.1, 0.4, 0.6])]
    duplicate = class_to_hazard("NO-Hardhat", 0.95, [0.11, 0.1, 0.4, 0.6])  # 中心距很小
    llm = [llm_finding_to_hazard({"category_code": "H1", "category_name": "高处坠落", "description": "d", "severity": "medium"})]
    merged = merge_hazards(yolo + [duplicate], llm)
    types = [h["hazard_type"] for h in merged]
    assert types.count("no_helmet") == 1  # 同检测去重，保留置信度高者
    assert "llm_h1" in types


def test_compute_risk_level():
    assert compute_risk_level([]) == "normal"
    assert (
        compute_risk_level(
            [
                {"risk_level": "low"},
                {"risk_level": "critical"},
                {"risk_level": "medium"},
            ]
        )
        == "critical"
    )


def test_normalize_risk_aliases():
    assert _normalize_risk("严重") == "high"
    assert _normalize_risk("一般") == "low"
    assert _normalize_risk(None) == "medium"


def test_hybrid_falls_back_to_mock_when_nothing_available(monkeypatch):
    settings = Settings(
        vision_provider="safety_hybrid",
        vision_llm_provider="off",
        yolo_model_path="storage/models/does-not-exist.pt",
    )
    monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: None)
    provider = SafetyHybridVisionProvider(settings)
    result = provider.analyze("fake.jpg", {"demo_scenario": "no_helmet"})
    assert result["is_simulated"] is True
    assert result["provider"] == "mock"
    assert len(result["hazards"]) >= 1


def test_hybrid_yolo_only_not_simulated(monkeypatch):
    settings = Settings(vision_provider="safety_hybrid", vision_llm_provider="off")
    fake_hazards = [class_to_hazard("NO-Hardhat", 0.9, [0.1, 0.1, 0.4, 0.6])]
    monkeypatch.setattr("app.providers.vision.yolo.load_model", lambda path: object())
    monkeypatch.setattr("app.providers.vision.hybrid.YOLODetector.detect", lambda self, image: fake_hazards)
    provider = SafetyHybridVisionProvider(settings)
    result = provider.analyze("fake.jpg", {"demo_scenario": "no_helmet"})
    assert result["is_simulated"] is False
    assert "yolo" in str(result["provider"])
    assert result["hazards"][0]["hazard_type"] == "no_helmet"

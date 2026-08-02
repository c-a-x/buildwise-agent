from __future__ import annotations


class MockVisionProvider:
    name = "mock"

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        scenario = context.get("demo_scenario") or "no_helmet"
        if scenario == "normal":
            return {
                "hazards": [],
                "risk_level": "normal",
                "is_simulated": True,
                "provider": self.name,
            }

        hazard_by_scenario: dict[str, dict[str, object]] = {
            "no_helmet": {
                "hazard_type": "no_helmet",
                "hazard_name": "未佩戴安全帽",
                "description": "检测到作业人员未正确佩戴并扣紧安全帽。",
                "confidence": 0.96,
                "risk_level": "high",
                "bbox": [0.24, 0.18, 0.48, 0.86],
            },
            "missing_guardrail": {
                "hazard_type": "missing_guardrail",
                "hazard_name": "临边防护缺失",
                "description": "检测到临边区域缺少连续可靠的防护栏杆。",
                "confidence": 0.91,
                "risk_level": "critical",
                "bbox": [0.08, 0.32, 0.78, 0.77],
            },
            "no_safety_vest": {
                "hazard_type": "no_safety_vest",
                "hazard_name": "未穿反光安全背心",
                "description": "检测到作业人员未穿戴反光安全背心。",
                "confidence": 0.88,
                "risk_level": "medium",
                "bbox": [0.31, 0.24, 0.61, 0.88],
            },
        }
        hazard = hazard_by_scenario.get(scenario, hazard_by_scenario["no_helmet"])
        return {
            "hazards": [hazard],
            "risk_level": str(hazard["risk_level"]),
            "is_simulated": True,
            "provider": self.name,
        }

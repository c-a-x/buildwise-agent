from __future__ import annotations


class QualityMockVisionProvider:
    """质量缺陷模拟 Provider：按 demo_scenario 返回固定缺陷（离线可演示）。"""

    name = "quality_mock"

    def analyze(self, image_path: str, context: dict[str, str]) -> dict[str, object]:
        scenario = context.get("demo_scenario") or "crack"
        if scenario == "normal":
            return {
                "hazards": [],
                "risk_level": "normal",
                "is_simulated": True,
                "provider": self.name,
            }

        hazard_by_scenario: dict[str, dict[str, object]] = {
            "crack": {
                "hazard_type": "crack",
                "hazard_name": "裂缝",
                "description": "检测到墙体竖向贯穿裂缝，宽度约 1.2mm。",
                "confidence": 0.95,
                "risk_level": "medium",
                "bbox": [0.22, 0.15, 0.31, 0.88],
            },
            "leakage": {
                "hazard_type": "leakage",
                "hazard_name": "渗漏",
                "description": "检测到墙面大范围水渍与渗水痕迹，疑为接缝渗漏。",
                "confidence": 0.92,
                "risk_level": "medium",
                "bbox": [0.35, 0.2, 0.78, 0.8],
            },
            "abscission": {
                "hazard_type": "abscission",
                "hazard_name": "剥落",
                "description": "检测到抹灰层局部剥落掉块，露出基层。",
                "confidence": 0.9,
                "risk_level": "high",
                "bbox": [0.18, 0.25, 0.52, 0.75],
            },
            "corrosion": {
                "hazard_type": "corrosion",
                "hazard_name": "锈蚀",
                "description": "检测到钢结构构件表面锈蚀与锈水流痕。",
                "confidence": 0.88,
                "risk_level": "medium",
                "bbox": [0.3, 0.28, 0.64, 0.82],
            },
            "bulge": {
                "hazard_type": "bulge",
                "hazard_name": "鼓包",
                "description": "检测到饰面层局部鼓包隆起，空鼓变形明显。",
                "confidence": 0.86,
                "risk_level": "high",
                "bbox": [0.24, 0.3, 0.6, 0.72],
            },
        }
        hazard = hazard_by_scenario.get(scenario, hazard_by_scenario["crack"])
        return {
            "hazards": [hazard],
            "risk_level": str(hazard["risk_level"]),
            "is_simulated": True,
            "provider": self.name,
        }

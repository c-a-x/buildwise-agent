from __future__ import annotations


class TemplateTextProvider:
    name = "template"

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        risk_level = str(payload.get("risk_level", "medium"))
        hazard_name = str(payload.get("hazard_name", "现场隐患"))
        requirements = payload.get("requirements", [])
        first_requirement = str(requirements[0]) if isinstance(requirements, list) and requirements else "请按安全员要求完成整改"
        role = str(payload.get("role", "安全员"))
        if risk_level in {"high", "critical"}:
            return f"师傅，请先暂停作业。现场发现{hazard_name}，{first_requirement}，待{role}确认后再继续施工。"
        return f"师傅，现场发现{hazard_name}。{first_requirement}，完成后请联系{role}复查。"

    def generate_report(self, payload: dict[str, object]) -> str:
        statistics = payload.get("statistics", {})
        if not isinstance(statistics, dict):
            statistics = {}
        incident_total = statistics.get("incident_total", 0)
        high_total = statistics.get("high_risk_total", 0)
        new_orders = statistics.get("new_work_orders", 0)
        closed_orders = statistics.get("closed_work_orders", 0)
        pending_review = statistics.get("pending_review_work_orders", 0)
        return (
            f"一、今日巡检概况\n今日记录隐患 {incident_total} 项，其中高风险及以上 {high_total} 项。\n\n"
            f"二、主要风险\n请重点关注高处作业、个人防护和临边防护，所有 AI 结果均需人工复核。\n\n"
            f"三、整改进度\n今日新建工单 {new_orders} 张，关闭 {closed_orders} 张，待复查 {pending_review} 张。\n\n"
            "四、待协调事项\n请项目经理协调未完成工单的责任人和复查资源。\n\n"
            "五、明日重点\n继续关注临边防护、个人防护用品和交叉作业区域。"
        )

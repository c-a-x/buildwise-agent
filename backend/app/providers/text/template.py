from __future__ import annotations


class TemplateTextProvider:
    name = "template"

    def generate_chat_reply(self, payload: dict[str, object]) -> str:
        question = str(payload.get("question", "")).strip() or "这个问题"
        context = payload.get("context", [])
        context_lines = [str(item).strip() for item in context if str(item).strip()] if isinstance(context, list) else []
        if context_lines:
            reply = f"师傅，先按这条来：{context_lines[0]}。"
            if len(context_lines) > 1:
                reply += f"补充参考：{'；'.join(context_lines[1:3])}。"
            return reply + "如果现场条件和条款有冲突，先停一下，找安全员确认后再继续。"
        return f"师傅，先把问题说清楚：{question}。如果还不确定，先别硬干，找安全员确认后再继续。"

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        risk_level = str(payload.get("risk_level", "medium"))
        hazard_name = str(payload.get("hazard_name", "现场隐患"))
        requirements = payload.get("requirements", [])
        first_requirement = str(requirements[0]) if isinstance(requirements, list) and requirements else "请按安全员要求完成整改"
        role = str(payload.get("role", "安全员"))
        if risk_level in {"high", "critical"}:
            return f"师傅，请先暂停作业。现场发现{hazard_name}，{first_requirement}，待{role}确认后再继续施工。"
        return f"师傅，现场发现{hazard_name}。{first_requirement}，完成后请联系{role}复查。"

    def generate_worker_answer(self, payload: dict[str, object]) -> str:
        """离线兜底：引用检索到的第一条条款回答，未命中时给出诚实的"未检索到"提示。"""
        question = str(payload.get("question", "您的问题"))
        clauses = payload.get("clauses", [])
        if isinstance(clauses, list) and clauses:
            top = clauses[0]
            requirement = str(top.get("content", "")).strip().rstrip("。")
            return f"师傅，按《{top.get('source', '')}》{top.get('article', '') or ''}：{requirement}。请按此要求执行，完成后请联系安全员复查。"
        return f"师傅，知识库暂未检索到与「{question}」直接相关的条款，可换个说法再问，或直接咨询现场安全员。"

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

    def generate_green_advice(self, payload: dict[str, object]) -> str:
        """离线兜底：按得分偏低维度/高占比阶段给出预置建议，未接入 LLM 时使用。"""
        source_type = str(payload.get("source_type", "carbon"))
        lines: list[str] = []
        if source_type == "assessment":
            low = payload.get("low_dimensions", [])
            for item in (low if isinstance(low, list) else [])[:3]:
                name = item.get("name", "") if isinstance(item, dict) else ""
                lines.append(f"1. {name}维度得分偏低，建议制定专项提升措施：优先采用可循环材料、非传统水源与节能设备，严格落实扬尘、噪声、污水和固废管控要求。")
            if not lines:
                lines.append("1. 各维度均达到合格线，建议持续保持并定期复盘绿色施工专项方案落实情况。")
        else:
            stage_shares = payload.get("stage_shares", {})
            top_stage = max(stage_shares, key=stage_shares.get) if isinstance(stage_shares, dict) and stage_shares else None
            if top_stage == "A1-A3":
                lines.append("1. 建材生产阶段排放占比最高，优先选用经核证的绿色建材并优化结构设计、控制材料用量。")
            elif top_stage == "A4":
                lines.append("1. 建材运输阶段排放占比较高，优化运输线路与车辆调度，减少二次转运，优先使用新能源运输车辆。")
            elif top_stage == "A5":
                lines.append("1. 施工阶段排放占比较高，采用节能设备、错峰用电并加强临时用电管理，降低外购电力间接排放。")
            lines.append("2. 提高模板、脚手架等周转材料使用次数，减少一次性材料消耗。")
            lines.append("3. 绿色施工具体措施以项目绿色施工专项方案为准。")
        return "\n".join(lines)

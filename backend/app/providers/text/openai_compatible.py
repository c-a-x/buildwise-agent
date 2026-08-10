from __future__ import annotations


class OpenAICompatibleTextProvider:
    """Minimal OpenAI-compatible adapter; never imported in offline mode."""

    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _generate(self, prompt: str) -> str:
        import json
        from urllib.request import Request, urlopen

        payload = json.dumps({"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}).encode("utf-8")
        request = Request(f"{self.base_url}/chat/completions", data=payload, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])

    def generate_worker_message(self, payload: dict[str, object]) -> str:
        return self._generate(f"请将以下施工安全要求转为不超过100字、尊重且明确的工友提醒：{payload}")

    def generate_worker_answer(self, payload: dict[str, object]) -> str:
        """基于检索条款回答工友问题：只允许引用给定条款，不得编造规范/数字。

        payload：{"question": str, "clauses": [{"source", "article", "content"}, ...]}
        """
        question = str(payload.get("question", ""))
        clauses = payload.get("clauses", [])
        clauses_text = (
            "\n".join(
                f"{index}. 《{clause.get('source', '')}》{clause.get('article', '') or ''} {clause.get('content', '')}"
                for index, clause in enumerate(clauses, start=1)
            )
            if isinstance(clauses, list) and clauses
            else "（知识库暂未检索到相关条款）"
        )
        prompt = (
            "你是一名工地安全工友助手，用通俗易懂、尊重、口语化的中文回答工人的问题。\n"
            f"工人问题：{question}\n\n"
            "可依据的规范条款如下（只能引用这些条款，不得编造任何规范、条款或数字）：\n"
            f"{clauses_text}\n\n"
            "要求：\n"
            "1. 直接回答问题，给出具体、可执行的安全建议；\n"
            "2. 末尾注明所引用条款《来源》第X条；若上方条款为空（知识库暂未检索到条款），请明确说明该回答为一般性安全建议、并非知识库条款，不要编造条款、规范或数字；\n"
            "3. 不要假设现场已发生违规或事故，不要凭空要求「暂停作业」；\n"
            "4. 控制在 150 字以内。"
        )
        return self._generate(prompt)

    def generate_report(self, payload: dict[str, object]) -> str:
        return self._generate(f"请根据以下结构化统计生成项目安全日报，不要修改任何数字：{payload}")

    def generate_green_advice(self, payload: dict[str, object]) -> str:
        """基于碳排核算或四节一环保评估结果生成绿色施工优化建议。

        只输出 3~6 条编号行动建议；不得编造规范条款号/数字；演示数据时明确声明仅供演示。
        """
        project_name = str(payload.get("project_name", ""))
        is_demo = bool(payload.get("is_demo", False))
        source_type = str(payload.get("source_type", "carbon"))

        if source_type == "assessment":
            total_score = payload.get("total_score")
            level = payload.get("level")
            low = payload.get("low_dimensions", [])
            low_text = (
                "\n".join(f"- {item.get('name')}（得分 {item.get('score')}）" for item in low if isinstance(item, dict))
                if isinstance(low, list) and low
                else "（各维度均达到合格线，保持并持续改进）"
            )
            prompt = (
                "你是一名资深绿色施工专家，请基于以下四节一环保评估结果给出绿色施工优化建议。\n"
                f"项目：{project_name}\n"
                f"总分：{total_score}　等级：{level}\n"
                f"得分偏低的维度：\n{low_text}\n\n"
                "要求：\n"
                "1. 输出 3~6 条编号行动建议，优先针对得分最低的维度给出可落地的具体措施；\n"
                "2. 每条 ≤120 字；\n"
                "3. 不得编造规范条款号或具体数字；\n"
                "4. 只输出编号建议，不要其他说明。"
            )
        else:
            total_emission = payload.get("total_emission")
            intensity = payload.get("intensity")
            stage_shares = payload.get("stage_shares", {})
            stage_text = (
                "；".join(f"{stage} 占比 {share * 100:.0f}%" for stage, share in stage_shares.items())
                if isinstance(stage_shares, dict) and stage_shares
                else "（无分阶段数据）"
            )
            current = payload.get("current_suggestions", [])
            current_text = (
                "\n".join(f"- {item}" for item in current)
                if isinstance(current, list) and current
                else "（无）"
            )
            prompt = (
                "你是一名资深绿色施工专家，请基于以下建筑碳排放核算结果给出绿色施工优化建议。\n"
                f"项目：{project_name}\n"
                f"总排放：{total_emission} tCO2e　面积强度：{intensity} tCO2e/m²\n"
                f"分阶段占比：{stage_text}\n"
                "已有的静态建议（请勿重复）：\n"
                f"{current_text}\n\n"
                "要求：\n"
                "1. 输出 3~6 条编号行动建议，重点针对排放占比最高的阶段给出可落地的具体措施；\n"
                "2. 每条 ≤120 字；\n"
                "3. 不得编造规范条款号或具体数字；\n"
                "4. 只输出编号建议，不要其他说明。"
            )
        if is_demo:
            prompt += "\n\n注：本次核算/评估使用了演示数据，请在建议结尾注明「以上建议基于演示数据，仅供演示参考」。"
        return self._generate(prompt)

# 06 Agent 与算法设计文档

## 1. 总体原则

五个 Agent 在 MVP 中是 LangGraph 的确定性业务节点，不是五个自由聊天机器人。

```text
SafetyAgent
  → RagAgent
  → WorkOrderAgent
  → WorkerCareAgent
  → ReportAgent
```

如果没有隐患：

```text
SafetyAgent
  → ReportAgent（生成“今日未发现新增隐患”的预览）
  → END
```

## 2. 共享状态

```python
class WorkflowState(TypedDict, total=False):
    task_id: str
    project_id: str
    upload_id: str
    image_path: str
    location: str
    work_type: str
    description: str
    requested_by: str

    hazards: list[dict]
    risk_level: str
    evidence: list[dict]
    work_order_draft: dict | None
    worker_message: str
    report_preview: str

    agent_trace: list[dict]
    review_required: bool
    is_simulated: bool
    provider_info: dict[str, str]
    errors: list[dict]
```

每个节点只返回自己更新的字段。

## 3. Provider 抽象

### VisionProvider

```python
class VisionProvider(Protocol):
    def analyze(self, image_path: str, context: dict) -> VisionResult:
        ...
```

### RetrievalProvider

```python
class RetrievalProvider(Protocol):
    def search(self, query: str, filters: dict, top_k: int) -> list[Evidence]:
        ...
```

### TextProvider

```python
class TextProvider(Protocol):
    def generate_worker_message(self, payload: dict) -> str:
        ...

    def generate_report(self, payload: dict) -> str:
        ...
```

## 4. SafetyAgent

### 4.1 MVP 模式

`MockVisionProvider` 根据显式 `demo_scenario` 返回结果：

- `no_helmet`；
- `missing_guardrail`；
- `normal`。

若未传 `demo_scenario`，使用默认 `no_helmet`，并强制返回：

```json
{
  "is_simulated": true,
  "provider": "mock"
}
```

不得伪装为真实图像识别。

### 4.2 真实视觉模式

推荐后续采用：

```text
YOLO 目标检测
  → person / helmet / vest / guardrail
  → 人员与 PPE 空间关联
  → 风险规则
  → 可选多模态模型复核复杂场景
```

### 4.3 人员与安全帽关联

对每个人员框，定义头部区域为人员框上部 35%。若安全帽中心落在头部区域，则视为匹配。

```python
head_bottom = person_y1 + 0.35 * (person_y2 - person_y1)
matched = (
    person_x1 <= helmet_center_x <= person_x2
    and person_y1 <= helmet_center_y <= head_bottom
)
```

需要处理多个安全帽和多个人员，使用距离或 IoU 进行一对一贪心匹配。

### 4.4 风险规则

示例：

```python
RISK_RULES = {
    "no_helmet": {
        "risk_level": "high",
        "base_score": 90,
        "assignee_role": "safety_officer",
        "deadline_hours": 4
    },
    "missing_guardrail": {
        "risk_level": "critical",
        "base_score": 98,
        "assignee_role": "project_manager",
        "deadline_hours": 2
    },
    "no_safety_vest": {
        "risk_level": "medium",
        "base_score": 65,
        "assignee_role": "safety_officer",
        "deadline_hours": 24
    }
}
```

综合风险等级取最高等级，不取平均。

### 4.5 输出

- hazards；
- risk_level；
- review_required=true；
- 标注图相对 URL；
- provider 信息；
- trace。

## 5. RagAgent

### 5.1 MVP 本地检索

使用 `safety_standards.json`，每条结构：

```json
{
  "id": "STD-HELMET-001",
  "category": "个人防护",
  "hazard_types": ["no_helmet"],
  "source": "项目安全生产管理制度",
  "article": "第12条",
  "content": "进入施工现场的人员应正确佩戴安全帽。",
  "keywords": ["安全帽", "个人防护", "施工现场"]
}
```

检索评分：

```text
hazard_type 精确匹配：+5
标题/分类关键词命中：每个 +2
正文关键词命中：每个 +1
```

按分数排序，返回 Top 3。低于最小分数不返回。

### 5.2 Chroma 模式

后续实现：

- 文档按条款切分；
- 元数据保存来源、条款、类别和适用风险；
- 向量召回 Top K；
- 可加关键词重排；
- 返回原文，不让 LLM 编造条款。

### 5.3 无依据处理

若无足够依据：

- `evidence=[]`；
- 写入 trace；
- `review_required=true`；
- 工单注明“规范依据待人工补充”；
- 禁止生成虚构条款。

## 6. WorkOrderAgent

### 6.1 硬字段由规则生成

- 工单 ID；
- 风险等级；
- 状态；
- 责任角色；
- 截止时间；
- 项目；
- 位置；
- 来源任务；
- 是否人工确认。

### 6.2 软字段

MVP 由模板生成：

- 标题；
- 问题描述；
- 整改要求；
- 复查要求。

后续 LLM 必须使用结构化输出并由 Pydantic 校验。

### 6.3 工单草稿

Agent 只生成草稿，不直接创建正式工单。正式工单由 `POST /work-orders` 创建。

## 7. WorkerCareAgent

### 7.1 目标

把专业整改要求转成尊重、简短、明确的工友提醒。

规则：

- 不超过 100 个中文字符；
- 高风险必须出现“暂停作业”；
- 不训斥；
- 不添加处罚、责任或未提供的法规；
- 明确下一步动作；
- 返回纯文本。

模板示例：

```text
师傅，请先暂停一下作业。请正确戴好安全帽并扣紧下颌带，
待安全员确认后再继续施工。
```

## 8. ReportAgent

### 8.1 统计由 SQL 完成

统计：

- 今日隐患总数；
- 各风险等级数量；
- 各工单状态数量；
- 今日新建和关闭数量；
- 临近截止工单；
- 高频隐患类型。

### 8.2 文本生成

MVP 用模板；LLM 模式只负责组织语言，输入为结构化统计，禁止修改数字。

日报结构：

1. 今日巡检概况；
2. 主要风险；
3. 整改进度；
4. 待协调事项；
5. 明日重点。

## 9. LangGraph 路由

```python
START -> safety

if hazards:
    safety -> rag -> work_order -> worker_care -> report -> END
else:
    safety -> report -> END
```

节点异常策略：

- 视觉失败：整个任务失败；
- RAG 失败：继续生成工单，但标记依据待补充；
- WorkerCare 失败：使用本地模板；
- Report 失败：使用本地模板；
- 所有异常进入 trace 和 agent_runs.error_message。

## 10. 执行轨迹

每个节点写：

```json
{
  "agent": "RagAgent",
  "status": "completed",
  "message": "检索到 2 条规范依据",
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 43
}
```

## 11. 安全边界

- 所有结果标记为辅助建议；
- 工程结论必须人工复核；
- 置信度不等于法规符合性；
- 模拟结果必须显式标注；
- 无依据时不得编造；
- 工单必须人工确认；
- 日报数字必须来源于数据库。

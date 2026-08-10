# API 摘要

所有接口统一返回：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {"request_id": "..."}
}
```

认证使用 Bearer Token。登录接口返回的 token 是本地开发 JWT。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 登录 |
| POST | `/api/v1/auth/register` | 注册 |
| GET | `/api/v1/auth/me` | 当前用户 |
| PATCH | `/api/v1/users/me` | 更新当前用户的姓名、手机号；用户名、角色和激活状态不可修改 |
| POST | `/api/v1/users/me/password` | 校验旧密码并修改当前用户密码 |
| GET | `/api/v1/projects` | 项目列表 |
| POST | `/api/v1/projects` | 创建项目 |
| GET | `/api/v1/dashboard/summary` | 首页统计 |
| POST | `/api/v1/safety/analyze` | 上传图片并运行五 Agent |
| GET | `/api/v1/safety/tasks` | 分析任务历史 |
| GET | `/api/v1/safety/tasks/{task_id}` | 分析详情 |
| POST | `/api/v1/work-orders` | 确认工单草稿 |
| GET | `/api/v1/work-orders` | 工单列表 |
| GET | `/api/v1/work-orders/{id}` | 工单详情 |
| PATCH | `/api/v1/work-orders/{id}/status` | 状态流转；关闭必须提供复查备注 |
| POST | `/api/v1/work-orders/{id}/attachments` | 保存整改图片并关联工单事件 |
| POST | `/api/v1/reports/daily/generate` | 生成日报 |
| GET | `/api/v1/reports/daily` | 日报历史 |
| POST | `/api/v1/worker-care/chat` | 工友助手问答（知识库 RAG 检索，未命中回退模板） |
| POST | `/api/v1/worker-care/transcribe` | 语音转写（multipart；未配置 ASR 时 `available=false`） |
| GET | `/api/v1/knowledge/documents` | 已导入规范文档/条款 |
| GET | `/api/v1/knowledge/search` | 规范知识检索 |
| GET | `/api/v1/knowledge/index/status` | Provider、索引状态、文档数和条款数 |
| POST | `/api/v1/knowledge/reindex` | 按当前知识源重建 Chroma 索引 |
| POST | `/api/v1/knowledge/chat` | 统一 RAG 问答：规范条文 + 风险提示 + 现场概况（可选 LLM 总结） |
| POST | `/api/v1/quality/analyze` | 质量巡检分析（上传图片 → 五 Agent 缺陷闭环） |
| GET | `/api/v1/quality/tasks` | 质量任务列表 |
| GET | `/api/v1/quality/tasks/{id}` | 质量任务详情 |
| GET | `/api/v1/quality/status` | 质量模块状态 |
| POST | `/api/v1/green/analyze` | 绿色碳排核算（JSON：材料/运输/能耗 → 分阶段排放） |
| GET | `/api/v1/green/analyses` | 碳排核算历史（可按 `project_id` 过滤） |
| GET | `/api/v1/green/analyses/{id}` | 碳排核算详情 |
| GET | `/api/v1/green/analyses/{id}/report` | 下载碳排核算 Word 报告（`.docx`，附 `Content-Disposition`） |
| GET | `/api/v1/green/benchmark` | 同类项目碳排强度 z-score 对标（可按 `project_id` 高亮当前项目） |
| GET | `/api/v1/green/factors` | 排放因子库（含 verified 标记） |
| GET | `/api/v1/green/status` | 绿色模块状态 |
| GET | `/api/v1/stats/anomalies` | 隐患/缺陷历史 z-score 异常波动检测（safety/quality） |
| GET | `/api/v1/health` | 健康检查，包含 Provider 与 SQLite 连接状态 |

健康检查的 `data.database` 会由后端执行真实 `SELECT 1` 得出；`data.capabilities` 是只读的 Provider/模块预检结果。每项包含 `key`、`name`、`provider`、`status`、`is_simulated`、`reason` 和 `next_step`。`status` 取值为：`available`（本地能力已就绪）、`configured`（配置或本地资源完整但尚未执行 smoke test）、`simulated`（离线模拟）、`not_configured`（缺少可选配置或索引）和 `unavailable`（依赖或资源不可用）。

```json
{
  "status": "connected",
  "dialect": "sqlite",
  "persistent": true
}
```

用户资料与密码接口示例：

```http
PATCH /api/v1/users/me
Content-Type: application/json

{"real_name":"现场负责人","phone":"13800000000"}
```

```http
POST /api/v1/users/me/password
Content-Type: application/json

{"current_password":"旧密码","new_password":"新密码至少8位","new_password_confirm":"新密码至少8位"}
```

## 图片分析

`POST /api/v1/safety/analyze` 使用 `multipart/form-data`，字段包括：

- `project_id`：项目 ID；
- `location`：位置；
- `work_type`：作业类型；
- `description`：现场描述，可选；
- `image`：jpg/png/webp 图片；
- `demo_scenario`：可选的离线演示场景，如 `no_helmet`、`missing_guardrail`、`no_safety_vest`、`normal`。

返回值包含 `risk_level`、`hazards`、`evidence`、`work_order_draft`、`worker_message`、`agent_trace` 和 `is_simulated`。

## 规范知识检索

`GET /api/v1/knowledge/search?q=安全帽` 的每条命中包含 `source`、`article`、`content`、`score` 和 `metadata`，并保留 `document_id`、标题、分类、版本和生效日期。没有充分依据时 `data` 为 `[]`。

`GET /api/v1/knowledge/index/status` 返回当前 `provider`（`local_keyword` 或 `chroma`）、`indexed`、`document_count`、`clause_count` 和 Chroma collection 信息。`POST /api/v1/knowledge/reindex` 在 Chroma 模式下读取 `KNOWLEDGE_JSON_PATH` 并重建持久化投影；关键词模式保持 JSON 直读，不需要向量重建。

### 统一 RAG 问答

`POST /api/v1/knowledge/chat` 提交 `{ "question": "...", "project_id": null, "use_llm": null }`，返回四层结构：

- `answer`：按「【一、规范与标准条文】」「【二、相关风险提示】」「【三、现场概况】」分段拼装；无命中时给兜底文案，不编造条款；
- `citations`：命中的条款来源（`source`/`article`/`title`/`score`）；
- `retrieval`：`{ clauses: {ready, count}, risk_tip: {included, hazard_types}, site: {included, project_id} }`；
- `llm`：`{ used, model, error }`，未配置 LLM 或调用失败时 `used=false` 自动降级为离线检索拼装（`mode="rag_only"`）。

传 `project_id` 时先校验项目访问权限，再追加近 7 天现场概况（隐患/缺陷计数按模块分、风险等级分布、未闭环整改工单数）。

## 工友助手问答

`POST /api/v1/worker-care/chat` 提交 `{ project_id, question }`。回答由知识库 RAG 检索生成：命中规范条款时把要求转成简短工友友好提醒并内嵌《来源·条款》（高风险项提示暂停作业），`answer_source="rag"`、`is_simulated=false`、附 `citations`（来源/条款/标题/相似度）；未命中或检索 Provider 不可用时回退本地模板，`answer_source="template"`、`is_simulated=true`、`citations=[]`。

## 语音转写

`POST /api/v1/worker-care/transcribe` 上传 multipart 表单：`project_id` + `audio` 音频文件（如 `voice.webm`）。返回：

- `available`：`true`=转写成功；`false`=未配置 ASR Provider（不报错）；
- `text`：转写文字（`available=false` 时为 `""`）；
- `reason`：未配置时给中文原因，否则 `null`；
- `provider`：实际 Provider 名（未配置时为 `"off"`）。

未配置时前端自动使用浏览器 Web Speech（`SpeechRecognition`，zh-CN）本地识别，无需后端；要接 whisper 兼容服务，设 `SPEECH_PROVIDER=openai_compatible`（复用 `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL`，POST `{base_url}/audio/transcriptions`）。

## 工单列表筛选

`GET /api/v1/work-orders` 支持 `project_id`、`status`、`risk_level`、`assignee_user_id`、`deadline_from` 和 `deadline_to` 查询参数。日期参数使用 ISO 8601 时间；详情响应会返回 `file_url`、`annotated_url` 和 `evidence`。每条工单带 `assignee_name`（负责人姓名，来自 `real_name`；未指派或查不到时为 `null`）。

## 绿色碳排对标

`GET /api/v1/green/benchmark?project_id=` 对用户可见项目集合做碳排强度（tCO2e/m²）z-score 对标，纯 `statistics` 计算，不引入 numpy：

- 每个项目取**最新一条有 `area_m2` 的核算**算强度；样本不足 2 个或标准差为 0 时返回 `available=false` + 中文 `reason`；
- 返回 `count`、`mean`、`std`、按强度升序的 `items`（每项含 `rank`、`z`、`better_than_pct`），`z` 为负表示优于均值；`current` 高亮当前项目；
- `better_than_pct` = 严格劣于当前项目的占比 × 100。

## 异常波动检测

`GET /api/v1/stats/anomalies?project_id=&module=safety&days=30&z_threshold=2.5` 对窗口内按天计数的隐患/缺陷数量做 z-score 检测（纯 `statistics`）：

- `module` 仅接受 `safety`/`quality`，按 `metadata_json.module` Python 侧分拣（`quality` 需 `module=="quality"`；`safety` 兼容无 module 键的历史行）；`days` 限制在 [3, 90]，`z_threshold` 限制在 (0, 10]；
- 补齐窗口内空日期为 0；空数据返回 `available=false`；标准差为 0 时所有天均非异常；
- 返回 `{available, project_id, module, days, z_threshold, total_days, mean, std, anomaly_days, ratio, samples:[{date, count, z, anomaly}]}`。

## 风险评分

`HazardRead`/`QualityHazardRead` 增加可选字段 `risk_score`（0-100 整数）。视觉映射（`mapping.py`/`quality_mapping.py`）在生成隐患时计算并写入；历史数据缺 `risk_score` 时后端读取接口会用 `rules/risk_rules.py` 的 `compute_risk_score` 按隐患类型基准分、风险等级、置信度现算兜底，因此接口返回始终非空。

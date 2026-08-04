# 核心算法与工作流

## 五 Agent 工作流

```text
上传图片
  → SafetyAgent：读取图片并识别风险
  → RagAgent：按风险关键词检索本地规范
  → WorkOrderAgent：生成待人工确认的工单草稿
  → WorkerCareAgent：生成简短关怀和整改提示
  → ReportAgent：输出统计摘要和日报草稿
```

正常图片会跳过中间风险处置节点，并保留完整 trace；有风险图片的正式工单只能通过 `POST /work-orders` 人工确认创建。

## 离线风险规则

MockVision 使用可重复的演示场景或文件名关键词：

- `no_helmet`：未佩戴安全帽，高风险；
- `no_vest`：未穿反光背心，中风险；
- `fall_risk`：临边/高处坠落风险，高风险；
- `normal`：无明显风险。

生产 Provider 接口位于 `backend/app/providers/vision/`，可以替换为 Ultralytics 或外部视觉服务，但必须继续返回统一的 `VisionResult` 并标记模拟性。

## 规范检索

`RETRIEVAL_PROVIDER=local_keyword` 时，`LocalKeywordRetrievalProvider` 对 `data_demo/standards/safety_standards.json` 做离线关键词匹配；没有命中时返回空证据，不生成虚构条款。

`RETRIEVAL_PROVIDER=chroma` 时，规范先被解析为带有 `document_id`、来源、标题、条款号、分类、正文、版本、生效日期和扩展 metadata 的 `KnowledgeClause`，再写入持久化 `buildwise-standards` collection。Chroma 使用本地可重复的中文字符 2/3-gram embedding，不下载外部模型；检索首先由 Chroma 执行 cosine 向量查询，再用来源文本的确定性重排和风险过滤控制低置信度结果。返回内容始终来自原文，不让文本模型补写条款。

JSON 可直接提供条款号；PDF/DOCX 只按显式的 `第12条`、`第4.3.1条`、`Article 12` 或数字层级标题切分。没有条款标题的文档会被拒绝，避免把全文伪装成不存在的条款。导入使用 `python scripts/ingest_knowledge.py`，重复条款按稳定 ID 增量 upsert，`--rebuild` 会重建 collection。

## 工单状态机

```text
pending → in_progress → pending_review → closed
   └──────────────────────────────→ cancelled
```

安全员可推进到 `pending_review`，项目经理可关闭或取消。每次变化写入 `work_order_events`。

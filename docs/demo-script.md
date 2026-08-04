# BuildWise 主 Demo

## 浏览器闭环

1. 启动后端、前端，确认 `/api/v1/health` 返回 `status=ok`。
2. 使用 `safety / BuildWise123!` 登录，进入“现场安全分析”。
3. 选择演示项目，上传 `data_demo/images/safety_no_helmet.jpg`，演示场景选择 `no_helmet`。
4. 验证隐患名称、风险等级、置信度、检测框、规范依据、工友提醒和五 Agent 执行轨迹；模拟结果必须显示 `is_simulated=true`。
5. 点击“确认创建正式工单”，重复点击或重复提交应返回同一未关闭工单，不产生重复任务。
6. 在工单详情依次执行：待整改 → 整改中 → 待复查。关闭时填写“复查通过，整改照片已核验”等备注；空备注应被拒绝。
7. 上传整改图片，刷新工单详情，确认原图、标注图、规范依据、附件和状态时间线仍可见。
8. 使用 `manager / BuildWise123!` 登录，确认项目经理可以完成最后的关闭操作。
9. 进入“日报中心”，选择项目和当天日期，生成日报并确认数字与当前 SQL 数据一致；无数据日期也应能生成零统计报告。
10. 返回“安全历史”，点击任务“查看”，确认 `/safety/analyze?task=...` 能直接恢复完整结果，不要求再次上传图片。

## 离线演示场景

- `no_helmet`：高风险未佩戴安全帽；
- `missing_guardrail`：重大风险临边防护缺失；
- `no_safety_vest`：中风险未穿安全背心；
- `normal`：无新增隐患。

演示图片只用于本地离线流程，实际检测结果会标记为模拟。真实 Provider 的模型、密钥、网络和许可不属于 Demo 前置条件。

## 自动化验证

Windows：

```powershell
cd E:\cc项目\buildwise-agent
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\test_runbooks.ps1
```

后端全量测试和前端检查：

```powershell
cd backend
..\backend\venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run test:unit -- --run
npm run type-check
npm run build
```

# 08 启动、部署与运维文档

## 1. 本地启动

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：`http://localhost:5173`
- Swagger：`http://localhost:8000/docs`

## 2. 一键开发脚本

Codex 需要提供：

- `scripts/dev.ps1`：Windows 下同时启动前后端；
- `scripts/dev.sh`：Unix 下同时启动前后端；
- 脚本不能静默吞掉错误。

## 3. Docker Compose

至少包含：

- backend；
- frontend；
- 可选 postgres profile。

默认可继续使用 SQLite 挂载卷。前端生产镜像由 Nginx 提供静态文件，并反向代理 `/api`。

## 4. README 必须包含

- 项目介绍；
- 技术架构；
- 目录说明；
- 环境要求；
- 本地启动；
- Docker 启动；
- 演示账号；
- 主 Demo 脚本；
- 模拟模式说明；
- 真实 YOLO、Chroma、LLM 的切换方式；
- 测试命令；
- 常见问题；
- 人工复核边界。

## 5. 生产注意事项

- 更换 `SECRET_KEY`；
- 使用 PostgreSQL；
- 关闭 DEBUG；
- 限制 CORS；
- 使用对象存储；
- 使用 HTTPS；
- 增加速率限制；
- 使用后台任务处理较慢模型；
- 使用集中式日志；
- 数据和模型许可需要人工确认。

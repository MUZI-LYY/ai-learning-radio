# CLAUDE.md

本文件为在仓库中工作的 AI 编程助手提供项目约束。先阅读根目录 `README.md`、`CONTRIBUTING.md` 和相关测试，再进行最小范围修改。

## 架构概览

- `frontend/`：Next.js 16 + React 19 的移动端优先 Web，默认端口 3001。
- `backend/app/main.py`：FastAPI 入口，默认端口 8002。
- `backend/app/api/v1/`：认证、学习资料、任务、节目、事件与新闻 API。
- `backend/app/services/agent.py`：统一的 `LearningRadioAgent` 能力入口。
- `backend/app/services/generation/`：私人节目持久化生成工作流。
- `backend/app/services/news/`：新闻来源、抓取、频道与节目生成。
- `backend/app/services/providers/`：LLM、TTS、音色和成本边界。
- `backend/app/services/storage/`：本地私有文件存储；不要与运行时 `storage/` 目录混淆。
- `backend/app/worker/main.py`：领取生成任务并维护 mock 新闻的独立 Worker。
- `backend/app/models/`、`backend/alembic/`：SQLAlchemy 模型与数据库迁移。

数据流：浏览器调用 FastAPI；API 把长任务写入数据库；Worker 分步执行任务并调用 mock 或真实 Provider；前端轮询任务状态并读取节目、逐字稿和复习内容。

## 关键开发路径

1. API 契约变化：同步修改 `backend/app/schemas/`、`backend/app/api/v1/`、`frontend/lib/api.ts` 和相关测试。
2. 数据模型变化：新增 Alembic 迁移，不修改已经发布的历史迁移。
3. 生成逻辑变化：保持任务步骤幂等、错误可恢复，并继续经过预算和 Provider 开关。
4. 文件处理变化：所有用户路径必须经过 storage 服务解析，禁止根据用户输入直接拼接路径。
5. 界面变化：保持移动端优先、键盘可达，并为纯逻辑增加 Node 测试。

## 安装、运行与测试

```bash
./setup.sh

# API / Worker / Web（分别在三个终端）
cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8002
cd backend && uv run python -m app.worker.main
cd frontend && npm run dev

# 后端质量检查
cd backend && uv run ruff check . && uv run pytest

# 前端质量检查
cd frontend && npm test && npm run lint && npm run build

# 数据库迁移
cd backend && uv run alembic upgrade head
```

依赖必须通过 `uv sync --locked` 和 `npm ci` 验证。修改依赖时同时更新 `backend/uv.lock` 或 `frontend/package-lock.json`。

## 隐私与安全约束

- 不读取、输出、记录或提交 `.env`、API Key、Cookie、数据库、用户资料、生成音频或私有存储内容。
- 测试和自动化默认使用 `LLM_PROVIDER=mock`、`TTS_PROVIDER=mock`、`PROVIDER_CALLS_ENABLED=false`、`PROJECT_MONTHLY_BUDGET_CNY=0`。
- 未经明确授权，不启用或调用真实 Provider；真实调用可能外传文本并产生费用。
- 日志只记录必要的 ID、状态和错误类型，不记录上传正文、节目全文、凭证或会话值。
- 不降低生产配置校验，不绕过预算熔断、邀请认证、路径边界或上传限制。
- 新增示例时只使用虚构数据、回环地址和空凭证；不要加入个人绝对路径或内部基础设施信息。
- 涉及安全漏洞时遵循 `SECURITY.md`，不要把可利用细节写入公开 Issue。

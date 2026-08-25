# 贡献指南

感谢你帮助改进 AI 学习电台。项目仍处于早期阶段，优先接受范围清晰、便于验证且不扩大隐私风险的改动。

## 开始之前

- Bug、文档错误和功能建议请先搜索现有 Issue。
- 较大功能、数据模型变化或新 Provider 接入，请先提交 Feature Request 讨论范围。
- 安全漏洞不要公开披露，请遵循 [SECURITY.md](SECURITY.md)。
- 参与项目即表示同意遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 本地开发

需要 Python 3.11、uv、Node.js 24 和 npm：

```bash
git clone https://github.com/liyongyan129-maker/ai-learning-radio.git
cd ai-learning-radio
./setup.sh
```

安装脚本不会启动服务，默认保持 mock Provider。运行方式见 [README.md](README.md)。不要把真实凭证放入测试、日志、提交或 Issue。

## 分支和提交

1. 从最新 `main` 创建短生命周期分支，例如 `feature/program-search` 或 `fix/task-retry`。
2. 只修改与 Issue/目标相关的文件；不要顺手格式化整个仓库。
3. 推荐使用 Conventional Commits，例如 `feat(news): add source health status`。
4. 提交前运行与改动相关的完整检查。

## 必须通过的检查

```bash
cd backend
uv run ruff check .
uv run pytest

cd ../frontend
npm test
npm run lint
npm run build
```

如果修改了依赖，请提交相应锁文件。如果修改了 SQLAlchemy 模型，请添加 Alembic 迁移并验证从空数据库升级到 `head`。

## Pull Request 要求

- 清楚说明问题、方案、验证结果和已知限制。
- 关联相关 Issue；界面变化可附不含私人数据的截图。
- 新行为应配测试，无法测试时说明原因和人工验证步骤。
- API 契约变化应同步更新后端 schema、前端调用和文档。
- 保持 mock 模式可用，不在 CI 或测试中调用真实 LLM/TTS。
- 确认没有 `.env`、密钥、用户内容、数据库、音频或机器绝对路径。

维护者可能要求缩小范围或拆分 PR。提交 PR 并不保证合并；优先级取决于项目方向、维护成本、安全性与兼容性。

## 许可证

提交贡献即表示你有权提供这些内容，并同意按项目的 [Apache License 2.0](LICENSE) 授权。不要提交授权不清的代码、文本、图片、音频、数据集或模型输出。

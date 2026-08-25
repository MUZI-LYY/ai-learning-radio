# 生成结构化 JSON 截断修复 TDD 记录

## 问题与结论

- 用户上传和正文解析均已成功，失败发生在 `summarizing` 分块摘要步骤。
- 失败响应在约 8KB JSON 附近出现 `Unterminated string` / `Expecting value`，符合模型输出达到长度限制或响应末尾不完整的特征。
- 原流程会自动重试三次并进入失败终态，但把底层 JSON 解析异常直接展示给用户，且失败后缺少原任务重试入口。

## 修复内容

1. 请求真实 LLM 时显式设置 `LLM_MAX_OUTPUT_TOKENS=8192`。
2. 摘要结构限制为每块最多 12 个要点；单条内容和来源标记均有长度上限。
3. `chunk_summary_v2` 要求模型提炼而非大段照搬，控制结构化输出规模。
4. 识别 `finish_reason=length/max_tokens` 和末尾 JSON 截断，分别返回稳定错误码。
5. JSON、Pydantic 和未知内部异常不再把解析细节、路径或资料片段写入任务错误信息。
6. 三次自动重试失败后任务明确进入 `failed`，前端停止 Loading。
7. 失败页提供“重新生成”按钮；只有用户主动点击才复用已解析资料重新发送，不重复扣上传额度。

## RED / GREEN 证据

| 行为 | RED | GREEN |
|---|---|---|
| 长度截断识别 | 缺少响应级解析函数，测试导入失败 | `finish_reason=length` 映射为 `LLM_OUTPUT_TRUNCATED` |
| 安全错误提示 | 直接抛出 `JSONDecodeError` 原文 | 原始 `Unterminated string` / `Expecting value` 不出现在接口消息中 |
| 失败终态 | 缺少专门错误码与最终提示 | 三次重试后为 `failed`，步骤 attempts=3 |
| 用户确认重试 | 重试接口返回 404 | 点击后任务进入 `retry_wait`，步骤 attempts 清零，不重新扣额度 |

## 验证结果

- 后端完整测试：`56 passed`
- 后端 Ruff：通过
- 前端 Node 测试：`5 passed`
- 前端 ESLint：通过
- 前端生产构建：通过
- `git diff --check`：通过

## 安全复核

- 排查和测试只读取任务状态、步骤、错误类型及资料字符数，没有输出上传正文或完整模型响应。
- API 不记录 Prompt 和上传资料；Worker 日志只记录任务 ID。
- 重试接口继续执行任务所有权校验，仅允许失败在摘要步骤的任务重试。
- 真实外部模型验收未自动执行：再次发送既有资料需要用户在失败页主动点击“重新生成”。

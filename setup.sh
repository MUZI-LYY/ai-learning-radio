#!/usr/bin/env bash

set -euo pipefail

readonly PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

fail() {
  printf '错误：%s\n' "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "未找到 $1。$2"
}

require_command python3.11 "请安装 Python 3.11。"
require_command uv "请安装 uv：https://docs.astral.sh/uv/"
require_command node "请安装 Node.js 24。"
require_command npm "请安装与 Node.js 配套的 npm。"

python_version="$(python3.11 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
node_version="$(node --version)"
node_major="${node_version#v}"
node_major="${node_major%%.*}"

[[ "$python_version" == 3.11.* ]] || fail "需要 Python 3.11，当前为 $python_version。"
[[ "$node_major" =~ ^[0-9]+$ ]] || fail "无法识别 Node.js 版本：$node_version。"
(( node_major >= 24 )) || fail "需要 Node.js 24 或更新版本，当前为 $node_version。"

printf '工具检查通过：Python %s，uv %s，Node.js %s，npm %s\n' \
  "$python_version" "$(uv --version)" "$node_version" "$(npm --version)"

umask 077
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  printf '已创建 .env（mock Provider，真实调用关闭）。\n'
else
  printf '保留现有 .env，不覆盖。\n'
fi

if [[ ! -f "$PROJECT_DIR/frontend/.env.local" ]]; then
  cp "$PROJECT_DIR/frontend/.env.example" "$PROJECT_DIR/frontend/.env.local"
  printf '已创建 frontend/.env.local。\n'
else
  printf '保留现有 frontend/.env.local，不覆盖。\n'
fi

printf '安装后端锁定依赖……\n'
uv sync --project "$PROJECT_DIR/backend" --locked

printf '安装前端锁定依赖……\n'
npm ci --prefix "$PROJECT_DIR/frontend"

printf '执行数据库迁移（强制 mock Provider 且关闭真实调用）……\n'
(
  cd "$PROJECT_DIR"
  LLM_PROVIDER=mock \
  TTS_PROVIDER=mock \
  PROVIDER_CALLS_ENABLED=false \
  PROJECT_MONTHLY_BUDGET_CNY=0 \
  PYTHONPATH="$PROJECT_DIR/backend" \
    uv run --project "$PROJECT_DIR/backend" alembic \
      -c "$PROJECT_DIR/backend/alembic.ini" upgrade head
)

printf '\n初始化完成。脚本未启动服务，也未调用真实 Provider。\n'
printf '请按 README.md 分别启动 API、Worker 和 Web。\n'

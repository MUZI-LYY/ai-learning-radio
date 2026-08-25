"""带版本号的 Prompt 文件加载。

Prompt 不散落在路由或页面代码中，生成结果可追溯到 Prompt 版本。
"""

from __future__ import annotations

from pathlib import Path
from string import Template

_PROMPT_DIR = Path(__file__).parent

PROMPT_VERSIONS: dict[str, str] = {
    "chunk_summary": "chunk_summary_v2",
    "lesson_generation": "lesson_generation_v2",
    "lesson_revision": "lesson_revision_v1",
    "news_agent_system": "news_agent_system_v1",
    "news_script": "news_script_v2",
}


def load_prompt(name: str) -> str:
    filename = f"{PROMPT_VERSIONS[name]}.md"
    return (_PROMPT_DIR / filename).read_text(encoding="utf-8")


def render_prompt(name: str, **variables: str) -> str:
    return Template(load_prompt(name)).safe_substitute(**variables)


def prompt_version(name: str) -> str:
    return PROMPT_VERSIONS[name]

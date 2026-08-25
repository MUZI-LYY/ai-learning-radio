"""应用配置。

所有敏感配置只从环境变量或本地 `.env` 读取，绝不硬编码真实密钥。
`backend/app/core/config.py` 只包含变量名、默认值与校验规则。
"""

from __future__ import annotations

from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/ 的上一级），用于解析相对存储路径。
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_APP_SECRET = "dev-only-secret-change-me"  # pragma: allowlist secret
DEFAULT_INVITE_CODE_PEPPER = "dev-only-pepper-change-me"  # pragma: allowlist secret


class Settings(BaseSettings):
    """运行时配置。字段名与 `.env.example` 一一对应。"""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 运行环境 ----
    app_env: str = "development"
    app_secret: str = Field(default=DEFAULT_APP_SECRET, min_length=16)
    backend_host: str = "127.0.0.1"
    backend_port: int = 8002  # 本地开发默认端口
    frontend_origin: str = "http://127.0.0.1:3001"
    cookie_secure: bool = False

    # ---- 认证 ----
    invite_code_pepper: str = Field(default=DEFAULT_INVITE_CODE_PEPPER, min_length=16)
    session_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 天
    invite_rate_limit_window_seconds: int = 300
    invite_rate_limit_max_attempts: int = 10

    # ---- 数据与存储 ----
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"
    private_storage_root: str = str(PROJECT_ROOT / "data" / "private")

    # ---- LLM（火山方舟）----
    llm_provider: str = "mock"  # mock | volcark
    llm_api_key: str = ""
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model_primary: str = "doubao-seed-2-1-pro-260628"
    llm_thinking_mode: str = "disabled"
    llm_timeout_seconds: int = 120
    llm_max_output_tokens: int = 8192

    # ---- TTS（豆包语音，语音技术新版 API Key 接入）----
    tts_provider: str = "mock"  # mock | volc
    tts_api_key: str = ""  # 语音技术控制台创建的 API Key（与方舟 LLM Key 不同）
    tts_base_url: str = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    tts_resource_id: str = "volc.service_type.10029"
    tts_default_voice_key: str = "elegant_youth"
    tts_timeout_seconds: int = 300
    # 保守单价（元 / 千字），用于 TTS 成本估值；真实价格确认后校准
    tts_cost_per_1k_chars_cny: float = 0.2

    # ---- 输入与额度限制 ----
    max_upload_mb: int = 15
    max_extracted_chars: int = 30_000
    daily_private_program_limit: int = 2

    # ---- 成本熔断 ----
    provider_calls_enabled: bool = False
    project_monthly_budget_cny: float = 0.0  # 0 = 未配置，视为禁止真实调用

    # ---- Worker ----
    worker_poll_seconds: int = 3

    @field_validator("backend_port")
    @classmethod
    def _port_range(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("backend_port 必须在 1-65535 之间")
        return v

    @model_validator(mode="after")
    def _validate_production_security(self) -> Self:
        """非开发环境必须显式满足会话、邀请码和 Cookie 安全基线。"""
        if self.is_development:
            return self

        if self.app_secret == DEFAULT_APP_SECRET:
            raise ValueError("生产环境 APP_SECRET 不得使用开发默认值")
        if self.invite_code_pepper == DEFAULT_INVITE_CODE_PEPPER:
            raise ValueError("生产环境 INVITE_CODE_PEPPER 不得使用开发默认值")
        if len(self.app_secret) < 32:
            raise ValueError("生产环境 APP_SECRET 必须至少 32 个字符")
        if len(self.invite_code_pepper) < 32:
            raise ValueError("生产环境 INVITE_CODE_PEPPER 必须至少 32 个字符")
        if self.app_secret == self.invite_code_pepper:
            raise ValueError("生产环境 APP_SECRET 与 INVITE_CODE_PEPPER 必须不同")
        if not self.cookie_secure:
            raise ValueError("生产环境 COOKIE_SECURE 必须为 true")

        origin = urlsplit(self.frontend_origin)
        if origin.scheme.lower() != "https" or not origin.netloc:
            raise ValueError("生产环境 FRONTEND_ORIGIN 必须是有效的 https URL")
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env.strip().lower() in {"development", "dev", "test"}

    @property
    def budget_configured(self) -> bool:
        """月度预算是否已显式配置为正数。未配置视为禁止真实 Provider 调用。"""
        return self.project_monthly_budget_cny > 0

    @property
    def real_provider_allowed(self) -> bool:
        """真实 LLM/TTS 调用是否被允许：需同时满足开关开启与预算已配置。"""
        return self.provider_calls_enabled and self.budget_configured


def get_settings() -> Settings:
    """每次返回最新配置（不缓存），便于测试通过环境变量注入。"""
    return Settings()

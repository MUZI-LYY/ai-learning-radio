"""生产环境配置安全基线测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "app_secret": "a" * 32,
        "invite_code_pepper": "b" * 32,
        "cookie_secure": True,
        "frontend_origin": "https://radio.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_settings_accept_secure_independent_secrets() -> None:
    settings = production_settings()

    assert settings.app_env == "production"
    assert settings.cookie_secure is True


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"app_secret": "dev-only-secret-change-me"}, "APP_SECRET"),  # pragma: allowlist secret
        (  # pragma: allowlist secret
            {"invite_code_pepper": "dev-only-pepper-change-me"},
            "INVITE_CODE_PEPPER",
        ),
        ({"app_secret": "a" * 31}, "APP_SECRET"),
        ({"invite_code_pepper": "b" * 31}, "INVITE_CODE_PEPPER"),
        ({"invite_code_pepper": "a" * 32}, "必须不同"),
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"frontend_origin": "http://radio.example.com"}, "FRONTEND_ORIGIN"),
    ],
)
def test_production_settings_reject_insecure_values(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_development_settings_allow_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.is_development is True
    assert settings.cookie_secure is False

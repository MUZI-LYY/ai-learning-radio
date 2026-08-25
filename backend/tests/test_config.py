"""生产环境配置安全基线测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "frontend_origin": "https://radio.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_settings_accept_https_origin() -> None:
    settings = production_settings()

    assert settings.app_env == "production"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
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

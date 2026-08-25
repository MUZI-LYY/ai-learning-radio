"""LLM 结构化输出边界测试。"""

from __future__ import annotations

import pytest

from app.core.errors import ApiError, ErrorCode
from app.services.providers.llm import _parse_json_response, _request_payload


def test_finish_reason_length_is_reported_as_safe_truncation_error():
    body = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": '{"title":"尚未结束'},
            }
        ]
    }

    with pytest.raises(ApiError) as caught:
        _parse_json_response(body)

    assert caught.value.code == ErrorCode.LLM_OUTPUT_TRUNCATED
    assert "Unterminated string" not in caught.value.message


def test_malformed_json_is_reported_without_exposing_parser_details():
    body = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": '{"title": invalid}'},
            }
        ]
    }

    with pytest.raises(ApiError) as caught:
        _parse_json_response(body)

    assert caught.value.code == ErrorCode.LLM_OUTPUT_INVALID
    assert "Expecting value" not in caught.value.message


def test_request_sets_explicit_output_token_budget():
    payload = _request_payload(
        model="test-model",
        system="rules",
        user="data",
        json_schema={"title": "ChunkSummary", "type": "object"},
        thinking_disabled=True,
        max_output_tokens=8192,
    )

    assert payload["max_tokens"] == 8192
    assert payload["thinking"] == {"type": "disabled"}

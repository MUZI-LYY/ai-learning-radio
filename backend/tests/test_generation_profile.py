"""私人节目根据资料长度选择生成规模。"""

from app.services.generation.workflow import generation_profile


def test_short_source_uses_compact_profile():
    profile = generation_profile(800)

    assert profile.key == "short"
    assert profile.skip_chunk_summary is True
    assert profile.min_narration_chars == 600
    assert profile.max_narration_chars == 1000


def test_medium_source_keeps_summary_and_balanced_length():
    profile = generation_profile(801)

    assert profile.key == "medium"
    assert profile.skip_chunk_summary is False
    assert profile.min_narration_chars == 1100
    assert profile.max_narration_chars == 1800


def test_long_source_keeps_full_program_length():
    profile = generation_profile(4001)

    assert profile.key == "long"
    assert profile.skip_chunk_summary is False
    assert profile.min_narration_chars == 1400
    assert profile.max_narration_chars == 2600

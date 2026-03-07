from datetime import timedelta

import pytest
from src.model.constants import CandleType
from src.util.helpers import parse_timeframe

# ---------------------------------------------------------------------------
# 기본 포맷 — 단순 단위 문자열
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_timeframe_seconds():
    """초 단위 문자열을 올바르게 변환한다."""
    assert parse_timeframe("1s") == timedelta(seconds=1)


@pytest.mark.unit
def test_parse_timeframe_minutes():
    """분 단위 문자열을 올바르게 변환한다."""
    assert parse_timeframe("5m") == timedelta(minutes=5)


@pytest.mark.unit
def test_parse_timeframe_hours():
    """시 단위 문자열을 올바르게 변환한다."""
    assert parse_timeframe("1h") == timedelta(hours=1)


@pytest.mark.unit
def test_parse_timeframe_days():
    """일 단위 문자열을 올바르게 변환한다."""
    assert parse_timeframe("1d") == timedelta(days=1)


@pytest.mark.unit
def test_parse_timeframe_weeks():
    """주 단위 문자열을 올바르게 변환한다."""
    assert parse_timeframe("1w") == timedelta(weeks=1)


@pytest.mark.unit
def test_parse_timeframe_large_minutes():
    """240m 처럼 큰 분 값도 올바르게 변환한다."""
    assert parse_timeframe("240m") == timedelta(minutes=240)


# ---------------------------------------------------------------------------
# candle.Xm / candle.Xs 포맷 — CandleType.value 직접 전달
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_timeframe_candle_second():
    """candle.1s 포맷을 1초 timedelta로 변환한다."""
    assert parse_timeframe("candle.1s") == timedelta(seconds=1)


@pytest.mark.unit
def test_parse_timeframe_candle_1m():
    """candle.1m 포맷을 1분 timedelta로 변환한다."""
    assert parse_timeframe("candle.1m") == timedelta(minutes=1)


@pytest.mark.unit
def test_parse_timeframe_candle_3m():
    """candle.3m 포맷을 3분 timedelta로 변환한다."""
    assert parse_timeframe("candle.3m") == timedelta(minutes=3)


@pytest.mark.unit
def test_parse_timeframe_candle_240m():
    """candle.240m 포맷을 240분 timedelta로 변환한다."""
    assert parse_timeframe("candle.240m") == timedelta(minutes=240)


@pytest.mark.unit
def test_parse_timeframe_all_candle_types():
    """모든 CandleType 값이 ValueError 없이 timedelta로 변환된다."""
    expected = {
        CandleType.SECOND: timedelta(seconds=1),
        CandleType.MINUTE: timedelta(minutes=1),
        CandleType.MINUTE_3: timedelta(minutes=3),
        CandleType.MINUTE_5: timedelta(minutes=5),
        CandleType.MINUTE_10: timedelta(minutes=10),
        CandleType.MINUTE_15: timedelta(minutes=15),
        CandleType.HALF_HOUR: timedelta(minutes=30),
        CandleType.HOUR: timedelta(minutes=60),
        CandleType.HOUR_4: timedelta(minutes=240),
    }
    for candle_type, expected_delta in expected.items():
        assert parse_timeframe(candle_type.value) == expected_delta, (
            f"{candle_type.value} should map to {expected_delta}"
        )


# ---------------------------------------------------------------------------
# 대소문자 구분 없음
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_timeframe_uppercase_is_accepted():
    """대문자 단위도 소문자로 정규화되어 처리된다."""
    assert parse_timeframe("5M") == timedelta(minutes=5)


# ---------------------------------------------------------------------------
# 잘못된 포맷 — ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_timeframe_invalid_raises_value_error():
    """인식할 수 없는 포맷은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        parse_timeframe("invalid")


@pytest.mark.unit
def test_parse_timeframe_empty_string_raises_value_error():
    """빈 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        parse_timeframe("")

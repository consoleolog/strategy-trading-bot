from datetime import datetime

import pytest
from src.model.signal import Signal
from src.util.constants import SignalDirection, SignalType, SignalValue

SAMPLE_DICT = {
    "strategy_id": "ma_crossover_v1",
    "indicator_id": "ma_5_20",
    "type": "cross_over",
    "value": "golden_cross",
    "direction": "long",
    "market": "KRW-BTC",
    "timeframe": "1m",
    "timestamp": "2025-01-02T04:28:05",
    "metadata": {"short_period": 5, "long_period": 20},
}


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_string_fields():
    """strategy_id, indicator_id, market, timeframe 필드가 올바르게 매핑된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert signal.strategy_id == "ma_crossover_v1"
    assert signal.indicator_id == "ma_5_20"
    assert signal.market == "KRW-BTC"
    assert signal.timeframe == "1m"


@pytest.mark.unit
def test_from_dict_metadata():
    """metadata 필드가 dict 그대로 매핑된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert signal.metadata == {"short_period": 5, "long_period": 20}


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_type_is_signal_type_enum():
    """문자열 type이 SignalType enum으로 변환된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert isinstance(signal.type, SignalType)
    assert signal.type == SignalType.CROSS_OVER


@pytest.mark.unit
def test_value_is_signal_value_enum():
    """문자열 value가 SignalValue enum으로 변환된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert isinstance(signal.value, SignalValue)
    assert signal.value == SignalValue.GOLDEN_CROSS


@pytest.mark.unit
def test_direction_is_signal_direction_enum():
    """문자열 direction이 SignalDirection enum으로 변환된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert isinstance(signal.direction, SignalDirection)
    assert signal.direction == SignalDirection.LONG


@pytest.mark.unit
def test_all_signal_types_parseable():
    """모든 SignalType 값이 올바르게 파싱된다."""
    for signal_type in SignalType:
        signal = Signal.from_dict({**SAMPLE_DICT, "type": signal_type.value})
        assert signal.type == signal_type


@pytest.mark.unit
def test_all_signal_directions_parseable():
    """모든 SignalDirection 값이 올바르게 파싱된다."""
    for direction in SignalDirection:
        signal = Signal.from_dict({**SAMPLE_DICT, "direction": direction.value})
        assert signal.direction == direction


@pytest.mark.unit
def test_dead_cross_value_parsed():
    """DEAD_CROSS 값이 SignalValue.DEAD_CROSS로 변환된다."""
    signal = Signal.from_dict({**SAMPLE_DICT, "value": "dead_cross", "direction": "short"})
    assert signal.value == SignalValue.DEAD_CROSS
    assert signal.direction == SignalDirection.SHORT


@pytest.mark.unit
def test_post_init_skips_already_enum():
    """이미 enum인 필드는 그대로 유지된다."""
    data = {
        **SAMPLE_DICT,
        "type": SignalType.LEVEL_BREAK,
        "value": SignalValue.OVER_BOUGHT,
        "direction": SignalDirection.CLOSE,
    }
    signal = Signal.from_dict(data)
    assert signal.type == SignalType.LEVEL_BREAK
    assert signal.value == SignalValue.OVER_BOUGHT
    assert signal.direction == SignalDirection.CLOSE


@pytest.mark.unit
def test_invalid_type_raises_value_error():
    """정의되지 않은 type 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Signal.from_dict({**SAMPLE_DICT, "type": "unknown_type"})


@pytest.mark.unit
def test_invalid_value_raises_value_error():
    """정의되지 않은 value 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Signal.from_dict({**SAMPLE_DICT, "value": "unknown_value"})


@pytest.mark.unit
def test_invalid_direction_raises_value_error():
    """정의되지 않은 direction 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Signal.from_dict({**SAMPLE_DICT, "direction": "buy"})


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamp_is_datetime_type():
    """문자열 timestamp가 datetime 타입으로 변환된다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert isinstance(signal.timestamp, datetime)


@pytest.mark.unit
def test_timestamp_value():
    """timestamp가 ISO 8601 문자열과 동일한 값을 가진다."""
    signal = Signal.from_dict(SAMPLE_DICT)
    assert signal.timestamp == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_post_init_skips_already_datetime():
    """이미 datetime인 timestamp는 그대로 유지된다."""
    dt = datetime(2025, 1, 2, 4, 28, 5)
    signal = Signal.from_dict({**SAMPLE_DICT, "timestamp": dt})
    assert signal.timestamp == dt


# ---------------------------------------------------------------------------
# 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamp_defaults_to_now_when_absent():
    """timestamp가 dict에 없으면 현재 시각으로 설정된다."""
    before = datetime.now()
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "timestamp"}
    signal = Signal.from_dict(data)
    after = datetime.now()
    assert before <= signal.timestamp <= after


@pytest.mark.unit
def test_metadata_defaults_to_empty_dict_when_absent():
    """metadata가 dict에 없으면 빈 dict로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "metadata"}
    signal = Signal.from_dict(data)
    assert signal.metadata == {}


@pytest.mark.unit
def test_direct_construction_timestamp_defaults():
    """직접 생성 시 timestamp를 생략하면 현재 시각이 자동 설정된다."""
    before = datetime.now()
    signal = Signal(
        strategy_id="s1",
        indicator_id="i1",
        type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=SignalDirection.LONG,
        market="KRW-BTC",
        timeframe="1m",
    )
    after = datetime.now()
    assert before <= signal.timestamp <= after


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = Signal.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "strategy_id",
        "indicator_id",
        "type",
        "value",
        "direction",
        "market",
        "timeframe",
        "timestamp",
        "metadata",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_enum_fields_are_enum_type():
    """to_dict()의 enum 필드는 enum 타입으로 반환된다."""
    result = Signal.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["type"], SignalType)
    assert isinstance(result["value"], SignalValue)
    assert isinstance(result["direction"], SignalDirection)


@pytest.mark.unit
def test_to_dict_timestamp_is_datetime():
    """to_dict()의 timestamp는 datetime 타입으로 반환된다."""
    result = Signal.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["timestamp"], datetime)


@pytest.mark.unit
def test_to_dict_string_fields():
    """to_dict()의 문자열 필드가 원본 값과 일치한다."""
    result = Signal.from_dict(SAMPLE_DICT).to_dict()
    assert result["strategy_id"] == "ma_crossover_v1"
    assert result["market"] == "KRW-BTC"
    assert result["timeframe"] == "1m"


@pytest.mark.unit
def test_to_dict_metadata_preserved():
    """to_dict()의 metadata가 원본과 동일하다."""
    result = Signal.from_dict(SAMPLE_DICT).to_dict()
    assert result["metadata"] == {"short_period": 5, "long_period": 20}

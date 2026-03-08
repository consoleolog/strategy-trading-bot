from datetime import datetime
from decimal import Decimal

import pytest
from src.model.signal import Signal
from src.model.trade_candidate import TradeCandidate
from src.util.constants import SignalDirection, SignalType, SignalValue

SAMPLE_SIGNAL_DICT = {
    "strategy_id": "ma_crossover_v1",
    "indicator_id": "ma_5_20",
    "type": "cross_over",
    "value": "golden_cross",
    "direction": "long",
    "market": "KRW-BTC",
    "timeframe": "1m",
    "timestamp": "2025-01-02T04:28:05",
    "metadata": {},
}

SAMPLE_DICT = {
    "market": "KRW-BTC",
    "direction": "long",
    "contributing_signals": [SAMPLE_SIGNAL_DICT],
    "suggested_entry": "142000000",
    "suggested_stop_loss": "140000000",
    "suggested_take_profit": "146000000",
    "timestamp": "2025-01-02T04:28:05",
}


def make_signal() -> Signal:
    return Signal.from_dict(SAMPLE_SIGNAL_DICT)


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_market_field():
    """market 필드가 올바르게 매핑된다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert tc.market == "KRW-BTC"


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_direction_is_signal_direction_enum():
    """문자열 direction이 SignalDirection enum으로 변환된다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert isinstance(tc.direction, SignalDirection)
    assert tc.direction == SignalDirection.LONG


@pytest.mark.unit
def test_post_init_skips_already_direction_enum():
    """이미 SignalDirection enum인 direction은 그대로 유지된다."""
    data = {**SAMPLE_DICT, "direction": SignalDirection.SHORT}
    tc = TradeCandidate.from_dict(data)
    assert tc.direction == SignalDirection.SHORT


@pytest.mark.unit
def test_invalid_direction_raises_value_error():
    """정의되지 않은 direction 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        TradeCandidate.from_dict({**SAMPLE_DICT, "direction": "buy"})


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decimal_fields_are_decimal_type():
    """가격 필드들이 모두 Decimal 타입으로 변환된다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert isinstance(tc.suggested_entry, Decimal)
    assert isinstance(tc.suggested_stop_loss, Decimal)
    assert isinstance(tc.suggested_take_profit, Decimal)


@pytest.mark.unit
def test_decimal_values():
    """가격 필드들이 올바른 값을 가진다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert tc.suggested_entry == Decimal("142000000")
    assert tc.suggested_stop_loss == Decimal("140000000")
    assert tc.suggested_take_profit == Decimal("146000000")


@pytest.mark.unit
def test_decimal_converted_from_float():
    """float로 전달된 가격 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "suggested_entry": 142000000.0}
    tc = TradeCandidate.from_dict(data)
    assert isinstance(tc.suggested_entry, Decimal)


@pytest.mark.unit
def test_decimal_converted_from_int():
    """int로 전달된 가격 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "suggested_entry": 142000000}
    tc = TradeCandidate.from_dict(data)
    assert isinstance(tc.suggested_entry, Decimal)
    assert tc.suggested_entry == Decimal("142000000")


@pytest.mark.unit
def test_post_init_skips_already_decimal():
    """이미 Decimal인 가격 필드는 그대로 유지된다."""
    data = {**SAMPLE_DICT, "suggested_entry": Decimal("142000000")}
    tc = TradeCandidate.from_dict(data)
    assert tc.suggested_entry == Decimal("142000000")


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamp_is_datetime_type():
    """문자열 timestamp가 datetime 타입으로 변환된다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert isinstance(tc.timestamp, datetime)


@pytest.mark.unit
def test_timestamp_value():
    """timestamp가 ISO 8601 문자열과 동일한 값을 가진다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert tc.timestamp == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_timestamp_defaults_to_now_when_absent():
    """timestamp가 dict에 없으면 현재 시각으로 설정된다."""
    before = datetime.now()
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "timestamp"}
    tc = TradeCandidate.from_dict(data)
    after = datetime.now()
    assert before <= tc.timestamp <= after


# ---------------------------------------------------------------------------
# contributing_signals 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_contributing_signals_dict_converted_to_signal():
    """dict로 전달된 contributing_signals의 요소가 Signal 객체로 변환된다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    assert len(tc.contributing_signals) == 1
    assert isinstance(tc.contributing_signals[0], Signal)


@pytest.mark.unit
def test_contributing_signals_values():
    """변환된 Signal의 필드가 올바른 값을 가진다."""
    tc = TradeCandidate.from_dict(SAMPLE_DICT)
    signal = tc.contributing_signals[0]
    assert signal.strategy_id == "ma_crossover_v1"
    assert signal.type == SignalType.CROSS_OVER
    assert signal.value == SignalValue.GOLDEN_CROSS
    assert signal.direction == SignalDirection.LONG


@pytest.mark.unit
def test_contributing_signals_already_signal_skips_conversion():
    """이미 Signal 객체인 요소는 그대로 유지된다."""
    signal = make_signal()
    data = {**SAMPLE_DICT, "contributing_signals": [signal]}
    tc = TradeCandidate.from_dict(data)
    assert tc.contributing_signals[0] is signal


@pytest.mark.unit
def test_contributing_signals_empty_list():
    """contributing_signals가 빈 리스트이면 그대로 유지된다."""
    data = {**SAMPLE_DICT, "contributing_signals": []}
    tc = TradeCandidate.from_dict(data)
    assert tc.contributing_signals == []


@pytest.mark.unit
def test_contributing_signals_multiple():
    """여러 시그널 dict가 모두 Signal 객체로 변환된다."""
    data = {**SAMPLE_DICT, "contributing_signals": [SAMPLE_SIGNAL_DICT, SAMPLE_SIGNAL_DICT]}
    tc = TradeCandidate.from_dict(data)
    assert len(tc.contributing_signals) == 2
    assert all(isinstance(s, Signal) for s in tc.contributing_signals)


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "market",
        "direction",
        "contributing_signals",
        "suggested_entry",
        "suggested_stop_loss",
        "suggested_take_profit",
        "timestamp",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_direction_is_enum():
    """to_dict()의 direction은 SignalDirection enum으로 반환된다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["direction"], SignalDirection)


@pytest.mark.unit
def test_to_dict_decimal_fields_are_decimal():
    """to_dict()의 가격 필드는 Decimal 타입으로 반환된다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["suggested_entry"], Decimal)
    assert isinstance(result["suggested_stop_loss"], Decimal)
    assert isinstance(result["suggested_take_profit"], Decimal)


@pytest.mark.unit
def test_to_dict_contributing_signals_are_dicts():
    """to_dict()의 contributing_signals는 dict 리스트로 직렬화된다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    assert all(isinstance(s, dict) for s in result["contributing_signals"])


@pytest.mark.unit
def test_to_dict_contributing_signals_has_signal_keys():
    """to_dict()의 contributing_signals 각 요소가 Signal 필드 키를 포함한다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    signal_dict = result["contributing_signals"][0]
    assert "strategy_id" in signal_dict
    assert "type" in signal_dict
    assert "value" in signal_dict
    assert "direction" in signal_dict


@pytest.mark.unit
def test_to_dict_timestamp_is_datetime():
    """to_dict()의 timestamp는 datetime 타입으로 반환된다."""
    result = TradeCandidate.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["timestamp"], datetime)

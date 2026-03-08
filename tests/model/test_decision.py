from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from src.model.decision import Decision
from src.model.signal import Signal
from src.util.constants import DecisionState, SignalDirection, SignalType, SignalValue

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
    "decision_id": "cdd92199-2897-4e14-9448-f923320408ad",
    "market": "KRW-BTC",
    "direction": "long",
    "volume": "0.01",
    "entry_price": "142000000",
    "stop_loss": "140000000",
    "take_profit": "146000000",
    "risk_amount": "20000",
    "risk_percent": 1.0,
    "contributing_signals": [SAMPLE_SIGNAL_DICT],
    "state": "PENDING",
}


def make_signal() -> Signal:
    return Signal.from_dict(SAMPLE_SIGNAL_DICT)


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_market_field():
    """market 필드가 올바르게 매핑된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert decision.market == "KRW-BTC"


@pytest.mark.unit
def test_from_dict_risk_percent():
    """risk_percent 필드가 float로 매핑된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert isinstance(decision.risk_percent, float)
    assert decision.risk_percent == 1.0


# ---------------------------------------------------------------------------
# UUID 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_id_is_uuid_type():
    """문자열 decision_id가 UUID 타입으로 변환된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert isinstance(decision.decision_id, UUID)


@pytest.mark.unit
def test_decision_id_value():
    """decision_id가 샘플 문자열과 동일한 UUID 값을 가진다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert decision.decision_id == UUID("cdd92199-2897-4e14-9448-f923320408ad")


@pytest.mark.unit
def test_decision_id_defaults_to_uuid4_when_absent():
    """decision_id가 dict에 없으면 uuid4()로 자동 생성된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "decision_id"}
    decision = Decision.from_dict(data)
    assert isinstance(decision.decision_id, UUID)


@pytest.mark.unit
def test_post_init_skips_already_uuid():
    """이미 UUID인 decision_id는 그대로 유지된다."""
    uid = uuid4()
    decision = Decision.from_dict({**SAMPLE_DICT, "decision_id": uid})
    assert decision.decision_id == uid


@pytest.mark.unit
def test_invalid_uuid_raises_value_error():
    """유효하지 않은 decision_id 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Decision.from_dict({**SAMPLE_DICT, "decision_id": "not-a-uuid"})


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_direction_is_signal_direction_enum():
    """문자열 direction이 SignalDirection enum으로 변환된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert isinstance(decision.direction, SignalDirection)
    assert decision.direction == SignalDirection.LONG


@pytest.mark.unit
def test_state_is_decision_state_enum():
    """문자열 state가 DecisionState enum으로 변환된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert isinstance(decision.state, DecisionState)
    assert decision.state == DecisionState.PENDING


@pytest.mark.unit
def test_all_decision_states_parseable():
    """모든 DecisionState 값이 올바르게 파싱된다."""
    for state in DecisionState:
        decision = Decision.from_dict({**SAMPLE_DICT, "state": state.value})
        assert decision.state == state


@pytest.mark.unit
def test_post_init_skips_already_enum():
    """이미 enum인 필드는 그대로 유지된다."""
    data = {
        **SAMPLE_DICT,
        "direction": SignalDirection.SHORT,
        "state": DecisionState.APPROVED,
    }
    decision = Decision.from_dict(data)
    assert decision.direction == SignalDirection.SHORT
    assert decision.state == DecisionState.APPROVED


@pytest.mark.unit
def test_invalid_direction_raises_value_error():
    """정의되지 않은 direction 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Decision.from_dict({**SAMPLE_DICT, "direction": "buy"})


@pytest.mark.unit
def test_invalid_state_raises_value_error():
    """정의되지 않은 state 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Decision.from_dict({**SAMPLE_DICT, "state": "UNKNOWN"})


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decimal_fields_are_decimal_type():
    """가격/수량 필드들이 모두 Decimal 타입으로 변환된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    for field in ["volume", "entry_price", "stop_loss", "take_profit", "risk_amount"]:
        assert isinstance(getattr(decision, field), Decimal), f"{field} should be Decimal"


@pytest.mark.unit
def test_decimal_values():
    """가격/수량 필드들이 올바른 값을 가진다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert decision.volume == Decimal("0.01")
    assert decision.entry_price == Decimal("142000000")
    assert decision.stop_loss == Decimal("140000000")
    assert decision.take_profit == Decimal("146000000")
    assert decision.risk_amount == Decimal("20000")


@pytest.mark.unit
def test_decimal_converted_from_int():
    """int로 전달된 Decimal 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "entry_price": 142000000}
    decision = Decision.from_dict(data)
    assert isinstance(decision.entry_price, Decimal)
    assert decision.entry_price == Decimal("142000000")


@pytest.mark.unit
def test_decimal_converted_from_float():
    """float로 전달된 Decimal 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "volume": 0.01}
    decision = Decision.from_dict(data)
    assert isinstance(decision.volume, Decimal)


# ---------------------------------------------------------------------------
# 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_state_defaults_to_pending():
    """state가 dict에 없으면 DecisionState.PENDING으로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "state"}
    decision = Decision.from_dict(data)
    assert decision.state == DecisionState.PENDING


@pytest.mark.unit
def test_risk_percent_defaults_to_zero():
    """risk_percent가 dict에 없으면 0.0으로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "risk_percent"}
    decision = Decision.from_dict(data)
    assert decision.risk_percent == 0.0


@pytest.mark.unit
def test_contributing_signals_defaults_to_empty_list():
    """contributing_signals가 dict에 없으면 빈 리스트로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "contributing_signals"}
    decision = Decision.from_dict(data)
    assert decision.contributing_signals == []


# ---------------------------------------------------------------------------
# contributing_signals 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_contributing_signals_dict_converted_to_signal():
    """dict로 전달된 contributing_signals의 요소가 Signal 객체로 변환된다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    assert len(decision.contributing_signals) == 1
    assert isinstance(decision.contributing_signals[0], Signal)


@pytest.mark.unit
def test_contributing_signals_values():
    """변환된 Signal의 필드가 올바른 값을 가진다."""
    decision = Decision.from_dict(SAMPLE_DICT)
    signal = decision.contributing_signals[0]
    assert signal.type == SignalType.CROSS_OVER
    assert signal.value == SignalValue.GOLDEN_CROSS
    assert signal.direction == SignalDirection.LONG


@pytest.mark.unit
def test_contributing_signals_already_signal_skips_conversion():
    """이미 Signal 객체인 요소는 그대로 유지된다."""
    signal = make_signal()
    data = {**SAMPLE_DICT, "contributing_signals": [signal]}
    decision = Decision.from_dict(data)
    assert decision.contributing_signals[0] is signal


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "decision_id",
        "market",
        "direction",
        "volume",
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_amount",
        "risk_percent",
        "contributing_signals",
        "state",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_decision_id_is_uuid():
    """to_dict()의 decision_id는 UUID 타입으로 반환된다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["decision_id"], UUID)


@pytest.mark.unit
def test_to_dict_enum_fields_are_enum_type():
    """to_dict()의 enum 필드는 enum 타입으로 반환된다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["direction"], SignalDirection)
    assert isinstance(result["state"], DecisionState)


@pytest.mark.unit
def test_to_dict_decimal_fields_are_decimal():
    """to_dict()의 Decimal 필드는 Decimal 타입으로 반환된다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    for field in ["volume", "entry_price", "stop_loss", "take_profit", "risk_amount"]:
        assert isinstance(result[field], Decimal), f"{field} should be Decimal"


@pytest.mark.unit
def test_to_dict_contributing_signals_are_dicts():
    """to_dict()의 contributing_signals는 dict 리스트로 직렬화된다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    assert all(isinstance(s, dict) for s in result["contributing_signals"])


@pytest.mark.unit
def test_to_dict_market_and_risk():
    """to_dict()의 market, risk_percent 값이 원본과 일치한다."""
    result = Decision.from_dict(SAMPLE_DICT).to_dict()
    assert result["market"] == "KRW-BTC"
    assert result["risk_percent"] == 1.0

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from src.model.constants import ExecutionState
from src.model.execution_result import ExecutionResult

DECISION_ID = "cdd92199-2897-4e14-9448-f923320408ad"
ORDER_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

SAMPLE_DICT = {
    "success": True,
    "decision_id": DECISION_ID,
    "order_uuid": ORDER_UUID,
    "filled_quantity": "0.01",
    "average_price": "142000000",
    "fee": "142000",
    "fee_asset": "KRW",
    "state": "FILLED",
    "error_message": None,
    "timestamp": "2025-01-02T04:28:05",
}


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_success_field():
    """success 필드가 올바르게 매핑된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert result.success is True


@pytest.mark.unit
def test_from_dict_fee_asset_field():
    """fee_asset 필드가 올바르게 매핑된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert result.fee_asset == "KRW"


@pytest.mark.unit
def test_from_dict_error_message_none():
    """error_message가 None으로 매핑된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert result.error_message is None


@pytest.mark.unit
def test_from_dict_error_message_present():
    """error_message가 문자열로 매핑된다."""
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "error_message": "주문 실패"})
    assert result.error_message == "주문 실패"


# ---------------------------------------------------------------------------
# UUID 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_id_is_uuid_type():
    """문자열 decision_id가 UUID 타입으로 변환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert isinstance(result.decision_id, UUID)
    assert result.decision_id == UUID(DECISION_ID)


@pytest.mark.unit
def test_order_uuid_is_uuid_type():
    """문자열 order_uuid가 UUID 타입으로 변환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert isinstance(result.order_uuid, UUID)
    assert result.order_uuid == UUID(ORDER_UUID)


@pytest.mark.unit
def test_post_init_skips_already_uuid():
    """이미 UUID인 필드는 그대로 유지된다."""
    uid = uuid4()
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "decision_id": uid})
    assert result.decision_id == uid


@pytest.mark.unit
def test_invalid_decision_id_raises_value_error():
    """유효하지 않은 decision_id 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        ExecutionResult.from_dict({**SAMPLE_DICT, "decision_id": "not-a-uuid"})


@pytest.mark.unit
def test_invalid_order_uuid_raises_value_error():
    """유효하지 않은 order_uuid 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        ExecutionResult.from_dict({**SAMPLE_DICT, "order_uuid": "not-a-uuid"})


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_state_is_execution_state_enum():
    """문자열 state가 ExecutionState enum으로 변환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert isinstance(result.state, ExecutionState)
    assert result.state == ExecutionState.FILLED


@pytest.mark.unit
def test_all_execution_states_parseable():
    """모든 ExecutionState 값이 올바르게 파싱된다."""
    for state in ExecutionState:
        result = ExecutionResult.from_dict({**SAMPLE_DICT, "state": state.value})
        assert result.state == state


@pytest.mark.unit
def test_post_init_skips_already_enum():
    """이미 ExecutionState enum인 state는 그대로 유지된다."""
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "state": ExecutionState.CANCELLED})
    assert result.state == ExecutionState.CANCELLED


@pytest.mark.unit
def test_invalid_state_raises_value_error():
    """정의되지 않은 state 값은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        ExecutionResult.from_dict({**SAMPLE_DICT, "state": "UNKNOWN"})


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decimal_fields_are_decimal_type():
    """filled_quantity, average_price, fee 필드가 Decimal 타입으로 변환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert isinstance(result.filled_quantity, Decimal)
    assert isinstance(result.average_price, Decimal)
    assert isinstance(result.fee, Decimal)


@pytest.mark.unit
def test_decimal_values():
    """가격/수량/수수료 필드가 올바른 값을 가진다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert result.filled_quantity == Decimal("0.01")
    assert result.average_price == Decimal("142000000")
    assert result.fee == Decimal("142000")


@pytest.mark.unit
def test_decimal_converted_from_int():
    """int로 전달된 Decimal 필드가 Decimal로 변환된다."""
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "average_price": 142000000})
    assert isinstance(result.average_price, Decimal)
    assert result.average_price == Decimal("142000000")


@pytest.mark.unit
def test_decimal_converted_from_float():
    """float로 전달된 Decimal 필드가 Decimal로 변환된다."""
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "filled_quantity": 0.01})
    assert isinstance(result.filled_quantity, Decimal)


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamp_is_datetime_type():
    """문자열 timestamp가 datetime 타입으로 변환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert isinstance(result.timestamp, datetime)


@pytest.mark.unit
def test_timestamp_value():
    """timestamp가 ISO 8601 문자열과 동일한 값을 가진다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT)
    assert result.timestamp == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_timestamp_defaults_to_now_when_absent():
    """timestamp가 dict에 없으면 현재 시각으로 설정된다."""
    before = datetime.now()
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "timestamp"}
    result = ExecutionResult.from_dict(data)
    after = datetime.now()
    assert before <= result.timestamp <= after


# ---------------------------------------------------------------------------
# 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_state_defaults_to_pending():
    """state가 dict에 없으면 ExecutionState.PENDING으로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "state"}
    result = ExecutionResult.from_dict(data)
    assert result.state == ExecutionState.PENDING


@pytest.mark.unit
def test_fee_asset_defaults_to_krw():
    """fee_asset이 dict에 없으면 'KRW'로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "fee_asset"}
    result = ExecutionResult.from_dict(data)
    assert result.fee_asset == "KRW"


@pytest.mark.unit
def test_error_message_defaults_to_none():
    """error_message가 dict에 없으면 None으로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "error_message"}
    result = ExecutionResult.from_dict(data)
    assert result.error_message is None


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "success",
        "decision_id",
        "order_uuid",
        "filled_quantity",
        "average_price",
        "fee",
        "fee_asset",
        "state",
        "error_message",
        "timestamp",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_uuid_fields_are_uuid_type():
    """to_dict()의 UUID 필드는 UUID 타입으로 반환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["decision_id"], UUID)
    assert isinstance(result["order_uuid"], UUID)


@pytest.mark.unit
def test_to_dict_state_is_enum():
    """to_dict()의 state는 ExecutionState enum으로 반환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["state"], ExecutionState)


@pytest.mark.unit
def test_to_dict_decimal_fields_are_decimal():
    """to_dict()의 Decimal 필드는 Decimal 타입으로 반환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["filled_quantity"], Decimal)
    assert isinstance(result["average_price"], Decimal)
    assert isinstance(result["fee"], Decimal)


@pytest.mark.unit
def test_to_dict_timestamp_is_datetime():
    """to_dict()의 timestamp는 datetime 타입으로 반환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["timestamp"], datetime)


@pytest.mark.unit
def test_to_dict_success_field():
    """to_dict()의 success 값이 원본과 일치한다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert result["success"] is True


@pytest.mark.unit
def test_to_dict_error_message_none_preserved():
    """to_dict()의 error_message가 None이면 None으로 반환된다."""
    result = ExecutionResult.from_dict(SAMPLE_DICT).to_dict()
    assert result["error_message"] is None


@pytest.mark.unit
def test_to_dict_error_message_string_preserved():
    """to_dict()의 error_message 문자열이 원본과 일치한다."""
    result = ExecutionResult.from_dict({**SAMPLE_DICT, "error_message": "주문 실패"}).to_dict()
    assert result["error_message"] == "주문 실패"

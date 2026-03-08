from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from src.model.trade import Trade
from src.util.constants import OrderSide

TRADE_ID = "cdd92199-2897-4e14-9448-f923320408ad"
ORDER_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
DECISION_ID = "deadbeef-dead-beef-dead-beefdeadbeef"

SAMPLE_DICT = {
    "trade_id": TRADE_ID,
    "market": "KRW-BTC",
    "side": "ask",
    "volume": "0.01",
    "price": "142000000",
    "strategy_id": "ma_crossover_v1",
    "order_uuid": ORDER_UUID,
    "fee": "142000",
    "fee_asset": "KRW",
    "decision_id": DECISION_ID,
    "timestamp": "2025-01-02T04:28:05",
}


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_string_fields():
    """market, strategy_id, fee_asset 필드가 올바르게 매핑된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert trade.market == "KRW-BTC"
    assert trade.strategy_id == "ma_crossover_v1"
    assert trade.fee_asset == "KRW"


# ---------------------------------------------------------------------------
# UUID 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_trade_id_is_uuid_type():
    """문자열 trade_id가 UUID 타입으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.trade_id, UUID)
    assert trade.trade_id == UUID(TRADE_ID)


@pytest.mark.unit
def test_order_uuid_is_uuid_type():
    """문자열 order_uuid가 UUID 타입으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.order_uuid, UUID)
    assert trade.order_uuid == UUID(ORDER_UUID)


@pytest.mark.unit
def test_decision_id_is_uuid_when_present():
    """문자열 decision_id가 UUID 타입으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.decision_id, UUID)
    assert trade.decision_id == UUID(DECISION_ID)


@pytest.mark.unit
def test_decision_id_is_none_when_absent():
    """decision_id가 dict에 없으면 None을 유지한다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "decision_id"}
    trade = Trade.from_dict(data)
    assert trade.decision_id is None


@pytest.mark.unit
def test_post_init_skips_already_uuid():
    """이미 UUID인 필드는 그대로 유지된다."""
    uid = uuid4()
    trade = Trade.from_dict({**SAMPLE_DICT, "trade_id": uid})
    assert trade.trade_id == uid


@pytest.mark.unit
def test_invalid_trade_id_raises_value_error():
    """유효하지 않은 trade_id 문자열은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Trade.from_dict({**SAMPLE_DICT, "trade_id": "not-a-uuid"})


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_side_is_order_side_enum():
    """문자열 side가 OrderSide enum으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.side, OrderSide)
    assert trade.side == OrderSide.ASK


@pytest.mark.unit
def test_side_bid_parsed():
    """'bid' 문자열이 OrderSide.BID로 변환된다."""
    trade = Trade.from_dict({**SAMPLE_DICT, "side": "bid"})
    assert trade.side == OrderSide.BID


@pytest.mark.unit
def test_post_init_skips_already_side_enum():
    """이미 OrderSide enum인 side는 그대로 유지된다."""
    trade = Trade.from_dict({**SAMPLE_DICT, "side": OrderSide.BID})
    assert trade.side == OrderSide.BID


@pytest.mark.unit
def test_invalid_side_raises_value_error():
    """정의되지 않은 side 값은 ValueError를 발생시킨다."""
    with pytest.raises(ValueError):
        Trade.from_dict({**SAMPLE_DICT, "side": "buy"})


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decimal_fields_are_decimal_type():
    """volume, price, fee 필드가 모두 Decimal 타입으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.volume, Decimal)
    assert isinstance(trade.price, Decimal)
    assert isinstance(trade.fee, Decimal)


@pytest.mark.unit
def test_decimal_values():
    """가격/수량/수수료 필드가 올바른 값을 가진다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert trade.volume == Decimal("0.01")
    assert trade.price == Decimal("142000000")
    assert trade.fee == Decimal("142000")


@pytest.mark.unit
def test_decimal_converted_from_int():
    """int로 전달된 Decimal 필드가 Decimal로 변환된다."""
    trade = Trade.from_dict({**SAMPLE_DICT, "price": 142000000})
    assert isinstance(trade.price, Decimal)
    assert trade.price == Decimal("142000000")


@pytest.mark.unit
def test_decimal_converted_from_float():
    """float로 전달된 Decimal 필드가 Decimal로 변환된다."""
    trade = Trade.from_dict({**SAMPLE_DICT, "volume": 0.01})
    assert isinstance(trade.volume, Decimal)


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamp_is_datetime_type():
    """문자열 timestamp가 datetime 타입으로 변환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.timestamp, datetime)


@pytest.mark.unit
def test_timestamp_value():
    """timestamp가 ISO 8601 문자열과 동일한 값을 가진다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert trade.timestamp == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_timestamp_defaults_to_now_when_absent():
    """timestamp가 dict에 없으면 현재 시각으로 설정된다."""
    before = datetime.now()
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "timestamp"}
    trade = Trade.from_dict(data)
    after = datetime.now()
    assert before <= trade.timestamp <= after


# ---------------------------------------------------------------------------
# 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fee_asset_defaults_to_krw():
    """fee_asset이 dict에 없으면 'KRW'로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "fee_asset"}
    trade = Trade.from_dict(data)
    assert trade.fee_asset == "KRW"


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "trade_id",
        "market",
        "side",
        "volume",
        "price",
        "strategy_id",
        "order_uuid",
        "fee",
        "fee_asset",
        "decision_id",
        "timestamp",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_uuid_fields_are_uuid_type():
    """to_dict()의 UUID 필드는 UUID 타입으로 반환된다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["trade_id"], UUID)
    assert isinstance(result["order_uuid"], UUID)
    assert isinstance(result["decision_id"], UUID)


@pytest.mark.unit
def test_to_dict_decision_id_none_preserved():
    """to_dict()의 decision_id가 None이면 None으로 반환된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "decision_id"}
    result = Trade.from_dict(data).to_dict()
    assert result["decision_id"] is None


@pytest.mark.unit
def test_to_dict_side_is_enum():
    """to_dict()의 side는 OrderSide enum으로 반환된다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["side"], OrderSide)


@pytest.mark.unit
def test_to_dict_decimal_fields_are_decimal():
    """to_dict()의 Decimal 필드는 Decimal 타입으로 반환된다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["volume"], Decimal)
    assert isinstance(result["price"], Decimal)
    assert isinstance(result["fee"], Decimal)


@pytest.mark.unit
def test_to_dict_timestamp_is_datetime():
    """to_dict()의 timestamp는 datetime 타입으로 반환된다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["timestamp"], datetime)


@pytest.mark.unit
def test_to_dict_string_fields():
    """to_dict()의 문자열 필드가 원본 값과 일치한다."""
    result = Trade.from_dict(SAMPLE_DICT).to_dict()
    assert result["market"] == "KRW-BTC"
    assert result["strategy_id"] == "ma_crossover_v1"
    assert result["fee_asset"] == "KRW"


# ---------------------------------------------------------------------------
# property — value
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_value_is_price_times_volume():
    """체결 총액이 체결 단가 x 체결 수량으로 계산된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    expected = Decimal("142000000") * Decimal("0.01")
    assert trade.value == expected


@pytest.mark.unit
def test_value_is_decimal_type():
    """체결 총액은 Decimal 타입으로 반환된다."""
    trade = Trade.from_dict(SAMPLE_DICT)
    assert isinstance(trade.value, Decimal)

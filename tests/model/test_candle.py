from datetime import datetime
from decimal import Decimal

import pytest
from src.model.candle import Candle
from src.model.constants import CandleType, StreamType

SAMPLE_DICT = {
    "type": "candle.1s",
    "code": "KRW-BTC",
    "candle_date_time_utc": "2025-01-02T04:28:05",
    "candle_date_time_kst": "2025-01-02T13:28:05",
    "opening_price": 142009000.00000000,
    "high_price": 142009000.00000000,
    "low_price": 142009000.00000000,
    "trade_price": 142009000.00000000,
    "candle_acc_trade_volume": 0.00606119,
    "candle_acc_trade_price": 860743.5307100000000000,
    "timestamp": 1735792085824,
    "stream_type": "REALTIME",
}

DECIMAL_FIELDS = [
    "opening_price",
    "high_price",
    "low_price",
    "trade_price",
    "candle_acc_trade_volume",
    "candle_acc_trade_price",
]


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_code_field():
    """code 필드가 올바르게 매핑된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.code == "KRW-BTC"


@pytest.mark.unit
def test_from_dict_timestamp_field():
    """timestamp 필드가 정수로 매핑된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.timestamp == 1735792085824


# ---------------------------------------------------------------------------
# enum 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_type_is_candle_type_enum():
    """문자열 type이 CandleType enum으로 변환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert isinstance(candle.type, CandleType)


@pytest.mark.unit
def test_from_dict_type_value():
    """type이 CandleType.SECOND로 변환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.type == CandleType.SECOND


@pytest.mark.unit
def test_from_dict_stream_type_is_stream_type_enum():
    """문자열 stream_type이 StreamType enum으로 변환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert isinstance(candle.stream_type, StreamType)


@pytest.mark.unit
def test_from_dict_stream_type_value():
    """stream_type이 StreamType.REALTIME으로 변환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.stream_type == StreamType.REALTIME


@pytest.mark.unit
def test_from_dict_snapshot_stream_type():
    """SNAPSHOT 문자열이 StreamType.SNAPSHOT으로 변환된다."""
    data = {**SAMPLE_DICT, "stream_type": "SNAPSHOT"}
    candle = Candle.from_dict(data)
    assert candle.stream_type == StreamType.SNAPSHOT


@pytest.mark.unit
def test_post_init_skips_already_candle_type_enum():
    """이미 CandleType enum인 경우 그대로 유지된다."""
    data = {**SAMPLE_DICT, "type": CandleType.MINUTE_5}
    candle = Candle.from_dict(data)
    assert candle.type == CandleType.MINUTE_5


@pytest.mark.unit
def test_post_init_skips_already_stream_type_enum():
    """이미 StreamType enum인 경우 그대로 유지된다."""
    data = {**SAMPLE_DICT, "stream_type": StreamType.SNAPSHOT}
    candle = Candle.from_dict(data)
    assert candle.stream_type == StreamType.SNAPSHOT


@pytest.mark.unit
def test_invalid_type_raises_value_error():
    """정의되지 않은 type 문자열은 ValueError를 발생시킨다."""
    data = {**SAMPLE_DICT, "type": "candle.999m"}
    with pytest.raises(ValueError):
        Candle.from_dict(data)


@pytest.mark.unit
def test_invalid_stream_type_raises_value_error():
    """정의되지 않은 stream_type 문자열은 ValueError를 발생시킨다."""
    data = {**SAMPLE_DICT, "stream_type": "UNKNOWN"}
    with pytest.raises(ValueError):
        Candle.from_dict(data)


@pytest.mark.unit
def test_all_candle_types_are_parseable():
    """모든 CandleType 값이 from_dict로 올바르게 파싱된다."""
    for candle_type in CandleType:
        data = {**SAMPLE_DICT, "type": candle_type.value}
        candle = Candle.from_dict(data)
        assert candle.type == candle_type


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_datetime_fields_are_datetime_type():
    """문자열로 전달된 candle_date_time 필드가 datetime 타입으로 변환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert isinstance(candle.candle_date_time_utc, datetime)
    assert isinstance(candle.candle_date_time_kst, datetime)


@pytest.mark.unit
def test_from_dict_utc_datetime_value():
    """candle_date_time_utc가 ISO 8601 문자열과 동일한 datetime 값을 가진다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.candle_date_time_utc == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_from_dict_kst_datetime_value():
    """candle_date_time_kst가 ISO 8601 문자열과 동일한 datetime 값을 가진다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.candle_date_time_kst == datetime(2025, 1, 2, 13, 28, 5)


@pytest.mark.unit
def test_post_init_skips_already_datetime():
    """이미 datetime인 필드는 그대로 유지된다."""
    dt = datetime(2025, 1, 2, 4, 28, 5)
    data = {**SAMPLE_DICT, "candle_date_time_utc": dt}
    candle = Candle.from_dict(data)
    assert candle.candle_date_time_utc == dt


@pytest.mark.unit
def test_utc_and_kst_differ_by_nine_hours():
    """UTC와 KST 시각 차이가 9시간이다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    diff = candle.candle_date_time_kst - candle.candle_date_time_utc
    assert diff.seconds == 9 * 3600


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_decimal_fields_are_decimal_type():
    """from_dict() 후 Decimal 필드들은 모두 Decimal 타입이다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    for field in DECIMAL_FIELDS:
        assert isinstance(getattr(candle, field), Decimal), f"{field} should be Decimal"


@pytest.mark.unit
def test_from_dict_main_price_value():
    """opening_price가 샘플 데이터의 값과 일치한다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.opening_price == Decimal("142009000.0")


@pytest.mark.unit
def test_from_dict_small_volume_precision():
    """candle_acc_trade_volume의 소수 정밀도가 손실되지 않는다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.candle_acc_trade_volume == Decimal(str(0.00606119))


@pytest.mark.unit
def test_post_init_converts_int_to_decimal():
    """int로 전달된 Decimal 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "opening_price": 142009000}
    candle = Candle.from_dict(data)
    assert isinstance(candle.opening_price, Decimal)
    assert candle.opening_price == Decimal("142009000")


@pytest.mark.unit
def test_post_init_converts_str_to_decimal():
    """str로 전달된 Decimal 필드가 Decimal로 변환된다."""
    data = {**SAMPLE_DICT, "opening_price": "142009000.00"}
    candle = Candle.from_dict(data)
    assert isinstance(candle.opening_price, Decimal)
    assert candle.opening_price == Decimal("142009000.00")


@pytest.mark.unit
def test_post_init_skips_already_decimal():
    """이미 Decimal인 필드는 그대로 유지된다."""
    data = {**SAMPLE_DICT, "opening_price": Decimal("142009000")}
    candle = Candle.from_dict(data)
    assert candle.opening_price == Decimal("142009000")


@pytest.mark.unit
def test_post_init_does_not_touch_timestamp():
    """timestamp는 변환 대상이 아니므로 int로 유지된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert isinstance(candle.timestamp, int)


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    result = candle.to_dict()
    expected_keys = {
        "type",
        "code",
        "candle_date_time_utc",
        "candle_date_time_kst",
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_volume",
        "candle_acc_trade_price",
        "timestamp",
        "stream_type",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_type_is_candle_type_enum():
    """to_dict()의 type 필드는 CandleType enum이다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.to_dict()["type"] == CandleType.SECOND


@pytest.mark.unit
def test_to_dict_stream_type_is_stream_type_enum():
    """to_dict()의 stream_type 필드는 StreamType enum이다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    assert candle.to_dict()["stream_type"] == StreamType.REALTIME


@pytest.mark.unit
def test_to_dict_datetime_fields_are_datetime_type():
    """to_dict()의 candle_date_time 필드는 datetime 타입으로 반환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    result = candle.to_dict()
    assert isinstance(result["candle_date_time_utc"], datetime)
    assert isinstance(result["candle_date_time_kst"], datetime)


@pytest.mark.unit
def test_to_dict_decimal_values_preserved():
    """to_dict()의 Decimal 필드가 Decimal 값으로 반환된다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    result = candle.to_dict()
    assert isinstance(result["opening_price"], Decimal)
    assert result["opening_price"] == candle.opening_price


@pytest.mark.unit
def test_to_dict_code_and_timestamp():
    """to_dict()의 code, timestamp 필드가 원본 값과 일치한다."""
    candle = Candle.from_dict(SAMPLE_DICT)
    result = candle.to_dict()
    assert result["code"] == "KRW-BTC"
    assert result["timestamp"] == SAMPLE_DICT["timestamp"]

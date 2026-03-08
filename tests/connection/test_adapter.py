import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote, urlencode

import jwt
import pytest
from src.connection.adapter import UpbitAdapter
from src.model.candle import Candle
from src.util.constants import CandleType, StreamType, Timeframe

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> dict:
    return {
        "api_key": "test-key",
        "api_secret": "test-secret",
        "is_test": False,
    }


@pytest.fixture
def adapter(config: dict) -> UpbitAdapter:
    return UpbitAdapter(config)


def _make_session(closed: bool = False) -> MagicMock:
    """aiohttp.ClientSession 모의 객체를 생성한다."""
    session = MagicMock()
    session.closed = closed
    session.close = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_base_url(adapter: UpbitAdapter):
    assert adapter.base_url == "https://api.upbit.com/v1"


@pytest.mark.unit
def test_init_credentials(adapter: UpbitAdapter):
    assert adapter.api_key == "test-key"
    assert adapter.api_secret == "test-secret"


@pytest.mark.unit
def test_init_is_test_false(adapter: UpbitAdapter):
    assert adapter.is_test is False


@pytest.mark.unit
def test_init_is_test_true(config: dict):
    config["is_test"] = True
    a = UpbitAdapter(config)
    assert a.is_test is True


@pytest.mark.unit
def test_init_session_is_none(adapter: UpbitAdapter):
    assert adapter._session is None


@pytest.mark.unit
def test_init_missing_keys_use_defaults():
    """config에 키가 없으면 기본값을 사용한다."""
    a = UpbitAdapter({})
    assert a.api_key == ""
    assert a.api_secret == ""
    assert a.is_test is False


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_creates_session(adapter: UpbitAdapter):
    """세션이 없을 때 connect()는 새 ClientSession을 생성한다."""
    with patch("src.connection.adapter.aiohttp.ClientSession") as mock_cls:
        mock_cls.return_value = _make_session()
        await adapter.connect()

    assert adapter._session is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_does_not_recreate_open_session(adapter: UpbitAdapter):
    """세션이 이미 열려있으면 새로 생성하지 않는다."""
    existing = _make_session(closed=False)
    adapter._session = existing

    with patch("src.connection.adapter.aiohttp.ClientSession") as mock_cls:
        await adapter.connect()
        mock_cls.assert_not_called()

    assert adapter._session is existing


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connect_recreates_closed_session(adapter: UpbitAdapter):
    """세션이 닫혀있으면 새 세션을 생성한다."""
    adapter._session = _make_session(closed=True)
    new_session = _make_session(closed=False)

    with patch("src.connection.adapter.aiohttp.ClientSession", return_value=new_session):
        await adapter.connect()

    assert adapter._session is new_session


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_closes_open_session(adapter: UpbitAdapter):
    """열린 세션을 닫고 None으로 초기화한다."""
    session = _make_session(closed=False)
    adapter._session = session

    await adapter.disconnect()

    session.close.assert_awaited_once()
    assert adapter._session is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_does_nothing_when_session_is_none(adapter: UpbitAdapter):
    """세션이 None이면 아무것도 하지 않는다."""
    await adapter.disconnect()  # 예외 없이 통과


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_does_nothing_when_session_already_closed(adapter: UpbitAdapter):
    """이미 닫힌 세션에 대해 close()를 호출하지 않는다."""
    session = _make_session(closed=True)
    adapter._session = session

    await adapter.disconnect()

    session.close.assert_not_awaited()


# ---------------------------------------------------------------------------
# _ensure_session
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_session_calls_connect_when_no_session(adapter: UpbitAdapter):
    """세션이 없으면 connect()를 호출한다."""
    with patch("src.connection.adapter.aiohttp.ClientSession") as mock_cls:
        mock_cls.return_value = _make_session()
        await adapter._ensure_session()

    assert adapter._session is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_session_does_not_reconnect_when_open(adapter: UpbitAdapter):
    """세션이 열려있으면 connect()를 호출하지 않는다."""
    adapter._session = _make_session(closed=False)

    with patch.object(adapter, "connect", new_callable=AsyncMock) as mock_connect:
        await adapter._ensure_session()
        mock_connect.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_session_reconnects_when_closed(adapter: UpbitAdapter):
    """세션이 닫혀있으면 connect()를 호출한다."""
    adapter._session = _make_session(closed=True)

    with patch.object(adapter, "connect", new_callable=AsyncMock) as mock_connect:
        await adapter._ensure_session()
        mock_connect.assert_called_once()


# ---------------------------------------------------------------------------
# _sign_request
# ---------------------------------------------------------------------------


def _decode(token: str, secret: str) -> dict:
    """JWT 토큰을 검증 없이 디코딩한다."""
    return jwt.decode(token, secret, algorithms=["HS256"])


@pytest.mark.unit
def test_sign_request_returns_string(adapter: UpbitAdapter):
    """반환값이 문자열이다."""
    assert isinstance(adapter._sign_request(), str)


@pytest.mark.unit
def test_sign_request_is_valid_jwt(adapter: UpbitAdapter):
    """반환된 토큰이 api_secret으로 검증 가능하다."""
    token = adapter._sign_request()
    payload = _decode(token, adapter.api_secret)
    assert payload is not None


@pytest.mark.unit
def test_sign_request_payload_contains_access_key(adapter: UpbitAdapter):
    """페이로드에 api_key가 access_key로 포함된다."""
    token = adapter._sign_request()
    payload = _decode(token, adapter.api_secret)
    assert payload["access_key"] == adapter.api_key


@pytest.mark.unit
def test_sign_request_payload_contains_nonce(adapter: UpbitAdapter):
    """페이로드에 nonce(UUID 문자열)가 포함된다."""
    import uuid

    token = adapter._sign_request()
    payload = _decode(token, adapter.api_secret)
    nonce = payload["nonce"]
    assert uuid.UUID(nonce)  # 유효한 UUID 형식


@pytest.mark.unit
def test_sign_request_nonce_is_unique(adapter: UpbitAdapter):
    """호출마다 고유한 nonce가 생성된다."""
    token_a = adapter._sign_request()
    token_b = adapter._sign_request()
    nonce_a = _decode(token_a, adapter.api_secret)["nonce"]
    nonce_b = _decode(token_b, adapter.api_secret)["nonce"]
    assert nonce_a != nonce_b


@pytest.mark.unit
def test_sign_request_without_params_has_no_query_hash(adapter: UpbitAdapter):
    """params 없이 호출하면 query_hash가 포함되지 않는다."""
    token = adapter._sign_request()
    payload = _decode(token, adapter.api_secret)
    assert "query_hash" not in payload
    assert "query_hash_alg" not in payload


@pytest.mark.unit
def test_sign_request_with_params_includes_query_hash(adapter: UpbitAdapter):
    """params 전달 시 query_hash와 query_hash_alg가 포함된다."""
    token = adapter._sign_request({"market": "KRW-BTC"})
    payload = _decode(token, adapter.api_secret)
    assert "query_hash" in payload
    assert payload["query_hash_alg"] == "SHA512"


@pytest.mark.unit
def test_sign_request_query_hash_is_correct(adapter: UpbitAdapter):
    """query_hash가 params의 SHA512 해시와 일치한다."""
    params = {"market": "KRW-BTC", "side": "bid"}
    query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")
    expected_hash = hashlib.sha512(query_string).hexdigest()

    token = adapter._sign_request(params)
    payload = _decode(token, adapter.api_secret)
    assert payload["query_hash"] == expected_hash


@pytest.mark.unit
def test_sign_request_with_empty_params_has_no_query_hash(adapter: UpbitAdapter):
    """빈 dict 전달 시 query_hash가 포함되지 않는다."""
    token = adapter._sign_request({})
    payload = _decode(token, adapter.api_secret)
    assert "query_hash" not in payload


@pytest.mark.unit
def test_sign_request_wrong_secret_raises(adapter: UpbitAdapter):
    """잘못된 secret으로 디코딩하면 예외가 발생한다."""
    token = adapter._sign_request()
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "wrong-secret", algorithms=["HS256"])


# ---------------------------------------------------------------------------
# _request
# ---------------------------------------------------------------------------


def _make_api_response(data: object = None, status: int = 200) -> MagicMock:
    """error_handler가 처리할 수 있는 aiohttp 응답 모의 객체를 생성한다."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=data if data is not None else {"ok": True})
    response.text = AsyncMock(return_value="")
    response.release = MagicMock()
    return response


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.closed = False
    return session


@pytest.fixture
def connected_adapter(adapter: UpbitAdapter, mock_session: MagicMock) -> UpbitAdapter:
    """세션이 연결된 상태의 adapter."""
    adapter._session = mock_session
    return adapter


# GET


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_get_calls_session_get(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """GET 요청은 session.get()을 올바른 URL로 호출한다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/markets")

    mock_session.get.assert_awaited_once()
    call_kwargs = mock_session.get.call_args
    assert call_kwargs.args[0] == "https://api.upbit.com/v1/markets"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_get_passes_params(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """GET 요청은 params를 쿼리 파라미터로 전달한다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/candles", params={"market": "KRW-BTC"})

    _, kwargs = mock_session.get.call_args
    assert kwargs["params"] == {"market": "KRW-BTC"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_get_returns_json_data(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """GET 요청의 반환값은 error_handler가 파싱한 JSON 데이터다."""
    data = [{"market": "KRW-BTC"}, {"market": "KRW-ETH"}]
    mock_session.get = AsyncMock(return_value=_make_api_response(data))

    result = await connected_adapter._request("GET", "/markets")

    assert result == data


# POST


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_post_calls_session_post(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """POST 요청은 session.post()를 올바른 URL로 호출한다."""
    response = _make_api_response()
    mock_session.post = AsyncMock(return_value=response)

    await connected_adapter._request("POST", "/orders")

    mock_session.post.assert_awaited_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs.args[0] == "https://api.upbit.com/v1/orders"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_post_passes_params_as_json(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """POST 요청은 params를 json body로 전달한다."""
    response = _make_api_response()
    mock_session.post = AsyncMock(return_value=response)
    body = {"market": "KRW-BTC", "side": "bid", "volume": "0.001"}

    await connected_adapter._request("POST", "/orders", params=body)

    _, kwargs = mock_session.post.call_args
    assert kwargs["json"] == body


# DELETE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_delete_calls_session_delete(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """DELETE 요청은 session.delete()를 올바른 URL로 호출한다."""
    response = _make_api_response()
    mock_session.delete = AsyncMock(return_value=response)

    await connected_adapter._request("DELETE", "/order", params={"uuid": "abc-123"})

    mock_session.delete.assert_awaited_once()
    call_kwargs = mock_session.delete.call_args
    assert call_kwargs.args[0] == "https://api.upbit.com/v1/order"


# 알 수 없는 메서드


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_unknown_method_raises_value_error(
    connected_adapter: UpbitAdapter,
):
    """정의되지 않은 HTTP 메서드는 ValueError를 발생시킨다."""
    with pytest.raises(ValueError, match="Unknown method"):
        await connected_adapter._request("PATCH", "/something")


# signed


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_signed_adds_authorization_header(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """signed=True이면 Authorization 헤더가 추가된다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/accounts", signed=True)

    _, kwargs = mock_session.get.call_args
    assert "Authorization" in kwargs["headers"]
    assert kwargs["headers"]["Authorization"].startswith("Bearer ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_unsigned_has_no_authorization_header(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """signed=False이면 Authorization 헤더가 없다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/markets", signed=False)

    _, kwargs = mock_session.get.call_args
    assert "Authorization" not in kwargs["headers"]


# 기본값


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_none_params_defaults_to_empty_dict(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """params=None이면 빈 dict로 처리된다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/markets", params=None)

    _, kwargs = mock_session.get.call_args
    assert kwargs["params"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_none_headers_defaults_to_empty_dict(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """headers=None이면 빈 dict로 처리된다."""
    response = _make_api_response()
    mock_session.get = AsyncMock(return_value=response)

    await connected_adapter._request("GET", "/markets", headers=None)

    _, kwargs = mock_session.get.call_args
    assert isinstance(kwargs["headers"], dict)


# ClientError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_client_error_is_reraised(connected_adapter: UpbitAdapter, mock_session: MagicMock):
    """aiohttp.ClientError 발생 시 예외가 그대로 전파된다."""
    import aiohttp

    mock_session.get = AsyncMock(side_effect=aiohttp.ClientError("연결 실패"))

    with pytest.raises(aiohttp.ClientError):
        await connected_adapter._request("GET", "/markets")


# _ensure_session 호출 확인


@pytest.mark.unit
@pytest.mark.asyncio
async def test_request_calls_ensure_session(adapter: UpbitAdapter):
    """_request()는 항상 _ensure_session()을 호출한다."""
    response = _make_api_response()

    with (
        patch.object(adapter, "_ensure_session", new_callable=AsyncMock) as mock_ensure,
        patch.object(adapter, "_session") as mock_session,
    ):
        mock_session.closed = False
        mock_session.get = AsyncMock(return_value=response)
        await adapter._request("GET", "/markets")

    mock_ensure.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_candles / _timeframe_to_candle_type
# ---------------------------------------------------------------------------

_SAMPLE_RAW = [
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2025-01-03T00:00:00",
        "candle_date_time_kst": "2025-01-03T09:00:00",
        "opening_price": 143000000.0,
        "high_price": 145000000.0,
        "low_price": 142000000.0,
        "trade_price": 144000000.0,
        "candle_acc_trade_volume": 10.5,
        "candle_acc_trade_price": 1500000000.0,
        "timestamp": 1735862400000,
    },
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2025-01-02T00:00:00",
        "candle_date_time_kst": "2025-01-02T09:00:00",
        "opening_price": 141000000.0,
        "high_price": 143000000.0,
        "low_price": 140000000.0,
        "trade_price": 142000000.0,
        "candle_acc_trade_volume": 8.2,
        "candle_acc_trade_price": 1160000000.0,
        "timestamp": 1735776000000,
    },
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_returns_list_of_candles(adapter: UpbitAdapter):
    """반환값이 Candle 리스트다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW):
        result = await adapter.get_candles("KRW-BTC")

    assert isinstance(result, list)
    assert all(isinstance(c, Candle) for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_reverses_order(adapter: UpbitAdapter):
    """API 응답(최신→과거)을 과거→최신 순으로 역전한다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW):
        result = await adapter.get_candles("KRW-BTC")

    # _SAMPLE_RAW[0]이 최신, [1]이 과거 → 역전 후 [0]이 과거여야 함
    assert result[0].candle_date_time_utc < result[1].candle_date_time_utc


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_calls_request_with_correct_endpoint(adapter: UpbitAdapter):
    """_request()가 올바른 엔드포인트로 호출된다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-BTC", timeframe=Timeframe.MINUTE_1)

    mock_req.assert_awaited_once()
    assert mock_req.call_args.args[1] == f"/candles/{Timeframe.MINUTE_1.value}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_passes_market_and_count(adapter: UpbitAdapter):
    """market과 count가 params에 포함된다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-ETH", count=50)

    params = mock_req.call_args.kwargs["params"]
    assert params["market"] == "KRW-ETH"
    assert params["count"] == 50


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_default_count_is_200(adapter: UpbitAdapter):
    """count 기본값은 200이다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-BTC")

    params = mock_req.call_args.kwargs["params"]
    assert params["count"] == 200


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_default_timeframe_is_day(adapter: UpbitAdapter):
    """timeframe 기본값은 Timeframe.DAY다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-BTC")

    endpoint = mock_req.call_args.args[1]
    assert endpoint == f"/candles/{Timeframe.DAY.value}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_includes_to_when_provided(adapter: UpbitAdapter):
    """to 인자가 전달되면 params에 포함된다."""
    to_str = "2025-01-03T00:00:00Z"
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-BTC", to=to_str)

    params = mock_req.call_args.kwargs["params"]
    assert params["to"] == to_str


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_omits_to_when_not_provided(adapter: UpbitAdapter):
    """to 인자가 없으면 params에 포함되지 않는다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW) as mock_req:
        await adapter.get_candles("KRW-BTC")

    params = mock_req.call_args.kwargs["params"]
    assert "to" not in params


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_stream_type_is_snapshot(adapter: UpbitAdapter):
    """모든 Candle의 stream_type이 SNAPSHOT이다."""
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW):
        result = await adapter.get_candles("KRW-BTC")

    assert all(c.stream_type == StreamType.SNAPSHOT for c in result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_candles_candle_fields_mapped_correctly(adapter: UpbitAdapter):
    """Candle 필드가 API 응답과 올바르게 매핑된다."""
    raw = _SAMPLE_RAW[1]  # 과거 항목 (역전 후 index 0)
    with patch.object(adapter, "_request", new_callable=AsyncMock, return_value=_SAMPLE_RAW):
        result = await adapter.get_candles("KRW-BTC")

    candle = result[0]
    assert candle.code == raw["market"]
    assert candle.opening_price == raw["opening_price"]
    assert candle.high_price == raw["high_price"]
    assert candle.low_price == raw["low_price"]
    assert candle.trade_price == raw["trade_price"]
    assert candle.timestamp == raw["timestamp"]


# _timeframe_to_candle_type


@pytest.mark.unit
@pytest.mark.parametrize(
    "timeframe, expected",
    [
        (Timeframe.SECOND, CandleType.SECOND),
        (Timeframe.MINUTE_1, CandleType.MINUTE_1),
        (Timeframe.MINUTE_3, CandleType.MINUTE_3),
        (Timeframe.MINUTE_5, CandleType.MINUTE_5),
        (Timeframe.HALF_HOUR, CandleType.HALF_HOUR),
        (Timeframe.HOUR, CandleType.HOUR),
        (Timeframe.HOUR_4, CandleType.HOUR_4),
    ],
)
def test_timeframe_to_candle_type_mapping(timeframe: Timeframe, expected: CandleType):
    """각 Timeframe이 대응하는 CandleType으로 변환된다."""
    assert UpbitAdapter._timeframe_to_candle_type(timeframe) == expected

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import unquote, urlencode

import jwt
import pytest
from src.connection.adapter import UpbitAdapter

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

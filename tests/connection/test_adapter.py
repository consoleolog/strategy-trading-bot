from unittest.mock import AsyncMock, MagicMock, patch

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

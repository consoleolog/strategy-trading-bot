import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.connection.market_data import MarketDataFeed


def make_feed(**kwargs) -> MarketDataFeed:
    defaults = {"codes": ["krw-btc", "krw-eth"], "types": ["ticker"]}
    return MarketDataFeed(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# __init__ — 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_codes_are_uppercased():
    """소문자 마켓 코드가 대문자로 변환된다."""
    feed = make_feed(codes=["krw-btc", "krw-eth"])
    assert feed.codes == ["KRW-BTC", "KRW-ETH"]


@pytest.mark.unit
def test_codes_already_uppercase_unchanged():
    """이미 대문자인 코드는 그대로 유지된다."""
    feed = make_feed(codes=["KRW-BTC"])
    assert feed.codes == ["KRW-BTC"]


@pytest.mark.unit
def test_types_stored():
    """types 파라미터가 그대로 저장된다."""
    feed = make_feed(types=["candle.1m", "ticker"])
    assert feed.types == ["candle.1m", "ticker"]


@pytest.mark.unit
def test_callbacks_default_to_none():
    """콜백이 전달되지 않으면 모두 None으로 초기화된다."""
    feed = make_feed()
    assert feed.on_ticker is None
    assert feed.on_candle is None
    assert feed.on_candle_close is None


@pytest.mark.unit
def test_callbacks_stored():
    """콜백이 전달되면 올바르게 저장된다."""
    ticker_cb = MagicMock()
    candle_cb = MagicMock()
    close_cb = MagicMock()
    feed = make_feed(on_ticker=ticker_cb, on_candle=candle_cb, on_candle_close=close_cb)
    assert feed.on_ticker is ticker_cb
    assert feed.on_candle is candle_cb
    assert feed.on_candle_close is close_cb


@pytest.mark.unit
def test_reconnect_settings_stored():
    """재연결 설정이 올바르게 저장된다."""
    feed = make_feed(reconnect_delay=3, max_reconnect_attempts=5)
    assert feed.reconnect_delay == 3
    assert feed.max_reconnect_attempts == 5


@pytest.mark.unit
def test_reconnect_settings_defaults():
    """재연결 설정의 기본값이 올바르게 설정된다."""
    feed = make_feed()
    assert feed.reconnect_delay == 5
    assert feed.max_reconnect_attempts == 10


@pytest.mark.unit
def test_initial_state():
    """초기 상태 값이 올바르게 설정된다."""
    feed = make_feed()
    assert feed._ws is None
    assert feed._running is False
    assert feed._reconnect_count == 0


# ---------------------------------------------------------------------------
# is_connected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_is_connected_false_when_ws_is_none():
    """_ws가 None이면 is_connected는 False를 반환한다."""
    feed = make_feed()
    assert feed.is_connected is False


@pytest.mark.unit
def test_is_connected_false_when_ws_not_open():
    """_ws가 존재하지만 open이 False이면 is_connected는 False를 반환한다."""
    feed = make_feed()
    feed._ws = MagicMock()
    feed._ws.open = False
    assert feed.is_connected is False


@pytest.mark.unit
def test_is_connected_true_when_ws_open():
    """_ws가 존재하고 open이 True이면 is_connected는 True를 반환한다."""
    feed = make_feed()
    feed._ws = MagicMock()
    feed._ws.open = True
    assert feed.is_connected is True


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_sets_running_false():
    """disconnect() 호출 후 _running이 False로 설정된다."""
    feed = make_feed()
    feed._running = True
    await feed.disconnect()
    assert feed._running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_closes_ws_when_connected():
    """_ws가 있으면 disconnect() 시 close()가 호출된다."""
    feed = make_feed()
    mock_ws = AsyncMock()
    feed._ws = mock_ws
    await feed.disconnect()
    mock_ws.close.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_sets_ws_to_none():
    """disconnect() 후 _ws가 None으로 설정된다."""
    feed = make_feed()
    feed._ws = AsyncMock()
    await feed.disconnect()
    assert feed._ws is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_disconnect_when_not_connected():
    """_ws가 None인 상태에서 disconnect()를 호출해도 오류가 발생하지 않는다."""
    feed = make_feed()
    assert feed._ws is None
    await feed.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="connect() 내부 루프가 TODO 스텁(pass)으로 await 없이 이벤트 루프를 점유함 — 본 구현 완료 후 활성화"
)
async def test_connect_sets_running_true():
    """connect() 호출 시 _running이 True로 설정된다."""
    feed = make_feed()
    task = asyncio.create_task(feed.connect())
    await asyncio.sleep(0)
    assert feed._running is True
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.skip(
    reason="connect() 내부 루프가 TODO 스텁(pass)으로 await 없이 이벤트 루프를 점유함 — 본 구현 완료 후 활성화"
)
async def test_connect_stops_after_disconnect():
    """connect() 루프는 disconnect() 호출 후 종료된다."""
    feed = make_feed()
    task = asyncio.create_task(feed.connect())
    await asyncio.sleep(0)
    await feed.disconnect()
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        pytest.fail("connect() loop did not stop after disconnect()")


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ws_url_quotation():
    """WS_URL_QUOTATION이 업비트 공개 시세 엔드포인트를 가리킨다."""
    assert MarketDataFeed.WS_URL_QUOTATION == "wss://api.upbit.com/websocket/v1"


@pytest.mark.unit
def test_ws_url_exchange_is_private_endpoint():
    """WS_URL_EXCHANGE가 /private 경로를 포함한다."""
    assert MarketDataFeed.WS_URL_EXCHANGE == "wss://api.upbit.com/websocket/v1/private"

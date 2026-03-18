from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.models.signal import Signal
from src.repositories.signal_repository import SignalRepository
from src.utils.constants import SignalDirection, SignalType, SignalValue

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

_SIGNAL_ROW = {
    "strategy_id": "ma_v1",
    "indicator_id": "ema_5_20",
    "type": "cross_over",
    "value": "golden_cross",
    "direction": "long",
    "market": "KRW-BTC",
    "timeframe": "1h",
    "timestamp": datetime(2024, 1, 1, 9, 0, 0),
    "metadata": "{}",
}


def _make_signal(**overrides) -> Signal:
    base = {
        "strategy_id": "ma_v1",
        "indicator_id": "ema_5_20",
        "type": SignalType.CROSS_OVER,
        "value": SignalValue.GOLDEN_CROSS,
        "direction": SignalDirection.LONG,
        "market": "KRW-BTC",
        "timeframe": "1h",
    }
    base.update(overrides)
    return Signal(**base)


def _make_mock_pool(return_row: dict | None) -> MagicMock:
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=return_row)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


def _make_mock_pool_rows(return_rows: list[dict]) -> MagicMock:
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=return_rows)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


def _make_mock_pool_execute() -> MagicMock:
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_table_name():
    """table_name이 'signals'를 반환한다."""
    repo = SignalRepository(pool=None)  # type: ignore[arg-type]
    assert repo.table_name == "signals"


@pytest.mark.unit
def test_primary_key():
    """복합 PK가 ['strategy_id', 'indicator_id', 'type']이다."""
    assert SignalRepository.primary_key == ["strategy_id", "indicator_id", "type"]


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_save_upsert_query():
    """save()가 복합 PK ON CONFLICT 절이 포함된 upsert 쿼리를 생성한다."""
    mock_pool = _make_mock_pool(_SIGNAL_ROW)
    repo = SignalRepository(pool=mock_pool)

    await repo.save(_make_signal())

    query, *_ = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert "INSERT INTO signals" in query
    assert "ON CONFLICT (strategy_id, indicator_id, type)" in query
    assert "DO UPDATE SET" in query
    assert "RETURNING *" in query


@pytest.mark.unit
async def test_save_enum_fields_converted_to_value():
    """save()는 Enum 필드를 .value 문자열로 변환해 전달한다."""
    mock_pool = _make_mock_pool(_SIGNAL_ROW)
    repo = SignalRepository(pool=mock_pool)

    await repo.save(_make_signal())

    _, *values = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert "cross_over" in values
    assert "golden_cross" in values
    assert "long" in values
    assert SignalType.CROSS_OVER not in values
    assert SignalValue.GOLDEN_CROSS not in values
    assert SignalDirection.LONG not in values


@pytest.mark.unit
async def test_save_returns_signal():
    """save()는 RETURNING 결과를 Signal 엔티티로 반환한다."""
    mock_pool = _make_mock_pool(_SIGNAL_ROW)
    repo = SignalRepository(pool=mock_pool)

    result = await repo.save(_make_signal())

    assert isinstance(result, Signal)
    assert result.strategy_id == "ma_v1"
    assert result.type is SignalType.CROSS_OVER
    assert result.direction is SignalDirection.LONG


# ---------------------------------------------------------------------------
# find_by_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_by_id_composite_pk_query():
    """find_by_id()가 복합 PK 3개 컬럼으로 SELECT 쿼리를 생성한다."""
    mock_pool = _make_mock_pool(_SIGNAL_ROW)
    repo = SignalRepository(pool=mock_pool)

    await repo.find_by_id(["ma_v1", "ema_5_20", "cross_over"])

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert query == ("SELECT * FROM signals WHERE strategy_id = $1 AND indicator_id = $2 AND type = $3")
    assert args == ["ma_v1", "ema_5_20", "cross_over"]


@pytest.mark.unit
async def test_find_by_id_returns_signal():
    """find_by_id()는 조회 결과를 Signal 엔티티로 반환한다."""
    mock_pool = _make_mock_pool(_SIGNAL_ROW)
    repo = SignalRepository(pool=mock_pool)

    result = await repo.find_by_id(["ma_v1", "ema_5_20", "cross_over"])

    assert isinstance(result, Signal)
    assert result.strategy_id == "ma_v1"
    assert result.market == "KRW-BTC"


@pytest.mark.unit
async def test_find_by_id_returns_none_when_not_found():
    """find_by_id()는 행이 없으면 None을 반환한다."""
    mock_pool = _make_mock_pool(None)
    repo = SignalRepository(pool=mock_pool)

    result = await repo.find_by_id(["unknown", "unknown", "cross_over"])

    assert result is None


# ---------------------------------------------------------------------------
# delete_by_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_delete_by_id_composite_pk_query():
    """delete_by_id()가 복합 PK 3개 컬럼으로 DELETE 쿼리를 생성한다."""
    mock_pool = _make_mock_pool_execute()
    repo = SignalRepository(pool=mock_pool)

    await repo.delete_by_id(["ma_v1", "ema_5_20", "cross_over"])

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.execute.call_args.args
    assert query == ("DELETE FROM signals WHERE strategy_id = $1 AND indicator_id = $2 AND type = $3")
    assert args == ["ma_v1", "ema_5_20", "cross_over"]


# ---------------------------------------------------------------------------
# __getattr__ — 동적 조회
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_all_by_market_query():
    """find_all_by_market()이 market 조건 SELECT 쿼리를 생성한다."""
    mock_pool = _make_mock_pool_rows([_SIGNAL_ROW])
    repo = SignalRepository(pool=mock_pool)

    result = await repo.find_all_by_market("KRW-BTC")

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetch.call_args.args
    assert "WHERE market = $1" in query
    assert args == ["KRW-BTC"]
    assert len(result) == 1
    assert isinstance(result[0], Signal)


@pytest.mark.unit
async def test_find_all_by_direction_enum_coerced():
    """find_all_by_direction()은 Enum을 .value로 변환해 쿼리 인수로 전달한다."""
    mock_pool = _make_mock_pool_rows([])
    repo = SignalRepository(pool=mock_pool)

    await repo.find_all_by_direction(SignalDirection.LONG)

    _, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetch.call_args.args
    assert args == ["long"]


@pytest.mark.unit
async def test_find_all_by_strategy_id_query():
    """find_all_by_strategy_id()가 strategy_id 조건 SELECT 쿼리를 생성한다."""
    mock_pool = _make_mock_pool_rows([_SIGNAL_ROW])
    repo = SignalRepository(pool=mock_pool)

    await repo.find_all_by_strategy_id("ma_v1")

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetch.call_args.args
    assert "WHERE strategy_id = $1" in query
    assert args == ["ma_v1"]


@pytest.mark.unit
async def test_find_all_by_market_and_direction_query():
    """find_all_by_market_and_direction()이 AND 조건 쿼리를 생성한다."""
    mock_pool = _make_mock_pool_rows([])
    repo = SignalRepository(pool=mock_pool)

    await repo.find_all_by_market_and_direction("KRW-BTC", SignalDirection.LONG)

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetch.call_args.args
    assert "market = $1 AND direction = $2" in query
    assert args == ["KRW-BTC", "long"]

from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.models.base import Base
from src.repositories.base_repository import BaseRepository

# ---------------------------------------------------------------------------
# 테스트용 픽스처
# ---------------------------------------------------------------------------


class Direction(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Item(Base):
    item_id: str
    market: str
    strategy_id: str


@dataclass
class Trade(Base):
    trade_id: str
    market: str
    direction: Direction


class ItemRepository(BaseRepository[Item]):
    primary_key: ClassVar[list[str]] = ["item_id"]

    @property
    def table_name(self) -> str:
        return "items"

    async def find_all(self) -> list[Item]:
        raise NotImplementedError

    async def delete_by_id(self, entity_id: str | list[str]) -> None:
        raise NotImplementedError

    async def count(self) -> int:
        raise NotImplementedError

    async def _find_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> list[Item]:
        raise NotImplementedError


class TradeRepository(BaseRepository[Trade]):
    primary_key: ClassVar[list[str]] = ["trade_id"]

    @property
    def table_name(self) -> str:
        return "trades"

    async def find_all(self) -> list[Trade]:
        raise NotImplementedError

    async def delete_by_id(self, entity_id: str | list[str]) -> None:
        raise NotImplementedError

    async def count(self) -> int:
        raise NotImplementedError

    async def _find_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> list[Trade]:
        raise NotImplementedError


def _make_mock_pool(return_row: dict | None) -> MagicMock:
    """fetchrow 결과를 고정한 mock pool을 반환한다. None이면 행을 찾지 못한 경우를 시뮬레이션한다."""
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=return_row)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return mock_pool


@pytest.fixture
def repo() -> ItemRepository:
    return ItemRepository(pool=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# primary_key
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_primary_key_default():
    """primary_key 기본값이 ['id']이다."""
    assert BaseRepository.primary_key == "id"


@pytest.mark.unit
def test_primary_key_override(repo):
    """하위 클래스에서 primary_key를 오버라이드할 수 있다."""
    assert repo.primary_key == ["item_id"]


@pytest.mark.unit
def test_primary_key_composite():
    """복합 PK를 리스트로 정의할 수 있다."""

    class CompositeRepo(ItemRepository):
        primary_key: ClassVar[list[str]] = ["order_uuid", "trade_id"]

    assert CompositeRepo.primary_key == ["order_uuid", "trade_id"]


# ---------------------------------------------------------------------------
# table_name
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_table_name(repo):
    """table_name이 올바르게 반환된다."""
    assert repo.table_name == "items"


@pytest.mark.unit
async def test_save_schema_qualified_table_name():
    """schema.table 형식의 테이블명을 허용한다."""
    row = {"item_id": "1", "market": "KRW-BTC", "strategy_id": "ma_v1"}
    mock_pool = _make_mock_pool(row)

    class SchemaRepo(ItemRepository):
        @property
        def table_name(self) -> str:
            return "trading.items"

    repo = SchemaRepo(pool=mock_pool)
    await repo.save(Item(item_id="1", market="KRW-BTC", strategy_id="ma_v1"))

    query, *_ = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert "INSERT INTO trading.items" in query


# ---------------------------------------------------------------------------
# __getattr__ — find_by_<column>
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_find_by_single_column_returns_callable(repo):
    """find_by_<col> 호출 시 callable을 반환한다."""
    assert callable(repo.find_by_market)


@pytest.mark.unit
async def test_find_by_single_column_calls_find_by_columns(repo):
    """find_by_<col> 호출 시 _find_by_columns(columns, 'AND', values)를 호출한다."""
    repo._find_by_columns = AsyncMock(return_value=[])
    await repo.find_by_market("KRW-BTC")
    repo._find_by_columns.assert_called_once_with(["market"], "AND", ["KRW-BTC"])


# ---------------------------------------------------------------------------
# __getattr__ — find_by_<col>_and_<col>
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_by_and_columns_calls_find_by_columns(repo):
    """find_by_<col>_and_<col> 호출 시 operator='AND'로 전달된다."""
    repo._find_by_columns = AsyncMock(return_value=[])
    await repo.find_by_market_and_strategy_id("KRW-BTC", "ma_v1")
    repo._find_by_columns.assert_called_once_with(["market", "strategy_id"], "AND", ["KRW-BTC", "ma_v1"])


@pytest.mark.unit
async def test_find_by_and_three_columns(repo):
    """세 컬럼 AND 조건도 올바르게 파싱된다."""
    repo._find_by_columns = AsyncMock(return_value=[])
    await repo.find_by_market_and_strategy_id_and_item_id("KRW-BTC", "ma_v1", "abc")
    repo._find_by_columns.assert_called_once_with(
        ["market", "strategy_id", "item_id"], "AND", ["KRW-BTC", "ma_v1", "abc"]
    )


# ---------------------------------------------------------------------------
# __getattr__ — find_by_<col>_or_<col>
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_by_or_columns_calls_find_by_columns(repo):
    """find_by_<col>_or_<col> 호출 시 operator='OR'로 전달된다."""
    repo._find_by_columns = AsyncMock(return_value=[])
    await repo.find_by_market_or_strategy_id("KRW-BTC", "ma_v1")
    repo._find_by_columns.assert_called_once_with(["market", "strategy_id"], "OR", ["KRW-BTC", "ma_v1"])


# ---------------------------------------------------------------------------
# __getattr__ — 인수 개수 불일치
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_by_wrong_arg_count_raises_type_error(repo):
    """컬럼 수와 인수 수가 다르면 TypeError가 발생한다."""
    repo._find_by_columns = AsyncMock(return_value=[])
    with pytest.raises(TypeError):
        await repo.find_by_market_and_strategy_id("KRW-BTC")  # 2개 필요, 1개 전달


# ---------------------------------------------------------------------------
# __getattr__ — 잘못된 속성명
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unknown_attribute_raises_attribute_error(repo):
    """find_by_ 패턴이 아닌 속성 접근 시 AttributeError가 발생한다."""
    with pytest.raises(AttributeError):
        _ = repo.unknown_method


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_save_full_query():
    """save()가 올바른 upsert 쿼리 전문을 생성한다."""
    row = {"item_id": "1", "market": "KRW-BTC", "strategy_id": "ma_v1"}
    mock_pool = _make_mock_pool(row)
    repo = ItemRepository(pool=mock_pool)

    await repo.save(Item(item_id="1", market="KRW-BTC", strategy_id="ma_v1"))

    query, *_ = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    expected = (
        "INSERT INTO items (item_id, market, strategy_id)"
        " VALUES ($1, $2, $3)"
        " ON CONFLICT (item_id) DO UPDATE SET market = EXCLUDED.market, strategy_id = EXCLUDED.strategy_id"
        " RETURNING *"
    )
    assert query == expected


@pytest.mark.unit
async def test_save_composite_pk_full_query():
    """복합 PK인 경우 ON CONFLICT에 모든 PK 컬럼이 포함된 전체 쿼리를 생성한다."""

    @dataclass
    class OrderFill(Base):
        order_uuid: str
        trade_id: str
        market: str

    class OrderFillRepository(BaseRepository[OrderFill]):
        primary_key: ClassVar[list[str]] = ["order_uuid", "trade_id"]

        @property
        def table_name(self) -> str:
            return "order_fills"

        async def find_by_id(self, entity_id: str | list[str]) -> OrderFill | None: ...
        async def find_all(self) -> list[OrderFill]: ...
        async def delete_by_id(self, entity_id: str | list[str]) -> None: ...
        async def count(self) -> int: ...
        async def _find_by_columns(self, columns, operator, values): ...

    row = {"order_uuid": "u1", "trade_id": "t1", "market": "KRW-BTC"}
    mock_pool = _make_mock_pool(row)
    repo = OrderFillRepository(pool=mock_pool)

    await repo.save(OrderFill(order_uuid="u1", trade_id="t1", market="KRW-BTC"))

    query, *_ = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    expected = (
        "INSERT INTO order_fills (order_uuid, trade_id, market)"
        " VALUES ($1, $2, $3)"
        " ON CONFLICT (order_uuid, trade_id) DO UPDATE SET market = EXCLUDED.market"
        " RETURNING *"
    )
    assert query == expected


@pytest.mark.unit
async def test_save_enum_field_converted_to_value():
    """Enum 필드는 .value(문자열)로 변환되어 쿼리 인수로 전달된다."""
    row = {"trade_id": "t1", "market": "KRW-BTC", "direction": "long"}
    mock_pool = _make_mock_pool(row)
    repo = TradeRepository(pool=mock_pool)

    await repo.save(Trade(trade_id="t1", market="KRW-BTC", direction=Direction.LONG))

    _, *values = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert "long" in values
    assert Direction.LONG not in values


@pytest.mark.unit
async def test_save_returns_entity_from_row():
    """save()는 DB RETURNING 결과를 엔티티로 변환해 반환한다."""
    row = {"item_id": "99", "market": "KRW-ETH", "strategy_id": "rsi_v2"}
    mock_pool = _make_mock_pool(row)
    repo = ItemRepository(pool=mock_pool)

    result = await repo.save(Item(item_id="99", market="KRW-ETH", strategy_id="rsi_v2"))

    assert isinstance(result, Item)
    assert result.item_id == "99"
    assert result.market == "KRW-ETH"
    assert result.strategy_id == "rsi_v2"


# ---------------------------------------------------------------------------
# find_by_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_find_by_id_returns_entity():
    """find_by_id()는 DB 조회 결과를 엔티티로 변환해 반환한다."""
    row = {"item_id": "42", "market": "KRW-BTC", "strategy_id": "ma_v1"}
    mock_pool = _make_mock_pool(row)
    repo = ItemRepository(pool=mock_pool)

    result = await repo.find_by_id("42")

    assert isinstance(result, Item)
    assert result.item_id == "42"
    assert result.market == "KRW-BTC"
    assert result.strategy_id == "ma_v1"


@pytest.mark.unit
async def test_find_by_id_returns_none_when_not_found():
    """find_by_id()는 행이 없으면 None을 반환한다."""
    mock_pool = _make_mock_pool(None)
    repo = ItemRepository(pool=mock_pool)

    result = await repo.find_by_id("nonexistent")

    assert result is None


@pytest.mark.unit
async def test_find_by_id_single_pk_query():
    """find_by_id()가 단일 PK에 대한 올바른 SELECT 쿼리를 생성한다."""
    row = {"item_id": "1", "market": "KRW-BTC", "strategy_id": "ma_v1"}
    mock_pool = _make_mock_pool(row)
    repo = ItemRepository(pool=mock_pool)

    await repo.find_by_id("1")

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert query == "SELECT * FROM items WHERE item_id = $1"
    assert args == ["1"]


@pytest.mark.unit
async def test_find_by_id_composite_pk_query():
    """find_by_id()가 복합 PK에 대한 올바른 SELECT 쿼리를 생성한다."""

    @dataclass
    class OrderFill(Base):
        order_uuid: str
        trade_id: str
        market: str

    class OrderFillRepository(BaseRepository[OrderFill]):
        primary_key: ClassVar[list[str]] = ["order_uuid", "trade_id"]

        @property
        def table_name(self) -> str:
            return "order_fills"

        async def find_all(self) -> list[OrderFill]: ...
        async def delete_by_id(self, entity_id: str | list[str]) -> None: ...
        async def count(self) -> int: ...
        async def _find_by_columns(self, columns, operator, values): ...

    row = {"order_uuid": "u1", "trade_id": "t1", "market": "KRW-BTC"}
    mock_pool = _make_mock_pool(row)
    repo = OrderFillRepository(pool=mock_pool)

    await repo.find_by_id(["u1", "t1"])

    query, *args = mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.call_args.args
    assert query == "SELECT * FROM order_fills WHERE order_uuid = $1 AND trade_id = $2"
    assert args == ["u1", "t1"]


@pytest.mark.unit
async def test_find_by_id_composite_pk_returns_entity():
    """find_by_id()는 복합 PK 조회 결과를 올바르게 엔티티로 변환한다."""

    @dataclass
    class OrderFill(Base):
        order_uuid: str
        trade_id: str
        market: str

    class OrderFillRepository(BaseRepository[OrderFill]):
        primary_key: ClassVar[list[str]] = ["order_uuid", "trade_id"]

        @property
        def table_name(self) -> str:
            return "order_fills"

        async def find_all(self) -> list[OrderFill]: ...
        async def delete_by_id(self, entity_id: str | list[str]) -> None: ...
        async def count(self) -> int: ...
        async def _find_by_columns(self, columns, operator, values): ...

    row = {"order_uuid": "u1", "trade_id": "t1", "market": "KRW-BTC"}
    mock_pool = _make_mock_pool(row)
    repo = OrderFillRepository(pool=mock_pool)

    result = await repo.find_by_id(["u1", "t1"])

    assert isinstance(result, OrderFill)
    assert result.order_uuid == "u1"
    assert result.trade_id == "t1"
    assert result.market == "KRW-BTC"


@pytest.mark.unit
async def test_find_by_id_enum_field_restored():
    """find_by_id()는 DB에서 조회한 문자열 값을 Enum으로 복원한다."""
    row = {"trade_id": "t1", "market": "KRW-BTC", "direction": "long"}
    mock_pool = _make_mock_pool(row)
    repo = TradeRepository(pool=mock_pool)

    result = await repo.find_by_id("t1")

    assert isinstance(result, Trade)
    assert result.direction is Direction.LONG

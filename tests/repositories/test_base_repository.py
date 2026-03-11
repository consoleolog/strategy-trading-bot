from dataclasses import dataclass
from typing import Any, ClassVar
from unittest.mock import AsyncMock

import pytest
from src.models.base import Base
from src.repositories.base_repository import BaseRepository

# ---------------------------------------------------------------------------
# 테스트용 픽스처
# ---------------------------------------------------------------------------


@dataclass
class Item(Base):
    item_id: str
    market: str
    strategy_id: str


class ItemRepository(BaseRepository[Item]):
    primary_key: ClassVar[list[str]] = ["item_id"]

    @property
    def table_name(self) -> str:
        return "items"

    async def save(self, entity: Item) -> Item:
        raise NotImplementedError

    async def find_by_id(self, entity_id: str | list[str]) -> Item | None:
        raise NotImplementedError

    async def find_all(self) -> list[Item]:
        raise NotImplementedError

    async def delete_by_id(self, entity_id: str | list[str]) -> None:
        raise NotImplementedError

    async def count(self) -> int:
        raise NotImplementedError

    async def _find_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> list[Item]:
        raise NotImplementedError


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

import re
from abc import abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar, Generic, TypeVar

from ..connections.database import PostgresPool
from ..models.base import Base

T = TypeVar("T", bound=Base)

_FIND_BY_PATTERN = re.compile(r"^find_by_(.+)$")


class BaseRepository(Generic[T]):
    """비동기 기반 레포지토리."""

    primary_key: ClassVar[str | list[str]] = "id"

    def __init__(self, pool: PostgresPool) -> None:
        self.pool = pool

    @property
    @abstractmethod
    def table_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def save(self, entity: T) -> T:
        raise NotImplementedError()

    @abstractmethod
    async def find_by_id(self, entity_id: str | list[str]) -> T | None:
        raise NotImplementedError()

    @abstractmethod
    async def find_all(self) -> list[T]:
        raise NotImplementedError()

    @abstractmethod
    async def delete_by_id(self, entity_id: str | list[str]) -> None:
        raise NotImplementedError()

    # ------------------------------------------------------------------
    # 동적 쿼리 메서드 — find_by_<col>, find_by_<col>_and_<col>, _or_
    # ------------------------------------------------------------------

    @abstractmethod
    async def _find_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> list[T]:
        """컬럼 목록과 연산자(AND/OR)로 조회한다. 동적 메서드의 실제 구현부."""
        ...

    def __getattr__(self, name: str) -> Callable:
        match = _FIND_BY_PATTERN.match(name)
        if not match:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

        body = match.group(1)

        if "_or_" in body:
            columns = body.split("_or_")
            operator = "OR"
        else:
            columns = body.split("_and_")
            operator = "AND"

        async def _dynamic(*values: Any) -> list[T]:
            if len(values) != len(columns):
                raise TypeError(f"{name}() takes {len(columns)} argument(s), got {len(values)}")
            return await self._find_by_columns(columns, operator, list(values))

        return _dynamic

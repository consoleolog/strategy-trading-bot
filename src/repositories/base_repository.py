import json
import re
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import fields
from enum import Enum
from typing import Any, ClassVar, Generic, TypeVar, cast

from ..connections.database import PostgresPool
from ..models.base import Base

T = TypeVar("T", bound=Base)

_FIND_BY_PATTERN = re.compile(r"^find_by_(.+)$")
_SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_SAFE_TABLE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$")


def _validate_identifier(name: str) -> str:
    """컬럼명·PK 컬럼 식별자를 검증한다 (영문자·숫자·언더스코어만 허용).

    Raises:
        ValueError: 허용되지 않는 문자가 포함된 경우.
    """
    if not _SAFE_IDENTIFIER.match(name):
        raise ValueError(f"안전하지 않은 SQL 식별자: {name!r}")
    return name


def _validate_table(name: str) -> str:
    """테이블명 식별자를 검증한다 (schema.table 형식 허용).

    Raises:
        ValueError: 허용되지 않는 문자가 포함된 경우.
    """
    if not _SAFE_TABLE.match(name):
        raise ValueError(f"안전하지 않은 SQL 테이블명: {name!r}")
    return name


class BaseRepository(Generic[T]):
    """비동기 기반 레포지토리."""

    primary_key: ClassVar[str | list[str]] = "id"

    def __init__(self, pool: PostgresPool) -> None:
        self.pool = pool

    @property
    @abstractmethod
    def table_name(self) -> str:
        raise NotImplementedError()

    async def save(self, entity: T) -> T:
        """엔티티를 저장하거나 갱신한다 (upsert).

        dataclasses.fields()로 컬럼과 값을 추출하고
        INSERT ... ON CONFLICT DO UPDATE SET ... RETURNING * 쿼리를 실행한다.
        """
        entity_fields = fields(cast(Any, entity))
        columns = [_validate_identifier(f.name) for f in entity_fields]
        values = [
            v.value
            if isinstance(v := getattr(entity, f.name), Enum)
            else json.dumps(v)
            if isinstance(v, dict | list)
            else v
            for f in entity_fields
        ]

        pk = self.primary_key if isinstance(self.primary_key, list) else [self.primary_key]
        pk = [_validate_identifier(k) for k in pk]
        table = _validate_table(self.table_name)

        col_list = ", ".join(columns)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
        update_set = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col not in pk)
        conflict_target = ", ".join(pk)

        query = (
            f"INSERT INTO {table} ({col_list})"  # nosec B608
            f" VALUES ({placeholders})"
            f" ON CONFLICT ({conflict_target}) DO UPDATE SET {update_set}"
            f" RETURNING *"
        )

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            return type(entity).from_dict(dict(row))

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

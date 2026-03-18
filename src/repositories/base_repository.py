import asyncio
import dis
import json
import re
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import fields
from enum import Enum
from typing import Any, ClassVar, Generic, TypeVar, cast, get_args

from ..connections.database import PostgresPool
from ..models.base import Base

T = TypeVar("T", bound=Base)

_FIND_BY_PATTERN = re.compile(r"^find_by_(.+)$")
_FIND_ALL_BY_PATTERN = re.compile(r"^find_all_by_(.+)$")
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


def _parse_columns_operator(body: str) -> tuple[list[str], str]:
    """메서드명 바디에서 컬럼 목록과 연산자를 파싱한다.

    ``market_and_timeframe``  → (["market", "timeframe"], "AND")
    ``market_or_strategy_id`` → (["market", "strategy_id"], "OR")
    """
    if "_or_" in body:
        return body.split("_or_"), "OR"
    return body.split("_and_"), "AND"


def _is_stub(func: Any) -> bool:
    """코루틴 함수 바디가 스텁(``...`` / ``pass`` / ``raise NotImplementedError``)인지 확인한다.

    Spring Data 처럼 메서드 선언만으로 자동 구현이 필요한 메서드를 감지하는 데 쓰인다.
    """
    if not asyncio.iscoroutinefunction(func):
        return False
    code = func.__code__
    # 인자 외 추가 로컬 변수가 있으면 실제 구현으로 간주
    if code.co_nlocals > code.co_argcount:
        return False
    instructions = [
        i for i in dis.get_instructions(code) if i.opname not in ("RESUME", "RETURN_GENERATOR", "COPY_FREE_VARS")
    ]
    opnames = {i.opname for i in instructions}
    # raise NotImplementedError 패턴
    if "RAISE_VARARGS" in opnames:
        return True
    # pass / ... 패턴: 상수 로드 + 반환만 존재
    return opnames <= {"LOAD_CONST", "POP_TOP", "RETURN_VALUE", "RETURN_CONST"}


def _make_find_one(method_name: str, columns: list[str], operator: str) -> Any:
    """``_find_by_columns``를 호출하는 단일 조회 메서드를 생성한다."""

    async def _method(self: Any, *values: Any) -> Any:
        if len(values) != len(columns):
            raise TypeError(f"{method_name}() takes {len(columns)} argument(s), got {len(values)}")
        coerced = [v.value if isinstance(v, Enum) else v for v in values]
        return await self._find_by_columns(columns, operator, coerced)

    _method.__name__ = method_name
    return _method


def _make_find_all(method_name: str, columns: list[str], operator: str) -> Any:
    """``_find_all_by_columns``를 호출하는 복수 조회 메서드를 생성한다."""

    async def _method(self: Any, *values: Any) -> Any:
        if len(values) != len(columns):
            raise TypeError(f"{method_name}() takes {len(columns)} argument(s), got {len(values)}")
        coerced = [v.value if isinstance(v, Enum) else v for v in values]
        return await self._find_all_by_columns(columns, operator, coerced)

    _method.__name__ = method_name
    return _method


class BaseRepository(Generic[T]):
    """비동기 기반 레포지토리.

    서브클래스에서 ``find_by_*`` / ``find_all_by_*`` 메서드를 ``...`` 스텁으로
    선언하기만 하면 메서드명을 분석해 SQL 쿼리를 자동 생성한다.

    규칙:
        - ``find_by_<col>_and_<col>``      → ``T | None``     (단일 조회)
        - ``find_all_by_<col>_and_<col>``  → ``list[T]``      (복수 조회)
        - ``_and_`` 구분자 → AND, ``_or_`` 구분자 → OR
        - ``Enum`` 값은 자동으로 ``.value``(문자열)로 변환

    Example::

        class SignalRepository(BaseRepository[Signal]):
            async def find_by_strategy_id_and_market(
                self, strategy_id: str, market: str
            ) -> Signal | None: ...

            async def find_all_by_market(self, market: str) -> list[Signal]: ...
    """

    primary_key: ClassVar[str | list[str]] = "id"
    _entity_class: ClassVar[type]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # 제네릭 타입 인자에서 엔티티 클래스 캡처
        for base in getattr(cls, "__orig_bases__", []):
            args = get_args(base)
            if args and isinstance(args[0], type):
                cls._entity_class = args[0]
                break
        # 스텁으로 선언된 find_by_* / find_all_by_* 메서드 자동 구현
        for attr_name, func in list(vars(cls).items()):
            if not _is_stub(func):
                continue
            m = _FIND_ALL_BY_PATTERN.match(attr_name)
            if m:
                cols, op = _parse_columns_operator(m.group(1))
                setattr(cls, attr_name, _make_find_all(attr_name, cols, op))
                continue
            m = _FIND_BY_PATTERN.match(attr_name)
            if m:
                cols, op = _parse_columns_operator(m.group(1))
                setattr(cls, attr_name, _make_find_one(attr_name, cols, op))

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

    async def find_by_id(self, entity_id: str | list[str]) -> T | None:
        """PK로 단일 엔티티를 조회한다. 없으면 None을 반환한다."""
        pk = self.primary_key if isinstance(self.primary_key, list) else [self.primary_key]
        pk = [_validate_identifier(k) for k in pk]
        table = _validate_table(self.table_name)

        ids = entity_id if isinstance(entity_id, list) else [entity_id]
        conditions = " AND ".join(f"{col} = ${i + 1}" for i, col in enumerate(pk))
        query = f"SELECT * FROM {table} WHERE {conditions}"  # nosec B608

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *ids)
            if row is None:
                return None
            return self._entity_class.from_dict(dict(row))

    @abstractmethod
    async def delete_by_id(self, entity_id: str | list[str]) -> None:
        raise NotImplementedError()

    # ------------------------------------------------------------------
    # 쿼리 헬퍼 — find_by_* / find_all_by_* 의 실제 실행부
    # ------------------------------------------------------------------

    async def _find_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> T | None:
        """컬럼 목록과 연산자(AND/OR)로 단일 행을 조회한다.

        Returns:
            조건에 맞는 첫 번째 엔티티. 없으면 ``None``.
        """
        validated_cols = [_validate_identifier(col) for col in columns]
        table = _validate_table(self.table_name)
        conditions = f" {operator} ".join(f"{col} = ${i + 1}" for i, col in enumerate(validated_cols))
        query = f"SELECT * FROM {table} WHERE {conditions} LIMIT 1"  # nosec B608

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)
            if row is None:
                return None
            return self._entity_class.from_dict(dict(row))

    async def _find_all_by_columns(self, columns: list[str], operator: str, values: list[Any]) -> list[T]:
        """컬럼 목록과 연산자(AND/OR)로 복수 행을 조회한다.

        Returns:
            조건에 맞는 엔티티 목록.
        """
        validated_cols = [_validate_identifier(col) for col in columns]
        table = _validate_table(self.table_name)
        conditions = f" {operator} ".join(f"{col} = ${i + 1}" for i, col in enumerate(validated_cols))
        query = f"SELECT * FROM {table} WHERE {conditions}"  # nosec B608

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *values)
            return [self._entity_class.from_dict(dict(row)) for row in rows]

    # ------------------------------------------------------------------
    # 미선언 동적 메서드 — __getattr__ 폴백
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Callable:
        # find_all_by_* → 복수 조회 (list[T])
        m = _FIND_ALL_BY_PATTERN.match(name)
        if m:
            cols, op = _parse_columns_operator(m.group(1))

            async def _dynamic_all(*values: Any) -> list[T]:
                if len(values) != len(cols):
                    raise TypeError(f"{name}() takes {len(cols)} argument(s), got {len(values)}")
                coerced = [v.value if isinstance(v, Enum) else v for v in values]
                return await self._find_all_by_columns(cols, op, coerced)

            return _dynamic_all

        # find_by_* → 단일 조회 (T | None)
        m = _FIND_BY_PATTERN.match(name)
        if m:
            cols, op = _parse_columns_operator(m.group(1))

            async def _dynamic_one(*values: Any) -> T | None:
                if len(values) != len(cols):
                    raise TypeError(f"{name}() takes {len(cols)} argument(s), got {len(values)}")
                coerced = [v.value if isinstance(v, Enum) else v for v in values]
                return await self._find_by_columns(cols, op, coerced)

            return _dynamic_one

        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

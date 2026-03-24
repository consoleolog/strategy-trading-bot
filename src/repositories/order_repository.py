from typing import ClassVar

from ..connections import PostgresPool
from ..models import Order
from .base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Order 레포지토리.

    ``find_by_*`` / ``find_all_by_*`` 스텁은 메서드명에서 컬럼을 자동 파싱해 구현된다.
    Enum 파라미터는 ``.value`` 로 자동 변환된다.
    기본 키는 ``uuid`` 컬럼이다.
    """

    primary_key: ClassVar[str] = "uuid"

    def __init__(self, pool: PostgresPool) -> None:
        super().__init__(pool)

    @property
    def table_name(self) -> str:
        return "orders"

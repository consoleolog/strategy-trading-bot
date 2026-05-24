from typing import ClassVar

from ..connections import PostgresPool
from ..models import Trade
from .base_repository import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    """Trade 레포지토리.

    ``find_by_*`` / ``find_all_by_*`` 스텁은 메서드명에서 컬럼을 자동 파싱해 구현된다.
    Enum 파라미터는 ``.value`` 로 자동 변환된다.
    기본 키는 ``trade_id`` 컬럼이다.
    """

    primary_key: ClassVar[str] = "trade_id"

    def __init__(self, pool: PostgresPool) -> None:
        super().__init__(pool)

    @property
    def table_name(self) -> str:
        return "trading.trades"

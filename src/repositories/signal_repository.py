from typing import ClassVar

from ..connections.database import PostgresPool
from ..models.signal import Signal
from .base_repository import BaseRepository


class SignalRepository(BaseRepository[Signal]):
    """Signal 레포지토리.

    ``find_by_*`` / ``find_all_by_*`` 스텁은 메서드명에서 컬럼을 자동 파싱해 구현된다.
    Enum 파라미터는 ``.value`` 로 자동 변환된다.
    """

    primary_key: ClassVar[list[str]] = ["strategy_id", "indicator_id", "type"]

    def __init__(self, pool: PostgresPool) -> None:
        super().__init__(pool)

    @property
    def table_name(self) -> str:
        return "signals"

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..utils.constants import OrderSide
from .base import Base


@dataclass
class Trade(Base):
    """
    체결된 거래(Trade) 기록 모델

    Attributes:
        trade_id (UUID): 체결의 고유 식별자
        market (str): 마켓 코드 (예: KRW-BTC)
        side (OrderSide): 매수/매도 구분 (BID: 매수, ASK: 매도)
        volume (Decimal): 체결 수량
        price (Decimal): 체결 단가
        strategy_id (str): 이 체결을 발생시킨 전략의 식별자
        order_uuid (UUID): 연관된 업비트 주문 UUID
        fee (Decimal): 체결 수수료
        fee_asset (str): 수수료 자산 종류 (기본값: KRW)
        decision_id (UUID | None): 이 체결을 발생시킨 Decision의 식별자 (없으면 None)
        timestamp (datetime): 체결 시각
    """

    trade_id: UUID
    market: str
    side: OrderSide
    volume: Decimal
    price: Decimal
    strategy_id: str
    order_uuid: UUID
    fee: Decimal
    fee_asset: str = "KRW"
    decision_id: UUID | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.trade_id, str):
            self.trade_id = UUID(self.trade_id)
        if isinstance(self.order_uuid, str):
            self.order_uuid = UUID(self.order_uuid)
        if self.decision_id is not None and isinstance(self.decision_id, str):
            self.decision_id = UUID(self.decision_id)

        if isinstance(self.side, str):
            self.side = OrderSide(self.side)

        for field_name in ["volume", "price", "fee"]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    @property
    def value(self) -> Decimal:
        """체결 총액 (체결 단가 X 체결 수량)."""
        return self.volume * self.price

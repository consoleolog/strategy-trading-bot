from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .constants import OrderSide


@dataclass
class Trade:
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

    @classmethod
    def from_dict(cls, data: dict) -> "Trade":
        """딕셔너리 데이터를 Trade 객체로 변환합니다."""
        return cls(
            trade_id=data.get("trade_id"),
            market=data.get("market"),
            side=data.get("side"),
            volume=data.get("volume"),
            price=data.get("price"),
            strategy_id=data.get("strategy_id"),
            order_uuid=data.get("order_uuid"),
            fee=data.get("fee"),
            fee_asset=data.get("fee_asset", "KRW"),
            decision_id=data.get("decision_id"),
            timestamp=data.get("timestamp", datetime.now()),
        )

    def to_dict(self) -> dict:
        """Trade 객체를 딕셔너리로 변환합니다."""
        return {
            "trade_id": self.trade_id,
            "market": self.market,
            "side": self.side,
            "volume": self.volume,
            "price": self.price,
            "strategy_id": self.strategy_id,
            "order_uuid": self.order_uuid,
            "fee": self.fee,
            "fee_asset": self.fee_asset,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp,
        }

    @property
    def value(self) -> Decimal:
        """체결 총액 (체결 단가 X 체결 수량)."""
        return self.volume * self.price

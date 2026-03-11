from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..utils.constants import SignalDirection
from .base import Base
from .signal import Signal


@dataclass
class TradeCandidate(Base):
    """
    여러 시그널을 종합하여 생성된 거래 후보(TradeCandidate) 모델

    Attributes:
        market (str): 대상 마켓 코드 (예: KRW-BTC)
        direction (SignalDirection): 거래 방향 (LONG, SHORT, CLOSE, HOLD)
        contributing_signals (list[Signal]): 이 후보를 생성하는 데 기여한 시그널 목록
        suggested_entry (Decimal): 제안 진입 가격
        suggested_stop_loss (Decimal): 제안 손절 가격
        suggested_take_profit (Decimal): 제안 익절 가격
        timestamp (datetime): 거래 후보 생성 시각
    """

    market: str
    direction: SignalDirection
    contributing_signals: list[Signal]
    suggested_entry: Decimal
    suggested_stop_loss: Decimal
    suggested_take_profit: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.direction, str):
            self.direction = SignalDirection(self.direction)

        for field_name in ["suggested_entry", "suggested_stop_loss", "suggested_take_profit"]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

        self.contributing_signals = [
            Signal.from_dict(s) if isinstance(s, dict) else s for s in self.contributing_signals
        ]

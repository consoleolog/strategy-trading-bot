from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..util.constants import SignalDirection
from .signal import Signal


@dataclass
class TradeCandidate:
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

    @classmethod
    def from_dict(cls, data: dict) -> "TradeCandidate":
        """딕셔너리 데이터를 TradeCandidate 객체로 변환합니다."""
        return cls(
            market=data.get("market"),
            direction=data.get("direction"),
            contributing_signals=data.get("contributing_signals", []),
            suggested_entry=data.get("suggested_entry"),
            suggested_stop_loss=data.get("suggested_stop_loss"),
            suggested_take_profit=data.get("suggested_take_profit"),
            timestamp=data.get("timestamp", datetime.now()),
        )

    def to_dict(self) -> dict:
        """TradeCandidate 객체를 딕셔너리로 변환합니다."""
        return {
            "market": self.market,
            "direction": self.direction,
            "contributing_signals": [s.to_dict() for s in self.contributing_signals],
            "suggested_entry": self.suggested_entry,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "timestamp": self.timestamp,
        }

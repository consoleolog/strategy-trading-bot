from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from ..utils.constants import DecisionState, SignalDirection
from .signal import Signal


@dataclass
class Decision:
    """
    전략 실행 결정(Decision) 모델

    Attributes:
        decision_id (UUID): 결정의 고유 식별자
        market (str): 대상 마켓 코드 (예: KRW-BTC)
        direction (SignalDirection): 거래 방향 (LONG, SHORT, CLOSE, HOLD)
        volume (Decimal): 주문 수량
        entry_price (Decimal): 진입 가격
        stop_loss (Decimal): 손절 가격
        take_profit (Decimal): 익절 가격
        risk_amount (Decimal): 리스크 금액 (손절 시 손실 예상액)
        risk_percent (float): 계좌 대비 리스크 비율 (기본값: 0.0)
        contributing_signals (list[Signal]): 결정 생성에 기여한 시그널 목록
        state (DecisionState): 결정 상태 (PENDING, APPROVED, REJECTED, EXECUTED, CANCELLED)
    """

    decision_id: UUID
    market: str
    direction: SignalDirection
    volume: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    risk_amount: Decimal
    risk_percent: float = 0.0
    contributing_signals: list[Signal] = field(default_factory=list)
    state: DecisionState = DecisionState.PENDING

    def __post_init__(self):
        if isinstance(self.decision_id, str):
            self.decision_id = UUID(self.decision_id)

        if isinstance(self.direction, str):
            self.direction = SignalDirection(self.direction)

        for field_name in ["volume", "entry_price", "stop_loss", "take_profit", "risk_amount"]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.state, str):
            self.state = DecisionState(self.state)

        self.contributing_signals = [
            Signal.from_dict(s) if isinstance(s, dict) else s for s in self.contributing_signals
        ]

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        """딕셔너리 데이터를 Decision 객체로 변환합니다."""
        return cls(
            decision_id=data.get("decision_id", uuid4()),
            market=data.get("market"),
            direction=data.get("direction"),
            volume=data.get("volume"),
            entry_price=data.get("entry_price"),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            risk_amount=data.get("risk_amount"),
            risk_percent=data.get("risk_percent", 0.0),
            contributing_signals=data.get("contributing_signals", []),
            state=data.get("state", DecisionState.PENDING),
        )

    def to_dict(self) -> dict:
        """Decision 객체를 딕셔너리로 변환합니다."""
        return {
            "decision_id": self.decision_id,
            "market": self.market,
            "direction": self.direction,
            "volume": self.volume,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_amount": self.risk_amount,
            "risk_percent": self.risk_percent,
            "contributing_signals": [s.to_dict() for s in self.contributing_signals],
            "state": self.state,
        }

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

from ..utils.constants import DecisionState, SignalDirection
from .base import Base
from .signal import Signal


@dataclass
class Decision(Base):
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
    decision_id: UUID = field(default_factory=uuid4)

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

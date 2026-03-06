from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .constants import ExecutionState


@dataclass
class ExecutionResult:
    """
    주문 실행 결과 모델

    Attributes:
        success (bool): 실행 성공 여부
        decision_id (UUID): 이 실행을 발생시킨 Decision의 식별자
        order_uuid (UUID): 거래소에 제출된 주문의 UUID
        filled_quantity (Decimal): 실제 체결된 수량
        average_price (Decimal): 평균 체결 단가
        fee (Decimal): 체결 수수료
        fee_asset (str): 수수료 자산 종류 (기본값: KRW)
        state (ExecutionState): 체결 상태 (FILLED, PARTIALLY_FILLED, PENDING 등)
        error_message (str | None): 실행 실패 시 오류 메시지 (없으면 None)
        timestamp (datetime): 실행 결과 기록 시각
    """

    success: bool
    decision_id: UUID
    order_uuid: UUID
    filled_quantity: Decimal
    average_price: Decimal
    fee: Decimal
    fee_asset: str = "KRW"
    state: ExecutionState = ExecutionState.PENDING
    error_message: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if isinstance(self.decision_id, str):
            self.decision_id = UUID(self.decision_id)
        if isinstance(self.order_uuid, str):
            self.order_uuid = UUID(self.order_uuid)

        for field_name in ["filled_quantity", "average_price", "fee"]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.state, str):
            self.state = ExecutionState(self.state)

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionResult":
        """딕셔너리 데이터를 ExecutionResult 객체로 변환합니다."""
        return cls(
            success=data.get("success"),
            decision_id=data.get("decision_id"),
            order_uuid=data.get("order_uuid"),
            filled_quantity=data.get("filled_quantity"),
            average_price=data.get("average_price"),
            fee=data.get("fee"),
            fee_asset=data.get("fee_asset", "KRW"),
            state=data.get("state", ExecutionState.PENDING),
            error_message=data.get("error_message"),
            timestamp=data.get("timestamp", datetime.now()),
        )

    def to_dict(self) -> dict:
        """ExecutionResult 객체를 딕셔너리로 변환합니다."""
        return {
            "success": self.success,
            "decision_id": self.decision_id,
            "order_uuid": self.order_uuid,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "fee": self.fee,
            "fee_asset": self.fee_asset,
            "state": self.state,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }

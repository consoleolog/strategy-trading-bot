from dataclasses import dataclass

from ..utils.constants import RiskSeverity


@dataclass(frozen=True)
class TriggeredRule:
    """리스크 엔진에서 발화(triggered)된 단일 규칙의 평가 결과.

    Attributes:
        rule_name: 발화된 규칙 식별자 (예: ``max_drawdown``, ``daily_loss_limit``).
        severity: 규칙의 심각도. ``INFO`` | ``WARNING`` | ``CRITICAL`` | ``EMERGENCY``
        message: 규칙이 발화된 사유를 설명하는 메시지.
        suggested_action: 권장 조치 (선택). 없으면 ``None``.
    """

    rule_name: str
    severity: RiskSeverity
    message: str
    suggested_action: str | None = None

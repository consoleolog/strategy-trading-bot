from dataclasses import dataclass, field
from datetime import datetime

from ..utils.constants import RiskDecision, RiskSeverity
from .triggered_rule import TriggeredRule


@dataclass(frozen=True)
class RiskRecord:
    """리스크 엔진의 단일 평가 결과 레코드.

    의사결정(Decision) 하나에 대해 모든 리스크 규칙을 평가한 뒤 생성된다.
    감사(audit) 및 이력 추적 목적으로 저장된다.

    Attributes:
        input_decision_id: 평가 대상 Decision의 식별자.
        risk_decision: 최종 리스크 판정. ``ALLOW`` | ``REDUCE_SIZE`` | ``FORCE_NO_ACTION`` | ``EMERGENCY_STOP``
        reason: 최종 판정 사유 요약 메시지.
        timestamp: 평가 시각.
        triggered_rules: 발화된 규칙 목록. 없으면 빈 리스트.
        recommended_action: 판정이 ``ALLOW`` 가 아닐 때 권장 조치 (선택).
        max_allowed_size_krw: ``REDUCE_SIZE`` 판정 시 허용되는 최대 주문 금액 (KRW, 선택).
        config_reference: 평가에 사용된 설정값 스냅샷. 감사 추적용 (규칙명 → 설정값).
    """

    input_decision_id: str
    risk_decision: RiskDecision
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)

    # 발화된 규칙 목록
    triggered_rules: list[TriggeredRule] = field(default_factory=list)

    # ALLOW 가 아닐 때 권장 조치
    recommended_action: str | None = None

    # REDUCE_SIZE 판정 시 허용 최대 주문 금액 (KRW)
    max_allowed_size_krw: float | None = None

    # 감사 추적용 설정 스냅샷 (규칙명 → 설정값)
    config_reference: dict[str, str] = field(default_factory=dict)

    @property
    def is_blocked(self) -> bool:
        """거래가 차단된 판정인지 여부."""
        return self.risk_decision in (
            RiskDecision.FORCE_NO_ACTION,
            RiskDecision.EMERGENCY_STOP,
        )

    @property
    def highest_severity(self) -> RiskSeverity | None:
        """발화된 규칙 중 가장 높은 심각도. 발화된 규칙이 없으면 ``None``."""
        if not self.triggered_rules:
            return None
        severity_order = [
            RiskSeverity.INFO,
            RiskSeverity.WARNING,
            RiskSeverity.CRITICAL,
            RiskSeverity.EMERGENCY,
        ]
        return max(self.triggered_rules, key=lambda r: severity_order.index(r.severity)).severity

from decimal import Decimal

from ..models import RiskContext, RiskRecord, TriggeredRule
from ..utils.constants import RiskDecision, RiskSeverity
from .risk_rule import RiskRule


class RiskEngine:
    """등록된 리스크 규칙을 순서대로 평가하여 최종 리스크 결정을 반환하는 엔진.

    규칙은 :attr:`~risk_rule.RiskRule.priority` 오름차순으로 평가되며,
    발화된 규칙들의 심각도를 집계하여 ``ALLOW`` · ``REDUCE_SIZE`` ·
    ``FORCE_NO_ACTION`` · ``EMERGENCY_STOP`` 중 하나를 결정한다.

    Attributes:
        rules (list[RiskRule]): priority 오름차순으로 정렬된 리스크 규칙 목록.
    """

    def __init__(self, rules: list[RiskRule]):
        """RiskEngine을 초기화한다.

        Args:
            rules: 평가할 리스크 규칙 목록. 내부적으로 priority 오름차순 정렬된다.
        """
        # priority 오름차순 정렬 — 긴급 규칙이 항상 먼저 평가됨
        self.rules = sorted(rules, key=lambda r: r.priority)

    def evaluate(self, context: RiskContext, decision_id: str) -> RiskRecord:
        """모든 리스크 규칙을 평가하고 최종 리스크 판정 결과를 반환한다.

        각 규칙을 순서대로 실행하여 발화된 규칙을 수집한 뒤,
        심각도 집계를 통해 최종 결정을 산출한다.
        ``REDUCE_SIZE`` 결정인 경우 허용 가능한 최대 주문 크기도 함께 계산한다.

        Args:
            context: 규칙 평가에 필요한 포트폴리오·시장 상태 스냅샷.
            decision_id: 이 평가와 연결된 거래 결정의 고유 식별자.

        Returns:
            리스크 판정 결과를 담은 :class:`~models.RiskRecord` 객체.
        """
        triggered_rules: list[TriggeredRule] = []

        # 모든 규칙을 순서대로 실행하고 위반된 규칙만 수집
        for rule in self.rules:
            result = rule.evaluate(context)
            if result is not None:
                triggered_rules.append(result)

        aggregated_decision = self._aggregate_decision(triggered_rules)
        risk_decision = aggregated_decision["decision"]
        reason = aggregated_decision["reason"]
        recommended_action = aggregated_decision["recommended_action"]

        # REDUCE_SIZE 결정일 때만 허용 가능한 최대 주문 크기를 계산
        max_allowed_size = None
        if risk_decision == RiskDecision.REDUCE_SIZE:
            max_allowed_size = self._calculate_max_size(context)

        return RiskRecord(
            input_decision_id=decision_id,
            risk_decision=risk_decision,
            reason=reason,
            triggered_rules=triggered_rules,
            recommended_action=recommended_action,
            max_allowed_size_krw=max_allowed_size,
        )

    @staticmethod
    def _aggregate_decision(triggered_rules: list[TriggeredRule]) -> dict:
        """발화된 규칙 목록을 심각도 우선순위에 따라 집계하여 최종 결정을 반환한다.

        심각도 판정 우선순위: ``EMERGENCY`` > ``CRITICAL`` > ``WARNING`` > 기본(ALLOW).
        규칙이 하나도 발화되지 않으면 ``ALLOW`` 를 반환한다.

        Args:
            triggered_rules: 평가 중 발화된 :class:`~models.TriggeredRule` 목록.

        Returns:
            ``decision``, ``reason``, ``recommended_action`` 키를 갖는 딕셔너리.
        """
        # 발화된 규칙이 없으면 모든 규칙 통과 — 거래 허용
        if not triggered_rules:
            return {
                "decision": RiskDecision.ALLOW,
                "reason": "All risk rules passed",
                "recommended_action": None,
            }

        # 이후 로직에서 triggered_rules[0] 접근이 안전함이 보장됨
        return_dictionary = {
            "decision": RiskDecision.ALLOW,
            "reason": f"Info: {triggered_rules[0].message}",
            "recommended_action": None,
        }

        # EMERGENCY 규칙 발화 여부 확인 — 즉시 전체 청산
        emergencies = [r for r in triggered_rules if r.severity == RiskSeverity.EMERGENCY]
        if emergencies:
            return_dictionary["decision"] = RiskDecision.EMERGENCY_STOP
            return_dictionary["reason"] = f"Emergency: {emergencies[0].message}"
            return_dictionary["recommended_action"] = "Flatten all positions immediately"
            return return_dictionary

        # CRITICAL 규칙 발화 여부 확인 — 신규 거래 차단
        criticals = [r for r in triggered_rules if r.severity == RiskSeverity.CRITICAL]
        if criticals:
            return_dictionary["decision"] = RiskDecision.FORCE_NO_ACTION
            return_dictionary["reason"] = f"Blocked: {criticals[0].message}"
            return_dictionary["recommended_action"] = criticals[0].suggested_action
            return return_dictionary

        # WARNING 규칙 발화 여부 확인 — 포지션 크기 축소 (거래 차단 아님)
        warnings = [r for r in triggered_rules if r.severity == RiskSeverity.WARNING]
        if warnings:
            return_dictionary["decision"] = RiskDecision.REDUCE_SIZE
            return_dictionary["reason"] = f"Warning: {warnings[0].message}"
            return_dictionary["recommended_action"] = warnings[0].suggested_action
            return return_dictionary

        return return_dictionary

    @staticmethod
    def _calculate_max_size(context: RiskContext) -> float:
        """REDUCE_SIZE 결정 시 허용 가능한 최대 주문 금액(KRW)을 계산한다.

        포트폴리오 가치의 2%를 기본 상한으로 설정하며,
        낙폭이 10%를 초과하는 경우 상한을 절반으로 추가 축소한다.

        Args:
            context: 포트폴리오 가치와 낙폭 정보가 담긴 리스크 컨텍스트.

        Returns:
            허용 가능한 최대 주문 금액 (KRW, float).
        """
        # 기본 상한: 포트폴리오 가치의 2%
        base_max = float(context.portfolio_value_krw) * 0.02

        # 낙폭 10% 초과 시 추가 보수적 조치 — 상한을 절반으로 축소
        if context.current_drawdown_percent > Decimal("10"):
            base_max *= 0.5

        return base_max

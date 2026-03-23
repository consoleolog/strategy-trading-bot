from decimal import Decimal

from ...models import RiskContext, TriggeredRule
from ...utils.constants import RiskSeverity
from ..risk_rule import RiskRule


class MaxDrawdownRule(RiskRule):
    """고점 대비 낙폭(drawdown)이 임계값을 초과하는지 검사하는 리스크 규칙.

    ``current_drawdown_percent`` 를 기준으로 세 단계로 판정한다:

    - ``warning_threshold`` 이상  → ``WARNING``   (포지션 크기 50% 축소 권고)
    - ``critical_threshold`` 이상 → ``CRITICAL``  (신규 거래 차단)
    - ``emergency_threshold`` 이상 → ``EMERGENCY`` (전체 포지션 즉시 청산)

    Attributes:
        priority (int): 평가 우선순위 ``10`` (가장 먼저 평가되는 긴급 등급).
        default_severity (RiskSeverity): 기본 심각도 ``CRITICAL``.
        warning_threshold (Decimal): 경고 발화 기준 낙폭 (%). 기본값 ``10``.
        critical_threshold (Decimal): 위험 발화 기준 낙폭 (%). 기본값 ``15``.
        emergency_threshold (Decimal): 비상 발화 기준 낙폭 (%). 기본값 ``20``.
    """

    priority = 10
    default_severity = RiskSeverity.CRITICAL

    def __init__(
        self,
        warning_threshold: Decimal = Decimal("10"),
        critical_threshold: Decimal = Decimal("15"),
        emergency_threshold: Decimal = Decimal("20"),
    ):
        """MaxDrawdownRule 을 초기화한다.

        Args:
            warning_threshold: WARNING 을 발화할 낙폭 하한 (%). 기본값 ``10``.
            critical_threshold: CRITICAL 을 발화할 낙폭 하한 (%). 기본값 ``15``.
            emergency_threshold: EMERGENCY 를 발화할 낙폭 하한 (%). 기본값 ``20``.
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.emergency_threshold = emergency_threshold

    @property
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        return "MaxDrawdownRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """현재 낙폭을 확인하여 임계값 초과 시 TriggeredRule 을 반환한다.

        emergency → critical → warning 순으로 높은 심각도를 먼저 비교하여
        가장 엄격한 판정을 우선 반환한다.

        Args:
            context: 현재 낙폭(``current_drawdown_percent``)을 포함한 리스크 컨텍스트.

        Returns:
            - ``dd >= emergency_threshold`` 이면 ``EMERGENCY`` TriggeredRule
            - ``dd >= critical_threshold``  이면 ``CRITICAL``  TriggeredRule
            - ``dd >= warning_threshold``   이면 ``WARNING``   TriggeredRule
            - 임계값 미달 시 ``None``
        """
        # 고점 대비 현재 낙폭 (%)
        dd = context.current_drawdown_percent

        # emergency 임계값 초과 — 전체 포지션 즉시 청산
        if dd >= self.emergency_threshold:
            return self._create_triggered(
                f"EMERGENCY: Drawdown {dd:.1f}% exceeds {self.emergency_threshold}%",
                severity=RiskSeverity.EMERGENCY,
                suggested_action="Flatten all positions, pause trading, manual review required",
            )

        # critical 임계값 초과 — 신규 거래 차단
        if dd >= self.critical_threshold:
            return self._create_triggered(
                f"Drawdown {dd:.1f}% exceeds {self.critical_threshold}%",
                severity=RiskSeverity.CRITICAL,
                suggested_action="No new trades until drawdown reduces",
            )

        # warning 임계값 초과 — 포지션 크기 50% 축소 권고
        if dd >= self.warning_threshold:
            return self._create_triggered(
                f"Drawdown {dd:.1f}% approaching limit",
                severity=RiskSeverity.WARNING,
                suggested_action="Reduce position sizes by 50%",
            )

        return None

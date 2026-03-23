from decimal import Decimal

from ...models import RiskContext, TriggeredRule
from ...utils.constants import RiskSeverity
from ..risk_rule import RiskRule


class DailyLossLimitRule(RiskRule):
    """당일 손실률이 임계값을 초과하는지 검사하는 리스크 규칙.

    ``daily_pnl_percent`` 를 기준으로 두 단계로 판정한다:

    - ``warning_threshold`` 이상 → ``WARNING`` (포지션 크기 축소 권고)
    - ``critical_threshold`` 이상 → ``CRITICAL`` (신규 거래 차단)

    Attributes:
        priority (int): 평가 우선순위 ``20`` (비상 등급에 준하는 높은 우선순위).
        default_severity (RiskSeverity): 기본 심각도 ``CRITICAL``.
        warning_threshold (Decimal): 경고 발화 기준 당일 손실률 (%). 기본값 ``3``.
        critical_threshold (Decimal): 위험 발화 기준 당일 손실률 (%). 기본값 ``5``.
    """

    priority = 20
    default_severity = RiskSeverity.CRITICAL

    def __init__(
        self,
        warning_threshold: Decimal = Decimal("3"),
        critical_threshold: Decimal = Decimal("5"),
    ):
        """DailyLossLimitRule 을 초기화한다.

        Args:
            warning_threshold: WARNING 을 발화할 당일 손실률 하한 (%). 기본값 ``3``.
            critical_threshold: CRITICAL 을 발화할 당일 손실률 하한 (%). 기본값 ``5``.
        """
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    @property
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        return "DailyLossLimitRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """당일 손실률을 확인하여 임계값 초과 시 TriggeredRule 을 반환한다.

        ``daily_pnl_percent`` 에 부호를 반전하여 손실 크기(양수)로 변환한 뒤
        임계값과 비교한다. critical 임계값을 먼저 비교하여 더 높은 심각도를 우선 반환한다.

        Args:
            context: 당일 손익률(``daily_pnl_percent``)을 포함한 리스크 컨텍스트.

        Returns:
            - ``daily_loss >= critical_threshold`` 이면 ``CRITICAL`` TriggeredRule
            - ``daily_loss >= warning_threshold`` 이면 ``WARNING`` TriggeredRule
            - 임계값 미달 시 ``None``
        """
        # daily_pnl_percent 는 손실 시 음수이므로 부호를 반전하여 손실 크기를 양수로 변환
        daily_loss = -context.daily_pnl_percent

        # critical 임계값 초과 — 신규 거래 차단
        if daily_loss >= self.critical_threshold:
            return self._create_triggered(
                f"Daily loss {daily_loss:.2f}% exceeds {self.critical_threshold}%",
                severity=RiskSeverity.CRITICAL,
                suggested_action="Pause trading until next day, no new positions",
            )

        # warning 임계값 초과 — 포지션 크기 축소 권고
        if daily_loss >= self.warning_threshold:
            return self._create_triggered(
                f"Daily loss {daily_loss:.2f}% approaching limit",
                severity=RiskSeverity.WARNING,
                suggested_action="Reduce position sizes, consider pausing",
            )

        return None

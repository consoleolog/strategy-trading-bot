from decimal import Decimal

from ...models import RiskContext, TriggeredRule
from ...utils.constants import RiskSeverity
from ..risk_rule import RiskRule


class PortfolioExposureRule(RiskRule):
    """포트폴리오 대비 포지션 비중(노출도)이 허용 상한을 초과하는지 검사하는 리스크 규칙.

    ``position_utilization_percent`` 를 기준으로 세 단계로 판정한다:

    - ``warning_threshold`` 이상  → ``WARNING``  (신규 포지션 진입 주의 권고)
    - ``max_exposure`` 이상       → ``CRITICAL`` (노출도 최대치 도달, 신규 포지션 금지)
    - ``critical_exposure`` 이상  → ``CRITICAL`` (노출도 위험 수준, 포지션 축소 필요)

    Attributes:
        priority (int): 평가 우선순위 ``105`` (위험 등급 초입).
        default_severity (RiskSeverity): 기본 심각도 ``WARNING``.
        warning_threshold (Decimal): 경고 발화 기준 노출도 (%). 기본값 ``30``.
        max_exposure (Decimal): 최대 허용 노출도 (%). 기본값 ``40``.
        critical_exposure (Decimal): 위험 수준 노출도 (%). 기본값 ``60``.
    """

    priority = 105
    default_severity = RiskSeverity.WARNING

    def __init__(
        self,
        warning_threshold: Decimal = Decimal("30"),
        max_exposure: Decimal = Decimal("40"),
        critical_exposure: Decimal = Decimal("60"),
    ):
        """PortfolioExposureRule 을 초기화한다.

        Args:
            warning_threshold: WARNING 을 발화할 노출도 하한 (%). 기본값 ``30``.
            max_exposure: CRITICAL(최대 허용) 을 발화할 노출도 하한 (%). 기본값 ``40``.
            critical_exposure: CRITICAL(위험 수준) 을 발화할 노출도 하한 (%). 기본값 ``60``.
        """
        self.warning_threshold = warning_threshold
        self.max_exposure = max_exposure
        self.critical_exposure = critical_exposure

    @property
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        return "PortfolioExposureRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """현재 포트폴리오 노출도를 확인하여 임계값 초과 시 TriggeredRule 을 반환한다.

        critical_exposure → max_exposure → warning_threshold 순으로 높은 심각도를 먼저
        비교하여 가장 엄격한 판정을 우선 반환한다.

        Args:
            context: 포지션 비중(``position_utilization_percent``)을 포함한 리스크 컨텍스트.

        Returns:
            - ``exposure >= critical_exposure`` 이면 ``CRITICAL`` TriggeredRule (위험 수준)
            - ``exposure >= max_exposure``      이면 ``CRITICAL`` TriggeredRule (최대치 도달)
            - ``exposure >= warning_threshold`` 이면 ``WARNING``  TriggeredRule
            - 임계값 미달 시 ``None``
        """
        # 포트폴리오 대비 현재 포지션 노출도 (%)
        exposure = context.position_utilization_percent

        # 위험 수준 노출도 초과 — 기존 포지션 축소 필요
        if exposure >= self.critical_exposure:
            return self._create_triggered(
                f"Portfolio exposure {exposure:.1f}% critically high",
                severity=RiskSeverity.CRITICAL,
                suggested_action="Reduce positions, no new trades",
            )

        # 최대 허용 노출도 도달 — 신규 포지션 금지
        if exposure >= self.max_exposure:
            return self._create_triggered(
                f"Portfolio exposure {exposure:.1f}% at maximum",
                severity=RiskSeverity.CRITICAL,
                suggested_action="No new positions until exposure reduces",
            )

        # 경고 임계값 초과 — 신규 포지션 진입 주의 권고
        if exposure >= self.warning_threshold:
            return self._create_triggered(
                f"Portfolio exposure {exposure:.1f}% approaching limit",
                severity=RiskSeverity.WARNING,
                suggested_action="Be cautious with new positions",
            )

        return None

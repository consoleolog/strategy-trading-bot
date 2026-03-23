from decimal import Decimal

from ...models import RiskContext, TriggeredRule
from ...utils.constants import RiskSeverity
from ..risk_rule import RiskRule


class PositionSizeRule(RiskRule):
    """개별 거래의 리스크 비율이 허용 상한을 초과하는지 검사하는 리스크 규칙.

    ``proposed_trade_risk_percent`` 를 기준으로 세 단계로 판정한다:

    - ``warning_threshold`` 이상   → ``INFO``     (포지션 모니터링 강화 권고)
    - ``max_risk_percent`` 이상    → ``WARNING``  (권장 리스크 한도 초과)
    - ``hard_limit_percent`` 이상  → ``CRITICAL`` (하드 리스크 한도 초과, 거래 차단)

    Attributes:
        priority (int): 평가 우선순위 ``100`` (위험 등급 진입점).
        default_severity (RiskSeverity): 기본 심각도 ``CRITICAL``.
        max_risk_percent (Decimal): 권장 최대 리스크 비율 (%). 기본값 ``2``.
        warning_threshold (Decimal): INFO 발화 기준 리스크 비율 (%). 기본값 ``1.5``.
        hard_limit_percent (Decimal): CRITICAL 발화 기준 하드 한도 (%). 기본값 ``3``.
    """

    priority = 100
    default_severity = RiskSeverity.CRITICAL

    def __init__(
        self,
        max_risk_percent: Decimal = Decimal("2"),
        warning_threshold: Decimal = Decimal("1.5"),
        hard_limit_percent: Decimal = Decimal("3"),
    ):
        """PositionSizeRule 을 초기화한다.

        Args:
            max_risk_percent: WARNING 을 발화할 권장 리스크 비율 상한 (%). 기본값 ``2``.
            warning_threshold: INFO 를 발화할 리스크 비율 하한 (%). 기본값 ``1.5``.
            hard_limit_percent: CRITICAL 을 발화할 하드 한도 (%). 기본값 ``3``.
        """
        self.max_risk_percent = max_risk_percent
        self.warning_threshold = warning_threshold
        self.hard_limit_percent = hard_limit_percent

    @property
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        return "PositionSizeRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """검토 중인 거래의 리스크 비율을 확인하여 임계값 초과 시 TriggeredRule 을 반환한다.

        ``proposed_trade_risk_percent`` 가 None 이면 포지션 사이징 평가 대상이 아니므로
        즉시 None 을 반환한다. 설정된 경우 hard_limit → max_risk → warning 순으로
        높은 심각도를 먼저 비교하여 가장 엄격한 판정을 우선 반환한다.

        Args:
            context: 검토 중인 거래의 리스크 비율(``proposed_trade_risk_percent``)을
                포함한 리스크 컨텍스트.

        Returns:
            - ``proposed_trade_risk_percent`` 가 None 이면 ``None``
            - ``risk >= hard_limit_percent``  이면 ``CRITICAL`` TriggeredRule
            - ``risk >= max_risk_percent``    이면 ``WARNING``  TriggeredRule
            - ``risk >= warning_threshold``   이면 ``INFO``     TriggeredRule
            - 임계값 미달 시 ``None``
        """
        # 포지션 사이징 컨텍스트가 없으면 평가 대상 아님
        if context.proposed_trade_risk_percent is None:
            return None

        # 검토 중인 거래의 예상 리스크 비율 (%)
        risk = context.proposed_trade_risk_percent

        # 하드 한도 초과 — 거래 차단
        if risk >= self.hard_limit_percent:
            return self._create_triggered(
                f"Trade risk {risk:.2f}% exceeds hard limit {self.hard_limit_percent}%",
                severity=RiskSeverity.CRITICAL,
                suggested_action=f"Reduce position size to max {self.max_risk_percent}% risk",
            )

        # 권장 리스크 한도 초과 — 포지션 크기 축소 권고
        if risk >= self.max_risk_percent:
            return self._create_triggered(
                f"Trade risk {risk:.2f}% exceeds recommended {self.max_risk_percent}%",
                severity=RiskSeverity.WARNING,
                suggested_action=f"Consider reducing to {self.max_risk_percent}% risk",
            )

        # 경고 임계값 초과 — 포지션 모니터링 강화 권고
        if risk >= self.warning_threshold:
            return self._create_triggered(
                f"Trade risk {risk:.2f}% approaching limit",
                severity=RiskSeverity.INFO,
                suggested_action="Monitor position closely",
            )

        return None

from ...models import RiskContext, TriggeredRule
from ...utils.constants import RiskSeverity
from ..risk_rule import RiskRule


class MaxPositionsRule(RiskRule):
    """동시 보유 포지션 수가 허용 상한을 초과하는지 검사하는 리스크 규칙.

    ``open_positions_count`` 를 기준으로 두 단계로 판정한다:

    - ``max_positions - 1`` 이상 → ``INFO``     (신규 거래 전 포지션 수 재확인 권고)
    - ``max_positions`` 이상      → ``CRITICAL`` (신규 포지션 개설 차단)

    Attributes:
        priority (int): 평가 우선순위 ``110`` (위험 등급 초입).
        default_severity (RiskSeverity): 기본 심각도 ``WARNING``.
        max_positions (int): 동시 보유 허용 최대 포지션 수. 기본값 ``5``.
    """

    priority = 110
    default_severity = RiskSeverity.WARNING

    def __init__(self, max_positions: int = 5):
        """MaxPositionsRule 을 초기화한다.

        Args:
            max_positions: 동시 보유 허용 최대 포지션 수. 기본값 ``5``.
        """
        self.max_positions = max_positions

    @property
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        return "MaxPositionsRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """현재 보유 포지션 수를 확인하여 상한 초과 시 TriggeredRule 을 반환한다.

        상한 도달 여부를 먼저 확인하여 ``CRITICAL`` 을 우선 반환하고,
        상한 직전(``max_positions - 1``)에는 ``INFO`` 로 사전 경고한다.

        Args:
            context: 현재 보유 포지션 수(``open_positions_count``)를 포함한 리스크 컨텍스트.

        Returns:
            - ``open_positions_count >= max_positions``     이면 ``CRITICAL`` TriggeredRule
            - ``open_positions_count >= max_positions - 1`` 이면 ``INFO``     TriggeredRule
            - 상한 미달 시 ``None``
        """
        # 최대 포지션 수 도달 — 신규 포지션 개설 차단
        if context.open_positions_count >= self.max_positions:
            return self._create_triggered(
                f"Max positions ({self.max_positions}) reached",
                severity=RiskSeverity.CRITICAL,
                suggested_action="Close existing position before opening new one",
            )

        # 최대 포지션 수 직전 — 신규 거래 전 포지션 수 재확인 권고
        if context.open_positions_count >= self.max_positions - 1:
            return self._create_triggered(
                f"Approaching max positions ({context.open_positions_count}/{self.max_positions})",
                severity=RiskSeverity.INFO,
                suggested_action="Consider position count before new trades",
            )

        return None

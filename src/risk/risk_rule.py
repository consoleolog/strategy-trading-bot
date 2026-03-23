from abc import ABC, abstractmethod

from ..models import RiskContext, TriggeredRule
from ..utils.constants import RiskSeverity


class RiskRule(ABC):
    """리스크 규칙의 추상 기반 클래스.

    모든 리스크 규칙은 이 클래스를 상속하여 :attr:`name` 과 :meth:`evaluate` 를 구현해야 한다.
    규칙은 :attr:`priority` 값이 낮을수록 먼저 평가된다.

    우선순위 범위::

        0  ~ 99  : 비상(Emergency) 규칙
        100 ~ 199: 위험(Critical)  규칙
        200 ~ 299: 경고(Warning)   규칙
        300+     : 정보(Info)      규칙

    Attributes:
        priority (int): 평가 순서 (낮을수록 먼저 평가). 기본값 ``200`` (경고 등급).
        default_severity (RiskSeverity): 규칙 위반 시 기본 심각도. 기본값 ``WARNING``.
    """

    # 평가 순서를 결정하는 우선순위 (낮을수록 먼저 평가됨)
    # 0~99: 비상, 100~199: 위험, 200~299: 경고, 300+: 정보
    priority: int = 200

    default_severity: RiskSeverity = RiskSeverity.WARNING

    @property
    @abstractmethod
    def name(self) -> str:
        """규칙의 고유 식별 이름."""
        raise NotImplementedError()

    @abstractmethod
    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """리스크 조건을 평가하여 위반 시 TriggeredRule 을 반환한다.

        Args:
            context: 평가에 필요한 포트폴리오·시장 상태 정보.

        Returns:
            규칙이 위반된 경우 :class:`~models.TriggeredRule` 객체,
            위반되지 않은 경우 ``None``.
        """
        raise NotImplementedError()

    def _create_triggered(
        self,
        message: str,
        severity: RiskSeverity | None = None,
        suggested_action: str | None = None,
    ) -> TriggeredRule:
        """위반 규칙 객체(TriggeredRule)를 생성하는 편의 메서드.

        서브클래스의 ``evaluate()`` 구현에서 호출하여 일관된 형식의
        :class:`~models.TriggeredRule` 을 반환할 때 사용한다.

        Args:
            message: 규칙 위반 내용을 설명하는 메시지.
            severity: 이번 위반의 심각도. ``None`` 이면 ``default_severity`` 를 사용.
            suggested_action: 위반 시 권장 조치 설명 (선택).

        Returns:
            생성된 :class:`~models.TriggeredRule` 객체.
        """
        return TriggeredRule(
            rule_name=self.name,
            severity=severity or self.default_severity,
            message=message,
            suggested_action=suggested_action,
        )


class CompositeRiskRule(RiskRule):
    """여러 하위 규칙을 하나로 묶어 순서대로 평가하는 복합 규칙.

    관련된 규칙들을 그룹으로 관리할 때 유용하다.
    하위 규칙은 :attr:`priority` 오름차순으로 정렬되어 평가되며,
    첫 번째로 위반이 감지된 규칙의 결과만 반환한다.

    Attributes:
        rules (list[RiskRule]): priority 오름차순으로 정렬된 하위 규칙 목록.
    """

    def __init__(self, rules: list[RiskRule]):
        """CompositeRiskRule 을 초기화한다.

        Args:
            rules: 묶을 하위 규칙 목록. 내부적으로 priority 오름차순 정렬된다.
        """
        # priority 오름차순 정렬 — 긴급 규칙이 항상 먼저 평가됨
        self.rules = sorted(rules, key=lambda r: r.priority)

    @property
    def name(self) -> str:
        """복합 규칙의 고유 이름."""
        return "CompositeRule"

    def evaluate(self, context: RiskContext) -> TriggeredRule | None:
        """모든 하위 규칙을 순서대로 평가하고, 첫 번째 위반 결과를 반환한다.

        Args:
            context: 평가에 필요한 포트폴리오·시장 상태 정보.

        Returns:
            첫 번째로 위반된 하위 규칙의 :class:`~models.TriggeredRule`,
            모든 규칙을 통과하면 ``None``.
        """
        for rule in self.rules:
            result = rule.evaluate(context)
            if result is not None:
                return result
        return None

"""RiskRule / CompositeRiskRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.models.risk_context import RiskContext
from src.models.triggered_rule import TriggeredRule
from src.risk.risk_rule import CompositeRiskRule, RiskRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context() -> RiskContext:
    """테스트용 최소 RiskContext 생성."""
    return RiskContext(
        system_state="RUNNING",
        mode="DRY_RUN",
        open_positions_count=0,
        total_position_value_krw=Decimal("0"),
        portfolio_value_krw=Decimal("10000000"),
        starting_capital_krw=Decimal("10000000"),
        daily_pnl_krw=Decimal("0"),
        daily_pnl_percent=Decimal("0"),
        weekly_pnl_krw=Decimal("0"),
        weekly_pnl_percent=Decimal("0"),
        peak_portfolio_value_krw=Decimal("10000000"),
        current_drawdown_percent=Decimal("0"),
    )


def make_triggered(
    rule_name: str = "test_rule",
    severity: RiskSeverity = RiskSeverity.WARNING,
    message: str = "위반 발생",
) -> TriggeredRule:
    """테스트용 TriggeredRule 생성."""
    return TriggeredRule(rule_name=rule_name, severity=severity, message=message)


def make_rule(
    name_val: str = "test_rule",
    priority_val: int = 200,
    severity: RiskSeverity = RiskSeverity.WARNING,
    result: TriggeredRule | None = None,
) -> RiskRule:
    """테스트용 구체 RiskRule 구현체 생성.

    evaluate() 의 반환값을 result 로 고정하여 동작을 제어한다.
    """

    class _ConcreteRule(RiskRule):
        priority = priority_val
        default_severity = severity

        @property
        def name(self) -> str:
            return name_val

        def evaluate(self, context: RiskContext) -> TriggeredRule | None:
            return result

    return _ConcreteRule()


# ---------------------------------------------------------------------------
# RiskRule — 클래스 속성 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_priority_is_200():
    """priority 기본값은 200(경고 등급)이어야 한다."""
    rule = make_rule()
    assert rule.priority == 200


@pytest.mark.unit
def test_default_severity_is_warning():
    """default_severity 기본값은 WARNING 이어야 한다."""
    rule = make_rule()
    assert rule.default_severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_custom_priority_is_stored():
    """생성 시 지정한 priority 가 그대로 유지된다."""
    rule = make_rule(priority_val=50)
    assert rule.priority == 50


@pytest.mark.unit
def test_custom_default_severity_is_stored():
    """생성 시 지정한 default_severity 가 그대로 유지된다."""
    rule = make_rule(severity=RiskSeverity.CRITICAL)
    assert rule.default_severity == RiskSeverity.CRITICAL


# ---------------------------------------------------------------------------
# RiskRule — 추상 메서드 강제
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cannot_instantiate_without_name():
    """name 프로퍼티를 구현하지 않으면 인스턴스화 시 TypeError 가 발생한다."""

    class _NoName(RiskRule):
        def evaluate(self, context: RiskContext) -> TriggeredRule | None:
            return None

    with pytest.raises(TypeError):
        _NoName()


@pytest.mark.unit
def test_cannot_instantiate_without_evaluate():
    """evaluate 를 구현하지 않으면 인스턴스화 시 TypeError 가 발생한다."""

    class _NoEvaluate(RiskRule):
        @property
        def name(self) -> str:
            return "no_evaluate"

    with pytest.raises(TypeError):
        _NoEvaluate()


# ---------------------------------------------------------------------------
# RiskRule — _create_triggered
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_triggered_returns_triggered_rule():
    """_create_triggered() 의 반환값이 TriggeredRule 인스턴스여야 한다."""
    rule = make_rule(name_val="drawdown_check")
    result = rule._create_triggered("낙폭 초과")
    assert isinstance(result, TriggeredRule)


@pytest.mark.unit
def test_create_triggered_rule_name_matches_name_property():
    """_create_triggered() 가 생성한 TriggeredRule 의 rule_name 이 name 프로퍼티와 일치한다."""
    rule = make_rule(name_val="drawdown_check")
    result = rule._create_triggered("낙폭 초과")
    assert result.rule_name == "drawdown_check"


@pytest.mark.unit
def test_create_triggered_uses_default_severity_when_none():
    """severity 인자가 None 이면 default_severity 를 사용한다."""
    rule = make_rule(severity=RiskSeverity.CRITICAL)
    result = rule._create_triggered("위반", severity=None)
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_create_triggered_uses_given_severity():
    """severity 인자가 주어지면 default_severity 대신 해당 값을 사용한다."""
    rule = make_rule(severity=RiskSeverity.WARNING)
    result = rule._create_triggered("위반", severity=RiskSeverity.EMERGENCY)
    assert result.severity == RiskSeverity.EMERGENCY


@pytest.mark.unit
def test_create_triggered_message_is_stored():
    """_create_triggered() 에 전달한 메시지가 TriggeredRule 에 그대로 저장된다."""
    rule = make_rule()
    result = rule._create_triggered("일일 손실 한도 초과")
    assert result.message == "일일 손실 한도 초과"


@pytest.mark.unit
def test_create_triggered_suggested_action_is_none_by_default():
    """suggested_action 을 전달하지 않으면 None 이어야 한다."""
    rule = make_rule()
    result = rule._create_triggered("위반")
    assert result.suggested_action is None


@pytest.mark.unit
def test_create_triggered_suggested_action_is_stored():
    """suggested_action 을 전달하면 TriggeredRule 에 저장된다."""
    rule = make_rule()
    result = rule._create_triggered("위반", suggested_action="포지션 축소 권장")
    assert result.suggested_action == "포지션 축소 권장"


# ---------------------------------------------------------------------------
# CompositeRiskRule — 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_composite_name_is_composite_rule():
    """CompositeRiskRule 의 name 은 'CompositeRule' 이어야 한다."""
    composite = CompositeRiskRule(rules=[])
    assert composite.name == "CompositeRule"


@pytest.mark.unit
def test_composite_sorts_rules_by_priority_ascending():
    """생성자에서 rules 를 priority 오름차순으로 정렬한다."""
    low = make_rule(name_val="low", priority_val=300)
    mid = make_rule(name_val="mid", priority_val=150)
    high = make_rule(name_val="high", priority_val=50)

    composite = CompositeRiskRule(rules=[low, mid, high])

    assert [r.name for r in composite.rules] == ["high", "mid", "low"]


@pytest.mark.unit
def test_composite_preserves_equal_priority_order():
    """priority 가 같은 규칙들은 전달된 순서를 유지한다(안정 정렬)."""
    a = make_rule(name_val="a", priority_val=100)
    b = make_rule(name_val="b", priority_val=100)
    c = make_rule(name_val="c", priority_val=100)

    composite = CompositeRiskRule(rules=[a, b, c])

    assert [r.name for r in composite.rules] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# CompositeRiskRule — evaluate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_composite_returns_none_when_no_rules():
    """하위 규칙이 없으면 None 을 반환한다."""
    composite = CompositeRiskRule(rules=[])
    assert composite.evaluate(make_context()) is None


@pytest.mark.unit
def test_composite_returns_none_when_all_rules_pass():
    """모든 하위 규칙이 None 을 반환하면 None 을 반환한다."""
    rules = [make_rule(result=None) for _ in range(3)]
    composite = CompositeRiskRule(rules=rules)
    assert composite.evaluate(make_context()) is None


@pytest.mark.unit
def test_composite_returns_first_triggered_rule():
    """첫 번째로 위반된 규칙의 결과를 반환한다."""
    triggered = make_triggered(rule_name="first_violation")
    rules = [
        make_rule(name_val="pass_rule", result=None),
        make_rule(name_val="fail_rule", result=triggered),
        make_rule(name_val="another_fail", result=make_triggered(rule_name="second")),
    ]
    composite = CompositeRiskRule(rules=rules)

    result = composite.evaluate(make_context())

    assert result is triggered


@pytest.mark.unit
def test_composite_stops_at_first_violation():
    """첫 번째 위반 이후 나머지 규칙은 평가하지 않는다."""
    call_log: list[str] = []

    def make_tracking_rule(name_val: str, triggered_result: TriggeredRule | None) -> RiskRule:
        class _Tracking(RiskRule):
            priority = 200
            default_severity = RiskSeverity.WARNING

            @property
            def name(self) -> str:
                return name_val

            def evaluate(self, context: RiskContext) -> TriggeredRule | None:
                call_log.append(name_val)
                return triggered_result

        return _Tracking()

    first = make_tracking_rule("first", None)
    second = make_tracking_rule("second", make_triggered())
    third = make_tracking_rule("third", None)

    composite = CompositeRiskRule(rules=[first, second, third])
    composite.evaluate(make_context())

    assert "third" not in call_log


@pytest.mark.unit
def test_composite_evaluates_in_priority_order():
    """priority 가 낮은(긴급한) 규칙부터 평가된다."""
    call_log: list[str] = []

    def make_tracking_rule(name_val: str, priority_val: int) -> RiskRule:
        class _Tracking(RiskRule):
            priority = priority_val
            default_severity = RiskSeverity.WARNING

            @property
            def name(self) -> str:
                return name_val

            def evaluate(self, context: RiskContext) -> TriggeredRule | None:
                call_log.append(name_val)
                return None

        return _Tracking()

    rules = [
        make_tracking_rule("info_rule", priority_val=300),
        make_tracking_rule("emergency_rule", priority_val=50),
        make_tracking_rule("warning_rule", priority_val=200),
    ]
    composite = CompositeRiskRule(rules=rules)
    composite.evaluate(make_context())

    assert call_log == ["emergency_rule", "warning_rule", "info_rule"]

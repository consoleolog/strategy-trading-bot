"""MaxDrawdownRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.risk.rules.max_drawdown_rule import MaxDrawdownRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(drawdown_percent: str):
    """current_drawdown_percent 만 지정한 최소 RiskContext 생성."""
    from src.models.risk_context import RiskContext

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
        current_drawdown_percent=Decimal(drawdown_percent),
    )


# ---------------------------------------------------------------------------
# name 프로퍼티
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_is_max_drawdown_rule():
    """name 프로퍼티가 'MaxDrawdownRule' 을 반환한다."""
    rule = MaxDrawdownRule()
    assert rule.name == "MaxDrawdownRule"


# ---------------------------------------------------------------------------
# 낙폭 없음 — None 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_no_drawdown():
    """낙폭이 0% 이면 None 을 반환한다."""
    rule = MaxDrawdownRule()
    assert rule.evaluate(make_context("0")) is None


@pytest.mark.unit
def test_returns_none_below_warning_threshold():
    """낙폭이 warning_threshold 미만이면 None 을 반환한다."""
    rule = MaxDrawdownRule(warning_threshold=Decimal("10"))
    assert rule.evaluate(make_context("9.99")) is None


# ---------------------------------------------------------------------------
# WARNING 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_warning_at_warning_threshold():
    """낙폭이 warning_threshold 에 정확히 도달하면 WARNING 을 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("10"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_returns_warning_between_warning_and_critical():
    """낙폭이 warning_threshold 이상 critical_threshold 미만이면 WARNING 을 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("12"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_warning_message_contains_drawdown_value():
    """WARNING 발화 메시지에 낙폭 수치가 포함된다."""
    rule = MaxDrawdownRule(warning_threshold=Decimal("10"))
    result = rule.evaluate(make_context("11.5"))
    assert "11.5" in result.message


@pytest.mark.unit
def test_warning_suggested_action():
    """WARNING 발화 시 suggested_action 이 None 이 아니다."""
    rule = MaxDrawdownRule()
    result = rule.evaluate(make_context("10"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# CRITICAL 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_critical_threshold():
    """낙폭이 critical_threshold 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("15"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_between_critical_and_emergency():
    """낙폭이 critical_threshold 이상 emergency_threshold 미만이면 CRITICAL 을 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("17"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_takes_priority_over_warning():
    """CRITICAL 임계값을 초과하면 WARNING 이 아닌 CRITICAL 을 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("15"))
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_message_contains_drawdown_value():
    """CRITICAL 발화 메시지에 낙폭 수치가 포함된다."""
    rule = MaxDrawdownRule(critical_threshold=Decimal("15"))
    result = rule.evaluate(make_context("16"))
    assert "16.0" in result.message


# ---------------------------------------------------------------------------
# EMERGENCY 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_emergency_at_emergency_threshold():
    """낙폭이 emergency_threshold 에 정확히 도달하면 EMERGENCY 를 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("20"))
    assert result is not None
    assert result.severity == RiskSeverity.EMERGENCY


@pytest.mark.unit
def test_returns_emergency_above_emergency_threshold():
    """낙폭이 emergency_threshold 초과이면 EMERGENCY 를 반환한다."""
    rule = MaxDrawdownRule(emergency_threshold=Decimal("20"))
    result = rule.evaluate(make_context("25"))
    assert result is not None
    assert result.severity == RiskSeverity.EMERGENCY


@pytest.mark.unit
def test_emergency_takes_priority_over_critical():
    """EMERGENCY 임계값을 초과하면 CRITICAL 이 아닌 EMERGENCY 를 반환한다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("10"),
        critical_threshold=Decimal("15"),
        emergency_threshold=Decimal("20"),
    )
    result = rule.evaluate(make_context("20"))
    assert result.severity == RiskSeverity.EMERGENCY


@pytest.mark.unit
def test_emergency_message_contains_drawdown_value():
    """EMERGENCY 발화 메시지에 낙폭 수치가 포함된다."""
    rule = MaxDrawdownRule(emergency_threshold=Decimal("20"))
    result = rule.evaluate(make_context("22"))
    assert "22.0" in result.message


@pytest.mark.unit
def test_emergency_suggested_action():
    """EMERGENCY 발화 시 suggested_action 이 None 이 아니다."""
    rule = MaxDrawdownRule()
    result = rule.evaluate(make_context("20"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# rule_name 포함 여부
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_triggered_rule_name():
    """발화된 TriggeredRule 의 rule_name 이 'MaxDrawdownRule' 이다."""
    rule = MaxDrawdownRule()
    result = rule.evaluate(make_context("10"))
    assert result.rule_name == "MaxDrawdownRule"


# ---------------------------------------------------------------------------
# 커스텀 임계값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_custom_thresholds_respected():
    """생성자에서 전달한 커스텀 임계값이 올바르게 적용된다."""
    rule = MaxDrawdownRule(
        warning_threshold=Decimal("5"),
        critical_threshold=Decimal("8"),
        emergency_threshold=Decimal("12"),
    )
    assert rule.evaluate(make_context("4.9")) is None
    assert rule.evaluate(make_context("5")).severity == RiskSeverity.WARNING
    assert rule.evaluate(make_context("8")).severity == RiskSeverity.CRITICAL
    assert rule.evaluate(make_context("12")).severity == RiskSeverity.EMERGENCY


# ---------------------------------------------------------------------------
# priority / default_severity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_is_10():
    """MaxDrawdownRule.priority 가 10 이다."""
    assert MaxDrawdownRule.priority == 10


@pytest.mark.unit
def test_default_severity_is_critical():
    """MaxDrawdownRule.default_severity 가 CRITICAL 이다."""
    assert MaxDrawdownRule.default_severity == RiskSeverity.CRITICAL

"""WeeklyLossLimitRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.risk.rules.weekly_loss_rule import WeeklyLossLimitRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(weekly_pnl_percent: str):
    """weekly_pnl_percent 만 지정한 최소 RiskContext 를 생성한다."""
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
        weekly_pnl_percent=Decimal(weekly_pnl_percent),
        peak_portfolio_value_krw=Decimal("10000000"),
        current_drawdown_percent=Decimal("0"),
    )


# ---------------------------------------------------------------------------
# name 프로퍼티
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_is_weekly_loss_limit_rule():
    """name 프로퍼티가 'WeeklyLossLimitRule' 을 반환한다."""
    rule = WeeklyLossLimitRule()
    assert rule.name == "WeeklyLossLimitRule"


# ---------------------------------------------------------------------------
# 손실 없음 / 이익 — None 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_no_loss():
    """주간 손익이 0% 이면 None 을 반환한다."""
    rule = WeeklyLossLimitRule()
    assert rule.evaluate(make_context("0")) is None


@pytest.mark.unit
def test_returns_none_when_profit():
    """주간 손익이 양수(이익)이면 None 을 반환한다."""
    rule = WeeklyLossLimitRule()
    assert rule.evaluate(make_context("3")) is None


@pytest.mark.unit
def test_returns_none_below_warning_threshold():
    """손실률이 warning_threshold 미만이면 None 을 반환한다."""
    rule = WeeklyLossLimitRule(warning_threshold=Decimal("7"))
    assert rule.evaluate(make_context("-6.99")) is None


# ---------------------------------------------------------------------------
# WARNING 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_warning_at_warning_threshold():
    """손실률이 warning_threshold 에 정확히 도달하면 WARNING 을 반환한다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("7"),
        critical_threshold=Decimal("10"),
    )
    result = rule.evaluate(make_context("-7"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_returns_warning_between_warning_and_critical():
    """손실률이 warning_threshold 이상 critical_threshold 미만이면 WARNING 을 반환한다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("7"),
        critical_threshold=Decimal("10"),
    )
    result = rule.evaluate(make_context("-8"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_warning_rule_name():
    """WARNING 발화 시 rule_name 이 'WeeklyLossLimitRule' 이다."""
    rule = WeeklyLossLimitRule()
    result = rule.evaluate(make_context("-7"))
    assert result.rule_name == "WeeklyLossLimitRule"


@pytest.mark.unit
def test_warning_message_contains_loss_value():
    """WARNING 발화 메시지에 손실률 수치가 포함된다."""
    rule = WeeklyLossLimitRule(warning_threshold=Decimal("7"))
    result = rule.evaluate(make_context("-8.5"))
    assert "8.50" in result.message


@pytest.mark.unit
def test_warning_suggested_action():
    """WARNING 발화 시 suggested_action 이 None 이 아니다."""
    rule = WeeklyLossLimitRule()
    result = rule.evaluate(make_context("-7"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# CRITICAL 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_critical_threshold():
    """손실률이 critical_threshold 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("7"),
        critical_threshold=Decimal("10"),
    )
    result = rule.evaluate(make_context("-10"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_above_critical_threshold():
    """손실률이 critical_threshold 초과이면 CRITICAL 을 반환한다."""
    rule = WeeklyLossLimitRule(critical_threshold=Decimal("10"))
    result = rule.evaluate(make_context("-15"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_takes_priority_over_warning():
    """critical_threshold 도달 시 WARNING 이 아닌 CRITICAL 을 반환한다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("7"),
        critical_threshold=Decimal("10"),
    )
    result = rule.evaluate(make_context("-10"))
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_message_contains_loss_value():
    """CRITICAL 발화 메시지에 손실률 수치가 포함된다."""
    rule = WeeklyLossLimitRule(critical_threshold=Decimal("10"))
    result = rule.evaluate(make_context("-12"))
    assert "12.00" in result.message


@pytest.mark.unit
def test_critical_suggested_action():
    """CRITICAL 발화 시 suggested_action 이 None 이 아니다."""
    rule = WeeklyLossLimitRule()
    result = rule.evaluate(make_context("-10"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# 경계값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_just_below_warning_threshold():
    """손실률이 warning_threshold 에 미달하면 None 을 반환한다."""
    rule = WeeklyLossLimitRule(warning_threshold=Decimal("7"))
    assert rule.evaluate(make_context("-6.99")) is None


@pytest.mark.unit
def test_returns_warning_just_at_warning_threshold():
    """손실률이 warning_threshold 와 일치하면 WARNING 을 반환한다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("7"),
        critical_threshold=Decimal("10"),
    )
    result = rule.evaluate(make_context("-7.00"))
    assert result.severity == RiskSeverity.WARNING


# ---------------------------------------------------------------------------
# 커스텀 임계값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_custom_thresholds_respected():
    """생성자에서 전달한 커스텀 임계값이 올바르게 적용된다."""
    rule = WeeklyLossLimitRule(
        warning_threshold=Decimal("5"),
        critical_threshold=Decimal("8"),
    )
    assert rule.evaluate(make_context("-4.9")) is None
    assert rule.evaluate(make_context("-5")).severity == RiskSeverity.WARNING
    assert rule.evaluate(make_context("-8")).severity == RiskSeverity.CRITICAL


# ---------------------------------------------------------------------------
# priority / default_severity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_is_25():
    """WeeklyLossLimitRule.priority 가 25 이다."""
    assert WeeklyLossLimitRule.priority == 25


@pytest.mark.unit
def test_default_severity_is_warning():
    """WeeklyLossLimitRule.default_severity 가 WARNING 이다."""
    assert WeeklyLossLimitRule.default_severity == RiskSeverity.WARNING

"""PositionSizeRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.risk.rules.position_size_rule import PositionSizeRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(proposed_trade_risk_percent: str | None):
    """proposed_trade_risk_percent 를 지정한 최소 RiskContext 를 생성한다."""
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
        current_drawdown_percent=Decimal("0"),
        proposed_trade_risk_percent=(
            Decimal(proposed_trade_risk_percent) if proposed_trade_risk_percent is not None else None
        ),
    )


# ---------------------------------------------------------------------------
# name 프로퍼티
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_is_position_size_rule():
    """name 프로퍼티가 'PositionSizeRule' 을 반환한다."""
    rule = PositionSizeRule()
    assert rule.name == "PositionSizeRule"


# ---------------------------------------------------------------------------
# proposed_trade_risk_percent 가 None — 평가 대상 아님
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_risk_percent_is_none():
    """proposed_trade_risk_percent 가 None 이면 None 을 반환한다."""
    rule = PositionSizeRule()
    assert rule.evaluate(make_context(None)) is None


# ---------------------------------------------------------------------------
# 임계값 미달 — None 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_risk_is_zero():
    """리스크 비율이 0% 이면 None 을 반환한다."""
    rule = PositionSizeRule()
    assert rule.evaluate(make_context("0")) is None


@pytest.mark.unit
def test_returns_none_below_warning_threshold():
    """리스크 비율이 warning_threshold 미만이면 None 을 반환한다."""
    rule = PositionSizeRule(warning_threshold=Decimal("1.5"))
    assert rule.evaluate(make_context("1.49")) is None


# ---------------------------------------------------------------------------
# INFO 발화 조건 — warning_threshold 이상 max_risk_percent 미만
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_info_at_warning_threshold():
    """리스크 비율이 warning_threshold 에 정확히 도달하면 INFO 를 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("1.5"))
    assert result is not None
    assert result.severity == RiskSeverity.INFO


@pytest.mark.unit
def test_returns_info_between_warning_and_max_risk():
    """리스크 비율이 warning_threshold 이상 max_risk_percent 미만이면 INFO 를 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("1.8"))
    assert result is not None
    assert result.severity == RiskSeverity.INFO


@pytest.mark.unit
def test_info_rule_name():
    """INFO 발화 시 rule_name 이 'PositionSizeRule' 이다."""
    rule = PositionSizeRule()
    result = rule.evaluate(make_context("1.5"))
    assert result.rule_name == "PositionSizeRule"


@pytest.mark.unit
def test_info_message_contains_risk_value():
    """INFO 발화 메시지에 리스크 비율 수치가 포함된다."""
    rule = PositionSizeRule(warning_threshold=Decimal("1.5"))
    result = rule.evaluate(make_context("1.7"))
    assert "1.70" in result.message


@pytest.mark.unit
def test_info_suggested_action():
    """INFO 발화 시 suggested_action 이 None 이 아니다."""
    rule = PositionSizeRule()
    result = rule.evaluate(make_context("1.5"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# WARNING 발화 조건 — max_risk_percent 이상 hard_limit_percent 미만
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_warning_at_max_risk_percent():
    """리스크 비율이 max_risk_percent 에 정확히 도달하면 WARNING 을 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("2"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_returns_warning_between_max_risk_and_hard_limit():
    """리스크 비율이 max_risk_percent 이상 hard_limit_percent 미만이면 WARNING 을 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("2.5"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_warning_takes_priority_over_info():
    """max_risk_percent 도달 시 INFO 가 아닌 WARNING 을 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("2"))
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_warning_message_contains_risk_value():
    """WARNING 발화 메시지에 리스크 비율 수치가 포함된다."""
    rule = PositionSizeRule(max_risk_percent=Decimal("2"))
    result = rule.evaluate(make_context("2.3"))
    assert "2.30" in result.message


@pytest.mark.unit
def test_warning_suggested_action_contains_max_risk():
    """WARNING 발화 시 suggested_action 에 max_risk_percent 값이 포함된다."""
    rule = PositionSizeRule(max_risk_percent=Decimal("2"))
    result = rule.evaluate(make_context("2.5"))
    assert "2" in result.suggested_action


# ---------------------------------------------------------------------------
# CRITICAL 발화 조건 — hard_limit_percent 이상
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_hard_limit():
    """리스크 비율이 hard_limit_percent 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("3"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_above_hard_limit():
    """리스크 비율이 hard_limit_percent 초과이면 CRITICAL 을 반환한다."""
    rule = PositionSizeRule(hard_limit_percent=Decimal("3"))
    result = rule.evaluate(make_context("5"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_takes_priority_over_warning():
    """hard_limit_percent 도달 시 WARNING 이 아닌 CRITICAL 을 반환한다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1.5"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("3"),
    )
    result = rule.evaluate(make_context("3"))
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_message_contains_hard_limit():
    """CRITICAL 발화 메시지에 hard_limit_percent 값이 포함된다."""
    rule = PositionSizeRule(hard_limit_percent=Decimal("3"))
    result = rule.evaluate(make_context("3"))
    assert "3%" in result.message


@pytest.mark.unit
def test_critical_suggested_action_contains_max_risk():
    """CRITICAL 발화 시 suggested_action 에 max_risk_percent 값이 포함된다."""
    rule = PositionSizeRule(max_risk_percent=Decimal("2"), hard_limit_percent=Decimal("3"))
    result = rule.evaluate(make_context("3"))
    assert "2" in result.suggested_action


# ---------------------------------------------------------------------------
# 커스텀 임계값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_custom_thresholds_respected():
    """생성자에서 전달한 커스텀 임계값이 올바르게 적용된다."""
    rule = PositionSizeRule(
        warning_threshold=Decimal("1"),
        max_risk_percent=Decimal("2"),
        hard_limit_percent=Decimal("4"),
    )
    assert rule.evaluate(make_context("0.99")) is None
    assert rule.evaluate(make_context("1")).severity == RiskSeverity.INFO
    assert rule.evaluate(make_context("2")).severity == RiskSeverity.WARNING
    assert rule.evaluate(make_context("4")).severity == RiskSeverity.CRITICAL


# ---------------------------------------------------------------------------
# priority / default_severity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_is_100():
    """PositionSizeRule.priority 가 100 이다."""
    assert PositionSizeRule.priority == 100


@pytest.mark.unit
def test_default_severity_is_critical():
    """PositionSizeRule.default_severity 가 CRITICAL 이다."""
    assert PositionSizeRule.default_severity == RiskSeverity.CRITICAL

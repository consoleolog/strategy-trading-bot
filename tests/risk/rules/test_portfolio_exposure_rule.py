"""PortfolioExposureRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.risk.rules.portfolio_exposure_rule import PortfolioExposureRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(exposure_percent: str):
    """position_utilization_percent 가 exposure_percent 가 되도록 RiskContext 를 생성한다.

    portfolio_value_krw=10_000_000 을 기준으로
    total_position_value_krw = portfolio * (exposure / 100) 으로 설정한다.
    """
    from src.models.risk_context import RiskContext

    portfolio = Decimal("10000000")
    position_value = portfolio * Decimal(exposure_percent) / Decimal("100")

    return RiskContext(
        system_state="RUNNING",
        mode="DRY_RUN",
        open_positions_count=0,
        total_position_value_krw=position_value,
        portfolio_value_krw=portfolio,
        starting_capital_krw=portfolio,
        daily_pnl_krw=Decimal("0"),
        daily_pnl_percent=Decimal("0"),
        weekly_pnl_krw=Decimal("0"),
        weekly_pnl_percent=Decimal("0"),
        peak_portfolio_value_krw=portfolio,
        current_drawdown_percent=Decimal("0"),
    )


# ---------------------------------------------------------------------------
# name 프로퍼티
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_is_portfolio_exposure_rule():
    """name 프로퍼티가 'PortfolioExposureRule' 을 반환한다."""
    rule = PortfolioExposureRule()
    assert rule.name == "PortfolioExposureRule"


# ---------------------------------------------------------------------------
# 노출도 여유 — None 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_no_exposure():
    """노출도가 0% 이면 None 을 반환한다."""
    rule = PortfolioExposureRule()
    assert rule.evaluate(make_context("0")) is None


@pytest.mark.unit
def test_returns_none_below_warning_threshold():
    """노출도가 warning_threshold 미만이면 None 을 반환한다."""
    rule = PortfolioExposureRule(warning_threshold=Decimal("30"))
    assert rule.evaluate(make_context("29.9")) is None


# ---------------------------------------------------------------------------
# WARNING 발화 조건
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_warning_at_warning_threshold():
    """노출도가 warning_threshold 에 정확히 도달하면 WARNING 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("30"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_returns_warning_between_warning_and_max():
    """노출도가 warning_threshold 이상 max_exposure 미만이면 WARNING 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("35"))
    assert result is not None
    assert result.severity == RiskSeverity.WARNING


@pytest.mark.unit
def test_warning_rule_name():
    """WARNING 발화 시 rule_name 이 'PortfolioExposureRule' 이다."""
    rule = PortfolioExposureRule()
    result = rule.evaluate(make_context("30"))
    assert result.rule_name == "PortfolioExposureRule"


@pytest.mark.unit
def test_warning_message_contains_exposure_value():
    """WARNING 발화 메시지에 노출도 수치가 포함된다."""
    rule = PortfolioExposureRule(warning_threshold=Decimal("30"))
    result = rule.evaluate(make_context("35"))
    assert "35.0" in result.message


@pytest.mark.unit
def test_warning_suggested_action():
    """WARNING 발화 시 suggested_action 이 None 이 아니다."""
    rule = PortfolioExposureRule()
    result = rule.evaluate(make_context("30"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# CRITICAL(최대치) 발화 조건 — max_exposure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_max_exposure():
    """노출도가 max_exposure 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("40"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_between_max_and_critical_exposure():
    """노출도가 max_exposure 이상 critical_exposure 미만이면 CRITICAL 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("50"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_max_exposure_critical_takes_priority_over_warning():
    """max_exposure 도달 시 WARNING 이 아닌 CRITICAL 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("40"))
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_max_exposure_message_contains_exposure_value():
    """max_exposure 도달 시 메시지에 노출도 수치가 포함된다."""
    rule = PortfolioExposureRule(max_exposure=Decimal("40"))
    result = rule.evaluate(make_context("40"))
    assert "40.0" in result.message


# ---------------------------------------------------------------------------
# CRITICAL(위험 수준) 발화 조건 — critical_exposure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_critical_exposure():
    """노출도가 critical_exposure 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("30"),
        max_exposure=Decimal("40"),
        critical_exposure=Decimal("60"),
    )
    result = rule.evaluate(make_context("60"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_above_critical_exposure():
    """노출도가 critical_exposure 초과이면 CRITICAL 을 반환한다."""
    rule = PortfolioExposureRule(critical_exposure=Decimal("60"))
    result = rule.evaluate(make_context("80"))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_exposure_message_contains_critically_high():
    """critical_exposure 도달 시 메시지에 'critically high' 가 포함된다."""
    rule = PortfolioExposureRule(critical_exposure=Decimal("60"))
    result = rule.evaluate(make_context("60"))
    assert "critically high" in result.message


@pytest.mark.unit
def test_critical_exposure_suggested_action():
    """critical_exposure 도달 시 suggested_action 이 None 이 아니다."""
    rule = PortfolioExposureRule()
    result = rule.evaluate(make_context("60"))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# 커스텀 임계값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_custom_thresholds_respected():
    """생성자에서 전달한 커스텀 임계값이 올바르게 적용된다."""
    rule = PortfolioExposureRule(
        warning_threshold=Decimal("20"),
        max_exposure=Decimal("30"),
        critical_exposure=Decimal("50"),
    )
    assert rule.evaluate(make_context("19.9")) is None
    assert rule.evaluate(make_context("20")).severity == RiskSeverity.WARNING
    assert rule.evaluate(make_context("30")).severity == RiskSeverity.CRITICAL
    assert rule.evaluate(make_context("50")).severity == RiskSeverity.CRITICAL


# ---------------------------------------------------------------------------
# priority / default_severity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_is_105():
    """PortfolioExposureRule.priority 가 105 이다."""
    assert PortfolioExposureRule.priority == 105


@pytest.mark.unit
def test_default_severity_is_warning():
    """PortfolioExposureRule.default_severity 가 WARNING 이다."""
    assert PortfolioExposureRule.default_severity == RiskSeverity.WARNING

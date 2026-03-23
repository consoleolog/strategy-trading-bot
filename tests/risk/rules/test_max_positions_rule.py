"""MaxPositionsRule 단위 테스트."""

from decimal import Decimal

import pytest
from src.risk.rules.max_positions_rule import MaxPositionsRule
from src.utils.constants import RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(open_positions_count: int):
    """open_positions_count 만 지정한 최소 RiskContext 생성."""
    from src.models.risk_context import RiskContext

    return RiskContext(
        system_state="RUNNING",
        mode="DRY_RUN",
        open_positions_count=open_positions_count,
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


# ---------------------------------------------------------------------------
# name 프로퍼티
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_is_max_positions_rule():
    """name 프로퍼티가 'MaxPositionsRule' 을 반환한다."""
    rule = MaxPositionsRule()
    assert rule.name == "MaxPositionsRule"


# ---------------------------------------------------------------------------
# 포지션 수 여유 — None 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_no_positions():
    """보유 포지션이 0개이면 None 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    assert rule.evaluate(make_context(0)) is None


@pytest.mark.unit
def test_returns_none_well_below_max():
    """포지션 수가 max_positions - 1 미만이면 None 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    # max_positions - 1 = 4, 포지션 3개 → 임계 미달
    assert rule.evaluate(make_context(3)) is None


# ---------------------------------------------------------------------------
# INFO 발화 조건 (max_positions - 1 도달)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_info_at_max_minus_one():
    """포지션 수가 max_positions - 1 에 도달하면 INFO 를 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(4))
    assert result is not None
    assert result.severity == RiskSeverity.INFO


@pytest.mark.unit
def test_info_rule_name():
    """INFO 발화 시 rule_name 이 'MaxPositionsRule' 이다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(4))
    assert result.rule_name == "MaxPositionsRule"


@pytest.mark.unit
def test_info_message_contains_position_counts():
    """INFO 발화 메시지에 현재/최대 포지션 수가 포함된다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(4))
    assert "4" in result.message
    assert "5" in result.message


@pytest.mark.unit
def test_info_suggested_action():
    """INFO 발화 시 suggested_action 이 None 이 아니다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(4))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# CRITICAL 발화 조건 (max_positions 도달)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_critical_at_max_positions():
    """포지션 수가 max_positions 에 정확히 도달하면 CRITICAL 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(5))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_returns_critical_above_max_positions():
    """포지션 수가 max_positions 초과이면 CRITICAL 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(7))
    assert result is not None
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_takes_priority_over_info():
    """포지션 수가 max_positions 에 도달하면 INFO 가 아닌 CRITICAL 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(5))
    assert result.severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_critical_message_contains_max_positions():
    """CRITICAL 발화 메시지에 max_positions 값이 포함된다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(5))
    assert "5" in result.message


@pytest.mark.unit
def test_critical_suggested_action():
    """CRITICAL 발화 시 suggested_action 이 None 이 아니다."""
    rule = MaxPositionsRule(max_positions=5)
    result = rule.evaluate(make_context(5))
    assert result.suggested_action is not None


# ---------------------------------------------------------------------------
# 경계값 — max_positions - 2 (임계 직전)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_at_max_minus_two():
    """포지션 수가 max_positions - 2 이면 None 을 반환한다."""
    rule = MaxPositionsRule(max_positions=5)
    # 5 - 2 = 3, INFO 임계는 4 → None 반환
    assert rule.evaluate(make_context(3)) is None


# ---------------------------------------------------------------------------
# 커스텀 max_positions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_custom_max_positions_respected():
    """생성자에서 전달한 max_positions 가 올바르게 적용된다."""
    rule = MaxPositionsRule(max_positions=3)
    assert rule.evaluate(make_context(1)) is None
    assert rule.evaluate(make_context(2)).severity == RiskSeverity.INFO
    assert rule.evaluate(make_context(3)).severity == RiskSeverity.CRITICAL


@pytest.mark.unit
def test_default_max_positions_is_5():
    """기본 max_positions 는 5 이다."""
    rule = MaxPositionsRule()
    assert rule.max_positions == 5


# ---------------------------------------------------------------------------
# max_positions = 1 (엣지 케이스)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_positions_one_returns_critical_at_one():
    """max_positions=1 일 때 포지션 1개이면 CRITICAL 을 반환한다."""
    rule = MaxPositionsRule(max_positions=1)
    result = rule.evaluate(make_context(1))
    assert result.severity == RiskSeverity.CRITICAL


# ---------------------------------------------------------------------------
# priority / default_severity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_priority_is_110():
    """MaxPositionsRule.priority 가 110 이다."""
    assert MaxPositionsRule.priority == 110


@pytest.mark.unit
def test_default_severity_is_warning():
    """MaxPositionsRule.default_severity 가 WARNING 이다."""
    assert MaxPositionsRule.default_severity == RiskSeverity.WARNING

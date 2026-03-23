"""RiskEngine 단위 테스트."""

from decimal import Decimal

import pytest
from src.models.risk_context import RiskContext
from src.models.risk_record import RiskRecord
from src.models.triggered_rule import TriggeredRule
from src.risk.risk_engine import RiskEngine
from src.risk.risk_rule import RiskRule
from src.utils.constants import RiskDecision, RiskSeverity

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_context(
    portfolio_value: str = "10000000",
    drawdown_percent: str = "0",
) -> RiskContext:
    """테스트용 RiskContext 생성."""
    return RiskContext(
        system_state="RUNNING",
        mode="DRY_RUN",
        open_positions_count=0,
        total_position_value_krw=Decimal("0"),
        portfolio_value_krw=Decimal(portfolio_value),
        starting_capital_krw=Decimal("10000000"),
        daily_pnl_krw=Decimal("0"),
        daily_pnl_percent=Decimal("0"),
        weekly_pnl_krw=Decimal("0"),
        weekly_pnl_percent=Decimal("0"),
        peak_portfolio_value_krw=Decimal("10000000"),
        current_drawdown_percent=Decimal(drawdown_percent),
    )


def make_triggered(
    severity: RiskSeverity = RiskSeverity.WARNING,
    message: str = "위반 발생",
    suggested_action: str | None = None,
) -> TriggeredRule:
    """테스트용 TriggeredRule 생성."""
    return TriggeredRule(
        rule_name="test_rule",
        severity=severity,
        message=message,
        suggested_action=suggested_action,
    )


def make_rule(
    priority_val: int = 200,
    result: TriggeredRule | None = None,
) -> RiskRule:
    """evaluate() 반환값이 고정된 테스트용 RiskRule 구현체 생성."""

    class _Rule(RiskRule):
        priority = priority_val
        default_severity = RiskSeverity.WARNING

        @property
        def name(self) -> str:
            return "test_rule"

        def evaluate(self, context: RiskContext) -> TriggeredRule | None:
            return result

    return _Rule()


@pytest.fixture
def context() -> RiskContext:
    return make_context()


# ---------------------------------------------------------------------------
# __init__ — 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rules_sorted_by_priority_ascending():
    """생성자에서 rules 를 priority 오름차순으로 정렬한다."""
    low = make_rule(priority_val=300)
    mid = make_rule(priority_val=150)
    high = make_rule(priority_val=50)

    engine = RiskEngine(rules=[low, mid, high])

    assert [r.priority for r in engine.rules] == [50, 150, 300]


# ---------------------------------------------------------------------------
# evaluate — 규칙 없음 / 전부 통과
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_allow_when_no_rules(context):
    """등록된 규칙이 없으면 ALLOW 결정을 반환한다."""
    engine = RiskEngine(rules=[])
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.ALLOW


@pytest.mark.unit
def test_returns_allow_when_all_rules_pass(context):
    """모든 규칙이 None 을 반환하면 ALLOW 결정을 반환한다."""
    engine = RiskEngine(rules=[make_rule(result=None) for _ in range(3)])
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.ALLOW


@pytest.mark.unit
def test_triggered_rules_empty_when_all_pass(context):
    """모든 규칙 통과 시 RiskRecord.triggered_rules 가 빈 목록이어야 한다."""
    engine = RiskEngine(rules=[make_rule(result=None)])
    record = engine.evaluate(context, "decision-001")
    assert record.triggered_rules == []


@pytest.mark.unit
def test_decision_id_stored_in_record(context):
    """evaluate() 에 전달한 decision_id 가 RiskRecord 에 저장된다."""
    engine = RiskEngine(rules=[])
    record = engine.evaluate(context, "decision-xyz")
    assert record.input_decision_id == "decision-xyz"


@pytest.mark.unit
def test_returns_risk_record_instance(context):
    """evaluate() 의 반환값이 RiskRecord 인스턴스이어야 한다."""
    engine = RiskEngine(rules=[])
    assert isinstance(engine.evaluate(context, "decision-001"), RiskRecord)


# ---------------------------------------------------------------------------
# evaluate — 발화 규칙 수집
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_triggered_rules_collected(context):
    """발화된 규칙이 RiskRecord.triggered_rules 에 수집된다."""
    triggered = make_triggered(severity=RiskSeverity.WARNING)
    engine = RiskEngine(
        rules=[
            make_rule(result=None),
            make_rule(result=triggered),
        ]
    )
    record = engine.evaluate(context, "decision-001")
    assert triggered in record.triggered_rules


@pytest.mark.unit
def test_all_triggered_rules_collected(context):
    """여러 규칙이 발화되면 모두 수집된다."""
    t1 = make_triggered(severity=RiskSeverity.WARNING, message="경고 1")
    t2 = make_triggered(severity=RiskSeverity.INFO, message="정보 1")
    engine = RiskEngine(rules=[make_rule(result=t1), make_rule(result=t2)])
    record = engine.evaluate(context, "decision-001")
    assert len(record.triggered_rules) == 2


# ---------------------------------------------------------------------------
# evaluate — 심각도별 결정
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_emergency_rule_returns_emergency_stop(context):
    """EMERGENCY 규칙 발화 시 EMERGENCY_STOP 을 반환한다."""
    engine = RiskEngine(rules=[make_rule(result=make_triggered(severity=RiskSeverity.EMERGENCY))])
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.EMERGENCY_STOP


@pytest.mark.unit
def test_critical_rule_returns_force_no_action(context):
    """CRITICAL 규칙 발화 시 FORCE_NO_ACTION 을 반환한다."""
    engine = RiskEngine(rules=[make_rule(result=make_triggered(severity=RiskSeverity.CRITICAL))])
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.FORCE_NO_ACTION


@pytest.mark.unit
def test_warning_rule_returns_reduce_size(context):
    """WARNING 규칙 발화 시 REDUCE_SIZE 를 반환한다."""
    engine = RiskEngine(rules=[make_rule(result=make_triggered(severity=RiskSeverity.WARNING))])
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.REDUCE_SIZE


@pytest.mark.unit
def test_emergency_takes_priority_over_critical(context):
    """EMERGENCY 와 CRITICAL 이 함께 발화되면 EMERGENCY_STOP 이 우선한다."""
    engine = RiskEngine(
        rules=[
            make_rule(result=make_triggered(severity=RiskSeverity.CRITICAL)),
            make_rule(result=make_triggered(severity=RiskSeverity.EMERGENCY)),
        ]
    )
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.EMERGENCY_STOP


@pytest.mark.unit
def test_critical_takes_priority_over_warning(context):
    """CRITICAL 과 WARNING 이 함께 발화되면 FORCE_NO_ACTION 이 우선한다."""
    engine = RiskEngine(
        rules=[
            make_rule(result=make_triggered(severity=RiskSeverity.WARNING)),
            make_rule(result=make_triggered(severity=RiskSeverity.CRITICAL)),
        ]
    )
    record = engine.evaluate(context, "decision-001")
    assert record.risk_decision == RiskDecision.FORCE_NO_ACTION


# ---------------------------------------------------------------------------
# evaluate — max_allowed_size_krw
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_allowed_size_set_on_reduce_size(context):
    """REDUCE_SIZE 결정 시 max_allowed_size_krw 가 계산된다."""
    engine = RiskEngine(rules=[make_rule(result=make_triggered(severity=RiskSeverity.WARNING))])
    record = engine.evaluate(context, "decision-001")
    assert record.max_allowed_size_krw is not None


@pytest.mark.unit
def test_max_allowed_size_none_on_allow(context):
    """ALLOW 결정 시 max_allowed_size_krw 는 None 이어야 한다."""
    engine = RiskEngine(rules=[make_rule(result=None)])
    record = engine.evaluate(context, "decision-001")
    assert record.max_allowed_size_krw is None


@pytest.mark.unit
def test_max_allowed_size_none_on_emergency_stop(context):
    """EMERGENCY_STOP 결정 시 max_allowed_size_krw 는 None 이어야 한다."""
    engine = RiskEngine(rules=[make_rule(result=make_triggered(severity=RiskSeverity.EMERGENCY))])
    record = engine.evaluate(context, "decision-001")
    assert record.max_allowed_size_krw is None


# ---------------------------------------------------------------------------
# _aggregate_decision — reason / recommended_action
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reason_contains_all_risk_rules_passed_when_empty():
    """발화 규칙이 없을 때 reason 에 'All risk rules passed' 가 포함된다."""
    result = RiskEngine._aggregate_decision([])
    assert result["reason"] == "All risk rules passed"


@pytest.mark.unit
def test_reason_contains_emergency_message():
    """EMERGENCY 발화 시 reason 이 'Emergency: ...' 형식이어야 한다."""
    triggered = make_triggered(severity=RiskSeverity.EMERGENCY, message="낙폭 초과")
    result = RiskEngine._aggregate_decision([triggered])
    assert result["reason"] == "Emergency: 낙폭 초과"


@pytest.mark.unit
def test_reason_contains_critical_blocked_message():
    """CRITICAL 발화 시 reason 이 'Blocked: ...' 형식이어야 한다."""
    triggered = make_triggered(severity=RiskSeverity.CRITICAL, message="일일 손실 한도")
    result = RiskEngine._aggregate_decision([triggered])
    assert result["reason"] == "Blocked: 일일 손실 한도"


@pytest.mark.unit
def test_reason_contains_warning_message():
    """WARNING 발화 시 reason 이 'Warning: ...' 형식이어야 한다."""
    triggered = make_triggered(severity=RiskSeverity.WARNING, message="포지션 과다")
    result = RiskEngine._aggregate_decision([triggered])
    assert result["reason"] == "Warning: 포지션 과다"


@pytest.mark.unit
def test_critical_recommended_action_from_triggered_rule():
    """CRITICAL 발화 시 recommended_action 이 TriggeredRule.suggested_action 과 일치한다."""
    triggered = make_triggered(
        severity=RiskSeverity.CRITICAL,
        suggested_action="포지션 전량 청산",
    )
    result = RiskEngine._aggregate_decision([triggered])
    assert result["recommended_action"] == "포지션 전량 청산"


@pytest.mark.unit
def test_emergency_recommended_action_is_fixed_string():
    """EMERGENCY 발화 시 recommended_action 은 고정 문자열이어야 한다."""
    triggered = make_triggered(severity=RiskSeverity.EMERGENCY)
    result = RiskEngine._aggregate_decision([triggered])
    assert result["recommended_action"] == "Flatten all positions immediately"


# ---------------------------------------------------------------------------
# _calculate_max_size
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_size_is_two_percent_of_portfolio():
    """낙폭 0% 일 때 최대 주문 크기는 포트폴리오 가치의 2%이다."""
    context = make_context(portfolio_value="10000000", drawdown_percent="0")
    result = RiskEngine._calculate_max_size(context)
    assert result == pytest.approx(200000.0)


@pytest.mark.unit
def test_max_size_halved_when_drawdown_exceeds_10_percent():
    """낙폭이 10%를 초과하면 최대 주문 크기가 절반으로 축소된다."""
    context = make_context(portfolio_value="10000000", drawdown_percent="15")
    result = RiskEngine._calculate_max_size(context)
    assert result == pytest.approx(100000.0)


@pytest.mark.unit
def test_max_size_not_halved_at_exactly_10_percent():
    """낙폭이 정확히 10% 이면 축소되지 않는다 (초과 조건: > 10)."""
    context = make_context(portfolio_value="10000000", drawdown_percent="10")
    result = RiskEngine._calculate_max_size(context)
    assert result == pytest.approx(200000.0)

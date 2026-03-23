from decimal import Decimal

import pytest
from src.decision.position_sizer import PositionSizer
from src.models.portfolio_state import PortfolioState
from src.models.risk_limits_config import RiskLimitsConfig
from src.models.trade_candidate import TradeCandidate
from src.utils.constants import DecisionState, SignalDirection

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------

DEFAULT_RISK_CONFIG = RiskLimitsConfig(
    max_risk_per_trade=0.02,  # 2%
    max_position_size=0.40,  # 40%
    max_portfolio_exposure=0.40,
)

SAMPLE_SIGNAL_DICT = {
    "strategy_id": "test_strategy",
    "indicator_id": "macd_rsi",
    "type": "cross_over",
    "value": "golden_cross",
    "direction": "long",
    "regime": 0,
    "market": "KRW-BTC",
    "timeframe": "1m",
    "timestamp": "2025-01-01T00:00:00",
    "metadata": {},
}


def make_portfolio(
    total_capital: int = 10_000_000,
    available_capital: int | None = None,
    positions_value: int = 0,
) -> PortfolioState:
    """테스트용 PortfolioState 생성.

    positions_value > 0 이면 해당 평가금액을 가진 더미 포지션을 주입한다.
    """
    if available_capital is None:
        available_capital = total_capital

    portfolio = PortfolioState(
        total_capital=Decimal(str(total_capital)),
        available_capital=Decimal(str(available_capital)),
        daily_pnl=Decimal("0"),
        weekly_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        high_water_mark=Decimal(str(total_capital)),
    )

    if positions_value > 0:
        # positions_value 를 흉내 내기 위해 positions_value 프로퍼티를 monkeypatch 하는 대신,
        # positions dict 에 더미 Position 을 직접 추가한다.
        from src.models.position import Position

        dummy = Position(
            market="KRW-DUMMY",
            direction=SignalDirection.LONG,
            entry_price=Decimal("1"),
            current_price=Decimal("1"),
            volume=Decimal(str(positions_value)),
            stop_loss=Decimal("0"),
            take_profit=Decimal("0"),
            strategy_id="dummy",
        )
        portfolio.positions["KRW-DUMMY"] = dummy

    return portfolio


def make_candidate(
    entry: str = "100000",
    stop_loss: str = "95000",
    take_profit: str = "110000",
    direction: SignalDirection = SignalDirection.LONG,
) -> TradeCandidate:
    """테스트용 TradeCandidate 생성."""
    return TradeCandidate(
        market="KRW-BTC",
        direction=direction,
        contributing_signals=[],
        suggested_entry=Decimal(entry),
        suggested_stop_loss=Decimal(stop_loss),
        suggested_take_profit=Decimal(take_profit),
    )


@pytest.fixture
def sizer() -> PositionSizer:
    return PositionSizer(DEFAULT_RISK_CONFIG)


# ---------------------------------------------------------------------------
# 리스크 기반 포지션 산정 (정상 경로)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_risk_based_volume_calculation(sizer):
    """손절 정보가 있으면 리스크 기반으로 수량을 계산한다.

    entry=100_000, stop_loss=95_000 → stop_percent=5%
    risk_amount = 10_000_000 * 0.02 = 200_000
    position_value = 200_000 / 0.05 = 4_000_000
    volume = 4_000_000 / 100_000 = 40
    """
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.volume == Decimal("40.00000000")


@pytest.mark.unit
def test_risk_based_entry_price_propagated(sizer):
    """반환된 Decision 의 entry_price 가 candidate.suggested_entry 와 일치한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.entry_price == Decimal("100000")


@pytest.mark.unit
def test_risk_based_stop_loss_propagated(sizer):
    """반환된 Decision 의 stop_loss 가 candidate.suggested_stop_loss 와 일치한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.stop_loss == Decimal("95000")


@pytest.mark.unit
def test_risk_based_take_profit_propagated(sizer):
    """반환된 Decision 의 take_profit 이 candidate.suggested_take_profit 와 일치한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000", take_profit="110000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.take_profit == Decimal("110000")


# ---------------------------------------------------------------------------
# 단일 포지션 최대 비율 상한
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_position_capped_at_max_position_size(sizer):
    """리스크 기반 포지션 금액이 max_position_size 한도를 초과하면 상한으로 축소된다.

    stop_percent 가 매우 작으면(0.001) position_value 가 커지므로 max_position_size 로 절단된다.
    max_position_value = 10_000_000 * 0.40 = 4_000_000
    volume = 4_000_000 / 100_000 = 40
    """
    portfolio = make_portfolio()
    # stop_loss 가 entry 에 매우 가까워서 stop_percent 가 0.001
    candidate = make_candidate(entry="100000", stop_loss="99900")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.volume == Decimal("40.00000000")


# ---------------------------------------------------------------------------
# 포트폴리오 노출 한도
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_position_capped_by_portfolio_exposure(sizer):
    """이미 보유 포지션으로 잔여 노출 한도가 부족하면 position_value 를 축소한다.

    total_capital=10_000_000, max_exposure=40% → 4_000_000
    existing positions_value=3_500_000 → remaining=500_000
    volume = 500_000 / 100_000 = 5
    """
    portfolio = make_portfolio(positions_value=3_500_000)
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.volume == Decimal("5.00000000")


@pytest.mark.unit
def test_volume_is_zero_when_exposure_limit_reached(sizer):
    """포트폴리오 노출 한도를 이미 초과했으면 volume 이 0 이어야 한다."""
    portfolio = make_portfolio(positions_value=4_000_000)
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.volume == Decimal("0.00000000")


# ---------------------------------------------------------------------------
# 손절 정보 없음 (fallback)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fallback_to_fixed_size_when_no_stop_loss(sizer):
    """손절 가격이 0 이면 max_position_size 고정 비율로 포지션을 결정한다.

    position_value = 10_000_000 * 0.40 = 4_000_000
    volume = 4_000_000 / 100_000 = 40
    """
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="0")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.volume == Decimal("40.00000000")


# ---------------------------------------------------------------------------
# suggested_entry == 0 → current_price 대체
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_current_price_used_when_entry_is_zero(sizer):
    """suggested_entry 가 0 이면 current_price 를 진입 가격으로 사용한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="0", stop_loss="0")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.entry_price == Decimal("100000")


@pytest.mark.unit
def test_volume_computed_from_current_price_when_entry_is_zero(sizer):
    """entry 가 0 일 때 current_price 기준으로 volume 이 계산된다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="0", stop_loss="0")

    decision = sizer.calculate(candidate, portfolio, Decimal("50000"))

    # position_value = 10_000_000 * 0.40 = 4_000_000
    # volume = 4_000_000 / 50_000 = 80
    assert decision.volume == Decimal("80.00000000")


# ---------------------------------------------------------------------------
# entry_price == 0 → volume = 0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_volume_is_zero_when_both_entry_and_current_price_are_zero(sizer):
    """entry 와 current_price 가 모두 0 이면 volume 이 0 이어야 한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="0", stop_loss="0")

    decision = sizer.calculate(candidate, portfolio, Decimal("0"))

    assert decision.volume == Decimal("0")


# ---------------------------------------------------------------------------
# volume 소수점 절사(ROUND_DOWN)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_volume_is_rounded_down(sizer):
    """volume 은 소수점 8자리 이하를 올림 없이 절사한다.

    position_value=4_000_000, entry=3 → 1_333_333.33...
    그러나 max_position_value 와 noexposure 제한 후에도 절사 적용:
    available_capital=100, entry=3, max_position=0.40
    position_value = 100 * 0.40 = 40
    volume = 40 / 3 = 13.33333333... → 13.33333333
    """
    config = RiskLimitsConfig(max_risk_per_trade=0.02, max_position_size=0.40, max_portfolio_exposure=0.40)
    sizer_small = PositionSizer(config)

    portfolio = make_portfolio(total_capital=100, available_capital=100)
    candidate = make_candidate(entry="3", stop_loss="0")

    decision = sizer_small.calculate(candidate, portfolio, Decimal("3"))

    assert decision.volume == Decimal("13.33333333")


# ---------------------------------------------------------------------------
# 리스크 금액·비율
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_risk_amount_is_precise_when_stop_loss_set(sizer):
    """손절 정보가 있을 때 risk_amount = abs(entry - stop_loss) * volume 으로 계산된다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    expected_risk_amount = abs(Decimal("100000") - Decimal("95000")) * decision.volume
    assert decision.risk_amount == expected_risk_amount


@pytest.mark.unit
def test_risk_percent_is_precise_when_stop_loss_set(sizer):
    """손절 정보가 있을 때 risk_percent = risk_amount / total_capital 이다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="95000")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    expected = float(decision.risk_amount / portfolio.total_capital)
    assert decision.risk_percent == pytest.approx(expected)


@pytest.mark.unit
def test_risk_percent_fallback_when_no_stop_loss(sizer):
    """손절 정보가 없으면 risk_percent 는 max_risk_per_trade 와 같다."""
    portfolio = make_portfolio()
    candidate = make_candidate(entry="100000", stop_loss="0")

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.risk_percent == DEFAULT_RISK_CONFIG.max_risk_per_trade


# ---------------------------------------------------------------------------
# Decision 메타데이터
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decision_market_matches_candidate(sizer):
    """반환된 Decision 의 market 이 candidate.market 과 일치한다."""
    portfolio = make_portfolio()
    candidate = make_candidate()

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.market == "KRW-BTC"


@pytest.mark.unit
def test_decision_direction_matches_candidate(sizer):
    """반환된 Decision 의 direction 이 candidate.direction 과 일치한다."""
    portfolio = make_portfolio()
    candidate = make_candidate(direction=SignalDirection.LONG)

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.direction == SignalDirection.LONG


@pytest.mark.unit
def test_decision_state_is_pending(sizer):
    """생성된 Decision 의 초기 state 는 항상 PENDING 이어야 한다."""
    portfolio = make_portfolio()
    candidate = make_candidate()

    decision = sizer.calculate(candidate, portfolio, Decimal("100000"))

    assert decision.state == DecisionState.PENDING

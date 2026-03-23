"""DecisionEngine 단위 테스트."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from src.decision.confluence_checker import ConfluenceChecker
from src.decision.decision_engine import DecisionEngine
from src.models.decision import Decision
from src.models.portfolio_state import PortfolioState
from src.models.position import Position
from src.models.risk_limits_config import RiskLimitsConfig
from src.models.trade_candidate import TradeCandidate
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import DecisionState, SignalDirection

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------

DEFAULT_RISK_CONFIG = RiskLimitsConfig(
    max_risk_per_trade=0.02,
    max_position_size=0.40,
    max_portfolio_exposure=0.40,
)


def make_portfolio(positions: dict | None = None) -> PortfolioState:
    """테스트용 PortfolioState 생성."""
    return PortfolioState(
        total_capital=Decimal("10000000"),
        available_capital=Decimal("10000000"),
        daily_pnl=Decimal("0"),
        weekly_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        high_water_mark=Decimal("10000000"),
        positions=positions or {},
    )


def make_position(market: str = "KRW-BTC") -> Position:
    """테스트용 보유 포지션 생성."""
    return Position(
        market=market,
        direction=SignalDirection.LONG,
        entry_price=Decimal("100000"),
        current_price=Decimal("100000"),
        volume=Decimal("1"),
        stop_loss=Decimal("95000"),
        take_profit=Decimal("110000"),
        strategy_id="test",
    )


def make_candidate(
    market: str = "KRW-BTC",
    suggested_entry: str = "100000",
) -> TradeCandidate:
    """테스트용 TradeCandidate Mock 생성."""
    candidate = MagicMock(spec=TradeCandidate)
    candidate.market = market
    candidate.direction = SignalDirection.LONG
    candidate.suggested_entry = Decimal(suggested_entry)
    candidate.suggested_stop_loss = Decimal("95000")
    candidate.suggested_take_profit = Decimal("110000")
    candidate.contributing_signals = []
    return candidate


def make_decision(market: str = "KRW-BTC", volume: str = "1") -> Decision:
    """테스트용 Decision Mock 생성."""
    decision = MagicMock(spec=Decision)
    decision.market = market
    decision.volume = Decimal(volume)
    decision.state = DecisionState.PENDING
    return decision


@pytest.fixture
def aggregator() -> SignalAggregator:
    return SignalAggregator()


@pytest.fixture
def confluence_checker() -> MagicMock:
    return MagicMock(spec=ConfluenceChecker)


@pytest.fixture
def engine(aggregator, confluence_checker) -> DecisionEngine:
    """confluence_checker 는 Mock, position_sizer 도 생성 후 Mock 으로 교체한다."""
    eng = DecisionEngine(
        risk_config=DEFAULT_RISK_CONFIG,
        aggregator=aggregator,
        confluence_checker=confluence_checker,
    )
    # position_sizer 는 내부 생성이므로 Mock 으로 교체하여 격리
    eng.position_sizer = MagicMock()
    return eng


# ---------------------------------------------------------------------------
# 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_aggregator_is_stored(aggregator, confluence_checker):
    """생성자에서 전달한 aggregator 가 그대로 저장된다."""
    eng = DecisionEngine(DEFAULT_RISK_CONFIG, aggregator, confluence_checker)
    assert eng.aggregator is aggregator


@pytest.mark.unit
def test_confluence_checker_is_stored(aggregator, confluence_checker):
    """생성자에서 전달한 confluence_checker 가 그대로 저장된다."""
    eng = DecisionEngine(DEFAULT_RISK_CONFIG, aggregator, confluence_checker)
    assert eng.confluence_checker is confluence_checker


# ---------------------------------------------------------------------------
# 빈 시그널
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_empty_list_when_no_signals(engine):
    """집계된 시그널이 없으면 빈 Decision 목록을 반환한다."""
    result = engine.process(make_portfolio(), {})
    assert result == []


@pytest.mark.unit
def test_aggregator_cleared_when_no_signals(engine, aggregator):
    """시그널이 없어도 처리 후 aggregator.clear() 가 호출된다."""
    engine.process(make_portfolio(), {})
    # SignalAggregator.clear() 가 실제로 호출되어 내부 상태가 비워졌는지 확인
    assert aggregator.signal_count == 0


# ---------------------------------------------------------------------------
# 이미 보유 포지션 건너뜀
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skips_market_with_existing_position(engine, aggregator, confluence_checker):
    """이미 보유 중인 포지션이 있는 마켓은 컨플루언스 검증 없이 건너뜀."""
    # aggregator 에 KRW-BTC 시그널을 넣되, 포트폴리오에도 KRW-BTC 포지션 보유 중
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    portfolio = make_portfolio(positions={"KRW-BTC": make_position("KRW-BTC")})

    engine.process(portfolio, {"KRW-BTC": Decimal("100000")})

    confluence_checker.check.assert_not_called()


@pytest.mark.unit
def test_returns_empty_when_all_markets_have_positions(engine, aggregator, confluence_checker):
    """모든 마켓에 보유 포지션이 있으면 빈 목록을 반환한다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    aggregator._signals["KRW-ETH"] = [MagicMock()]
    portfolio = make_portfolio(
        positions={
            "KRW-BTC": make_position("KRW-BTC"),
            "KRW-ETH": make_position("KRW-ETH"),
        }
    )

    result = engine.process(portfolio, {})
    assert result == []


# ---------------------------------------------------------------------------
# 컨플루언스 미충족 건너뜀
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skips_when_confluence_returns_none(engine, aggregator, confluence_checker):
    """confluence_checker.check() 가 None 을 반환하면 해당 마켓을 건너뜀."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = None

    result = engine.process(make_portfolio(), {"KRW-BTC": Decimal("100000")})

    assert result == []
    engine.position_sizer.calculate.assert_not_called()


# ---------------------------------------------------------------------------
# 유효 가격 없음 건너뜀
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skips_when_price_is_zero(engine, aggregator, confluence_checker):
    """current_prices 에서 가져온 가격이 0 이면 건너뜀."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = make_candidate(suggested_entry="0")

    result = engine.process(make_portfolio(), {"KRW-BTC": Decimal("0")})

    assert result == []
    engine.position_sizer.calculate.assert_not_called()


@pytest.mark.unit
def test_skips_when_price_is_negative(engine, aggregator, confluence_checker):
    """current_prices 에서 가져온 가격이 음수이면 건너뜀."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = make_candidate(suggested_entry="0")

    result = engine.process(make_portfolio(), {"KRW-BTC": Decimal("-1")})

    assert result == []


@pytest.mark.unit
def test_uses_suggested_entry_as_fallback_price(engine, aggregator, confluence_checker):
    """current_prices 에 마켓이 없으면 candidate.suggested_entry 를 가격으로 사용한다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    candidate = make_candidate(suggested_entry="100000")
    confluence_checker.check.return_value = candidate
    engine.position_sizer.calculate.return_value = make_decision(volume="1")
    portfolio = make_portfolio()  # 동일 인스턴스를 process 와 assert 에 공유

    engine.process(portfolio, {})  # current_prices 에 KRW-BTC 없음

    engine.position_sizer.calculate.assert_called_once_with(candidate, portfolio, Decimal("100000"))


# ---------------------------------------------------------------------------
# volume 0 건너뜀
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_skips_when_volume_is_zero(engine, aggregator, confluence_checker):
    """position_sizer 가 volume=0 인 Decision 을 반환하면 결과에서 제외한다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = make_candidate()
    engine.position_sizer.calculate.return_value = make_decision(volume="0")

    result = engine.process(make_portfolio(), {"KRW-BTC": Decimal("100000")})

    assert result == []


# ---------------------------------------------------------------------------
# 정상 Decision 추가
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_decision_when_all_conditions_met(engine, aggregator, confluence_checker):
    """모든 조건을 충족하면 Decision 이 결과 목록에 포함된다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = make_candidate()
    expected = make_decision(volume="1")
    engine.position_sizer.calculate.return_value = expected

    result = engine.process(make_portfolio(), {"KRW-BTC": Decimal("100000")})

    assert result == [expected]


@pytest.mark.unit
def test_position_sizer_called_with_correct_args(engine, aggregator, confluence_checker):
    """position_sizer.calculate() 가 올바른 인자(candidate, portfolio, price)로 호출된다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    candidate = make_candidate()
    confluence_checker.check.return_value = candidate
    engine.position_sizer.calculate.return_value = make_decision(volume="1")
    portfolio = make_portfolio()

    engine.process(portfolio, {"KRW-BTC": Decimal("100000")})

    engine.position_sizer.calculate.assert_called_once_with(candidate, portfolio, Decimal("100000"))


# ---------------------------------------------------------------------------
# 여러 마켓 처리
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_processes_multiple_markets(engine, aggregator, confluence_checker):
    """여러 마켓을 순회하며 각각 독립적으로 처리한다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    aggregator._signals["KRW-ETH"] = [MagicMock()]
    confluence_checker.check.return_value = make_candidate()
    engine.position_sizer.calculate.side_effect = [
        make_decision(market="KRW-BTC", volume="1"),
        make_decision(market="KRW-ETH", volume="2"),
    ]

    result = engine.process(
        make_portfolio(),
        {
            "KRW-BTC": Decimal("100000"),
            "KRW-ETH": Decimal("50000"),
        },
    )

    assert len(result) == 2


@pytest.mark.unit
def test_partial_markets_skipped(engine, aggregator, confluence_checker):
    """일부 마켓은 통과, 일부는 컨플루언스 미충족으로 건너뛸 때 통과한 것만 반환된다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    aggregator._signals["KRW-ETH"] = [MagicMock()]

    # KRW-BTC 는 통과, KRW-ETH 는 컨플루언스 미충족
    def side_effect(signals):
        signal = signals[0]
        if hasattr(signal, "market") and signal.market == "KRW-ETH":
            return None
        return make_candidate()

    # 시그널에 market 속성 주입
    btc_signal = MagicMock()
    btc_signal.market = "KRW-BTC"
    eth_signal = MagicMock()
    eth_signal.market = "KRW-ETH"
    aggregator._signals["KRW-BTC"] = [btc_signal]
    aggregator._signals["KRW-ETH"] = [eth_signal]
    confluence_checker.check.side_effect = [make_candidate(), None]
    engine.position_sizer.calculate.return_value = make_decision(volume="1")

    result = engine.process(
        make_portfolio(),
        {
            "KRW-BTC": Decimal("100000"),
            "KRW-ETH": Decimal("50000"),
        },
    )

    assert len(result) == 1


# ---------------------------------------------------------------------------
# 집계기 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_aggregator_cleared_after_processing(engine, aggregator, confluence_checker):
    """처리 완료 후 aggregator 가 초기화되어 시그널이 비워진다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = None

    engine.process(make_portfolio(), {})

    assert aggregator.signal_count == 0


@pytest.mark.unit
def test_aggregator_cleared_even_when_no_decisions(engine, aggregator, confluence_checker):
    """Decision 이 하나도 생성되지 않아도 aggregator 는 초기화된다."""
    aggregator._signals["KRW-BTC"] = [MagicMock()]
    confluence_checker.check.return_value = None

    engine.process(make_portfolio(), {})

    assert len(aggregator._signals) == 0

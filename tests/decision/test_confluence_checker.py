"""ConfluenceChecker 단위 테스트."""

from decimal import Decimal

import pytest
from src.decision.confluence_checker import ConfluenceChecker
from src.models.signal import Signal
from src.models.trade_candidate import TradeCandidate
from src.utils.constants import MarketRegime, SignalDirection, SignalType, SignalValue

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_signal(
    direction: SignalDirection = SignalDirection.LONG,
    market: str = "KRW-BTC",
    entry_price: str = "100000",
    stop_loss: str = "95000",
    take_profit: str = "110000",
) -> Signal:
    """테스트용 Signal 객체를 생성한다.

    confluence_checker.py 가 Signal 에 없는 entry_price / stop_loss /
    take_profit / symbol 필드를 직접 참조하므로, 생성 후 동적으로 주입한다.
    """
    sig = Signal(
        strategy_id="test_strategy",
        indicator_id="macd_rsi",
        type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=direction,
        regime=MarketRegime.STABLE_BULL,
        market=market,
        timeframe="1m",
    )
    # Signal 모델에 없는 가격 필드를 동적으로 주입
    sig.entry_price = Decimal(entry_price)
    sig.stop_loss = Decimal(stop_loss)
    sig.take_profit = Decimal(take_profit)
    # confluence_checker.py 가 best_signals[0].symbol 을 참조하므로 주입
    sig.symbol = market
    return sig


@pytest.fixture
def checker() -> ConfluenceChecker:
    """min_signals=3 으로 설정한 ConfluenceChecker 픽스처."""
    return ConfluenceChecker(min_signals=3)


# ---------------------------------------------------------------------------
# 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_min_signals():
    """기본 min_signals 는 6이어야 한다."""
    assert ConfluenceChecker().min_signals == 6


@pytest.mark.unit
def test_custom_min_signals():
    """생성자에 전달한 min_signals 가 그대로 저장된다."""
    assert ConfluenceChecker(min_signals=3).min_signals == 3


# ---------------------------------------------------------------------------
# 조기 종료 — 시그널 수 부족
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_for_empty_signals(checker):
    """시그널 목록이 비어 있으면 None 을 반환한다."""
    assert checker.check([]) is None


@pytest.mark.unit
def test_returns_none_when_signals_below_min(checker):
    """시그널 수가 min_signals 미만이면 None 을 반환한다."""
    signals = [make_signal() for _ in range(2)]  # min_signals=3 인데 2개
    assert checker.check(signals) is None


@pytest.mark.unit
def test_returns_none_exactly_at_min_minus_one(checker):
    """시그널 수가 min_signals - 1 이면 None 을 반환한다."""
    signals = [make_signal() for _ in range(checker.min_signals - 1)]
    assert checker.check(signals) is None


# ---------------------------------------------------------------------------
# 조기 종료 — 방향 기준 미충족
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_none_when_all_signals_are_hold(checker):
    """모든 시그널이 HOLD 방향이면 None 을 반환한다."""
    signals = [make_signal(direction=SignalDirection.HOLD) for _ in range(5)]
    assert checker.check(signals) is None


@pytest.mark.unit
def test_returns_none_when_directions_are_split_below_min(checker):
    """LONG 과 SHORT 가 분산되어 어느 쪽도 min_signals 에 못 미치면 None 을 반환한다."""
    # LONG 2개 + SHORT 2개 = 4개 (>= min 3 통과), 하지만 각 방향은 2개 < 3
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(2)]
    signals += [make_signal(direction=SignalDirection.SHORT) for _ in range(2)]
    assert checker.check(signals) is None


@pytest.mark.unit
def test_returns_none_when_non_hold_direction_below_min_after_excluding_hold(checker):
    """HOLD 제외 후 유효 방향 시그널이 min_signals 미만이면 None 을 반환한다."""
    # LONG 2개 + HOLD 3개 → LONG 2 < min 3
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(2)]
    signals += [make_signal(direction=SignalDirection.HOLD) for _ in range(3)]
    assert checker.check(signals) is None


# ---------------------------------------------------------------------------
# 정상 경로 — TradeCandidate 반환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_returns_trade_candidate_when_confluence_met(checker):
    """조건을 충족하면 TradeCandidate 를 반환한다."""
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(3)]
    result = checker.check(signals)
    assert isinstance(result, TradeCandidate)


@pytest.mark.unit
def test_direction_matches_majority(checker):
    """반환된 TradeCandidate 의 direction 이 다수결 방향과 일치한다."""
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(3)]
    result = checker.check(signals)
    assert result.direction == SignalDirection.LONG


@pytest.mark.unit
def test_selects_direction_with_most_signals(checker):
    """LONG 3개 vs SHORT 4개일 때 SHORT 방향이 채택된다."""
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(3)]
    signals += [make_signal(direction=SignalDirection.SHORT) for _ in range(4)]
    result = checker.check(signals)
    assert result.direction == SignalDirection.SHORT


@pytest.mark.unit
def test_hold_signals_do_not_affect_direction_selection(checker):
    """HOLD 시그널이 섞여 있어도 유효 방향 선택에 영향을 주지 않는다."""
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(3)]
    signals += [make_signal(direction=SignalDirection.HOLD) for _ in range(10)]
    result = checker.check(signals)
    assert result.direction == SignalDirection.LONG


@pytest.mark.unit
def test_market_is_taken_from_first_best_signal(checker):
    """반환된 TradeCandidate 의 market 이 best_signals 첫 번째 시그널과 일치한다."""
    signals = [make_signal(direction=SignalDirection.LONG, market="KRW-ETH") for _ in range(3)]
    result = checker.check(signals)
    assert result.market == "KRW-ETH"


@pytest.mark.unit
def test_contributing_signals_are_best_signals(checker):
    """반환된 TradeCandidate 의 contributing_signals 가 채택된 시그널 목록과 일치한다."""
    signals = [make_signal(direction=SignalDirection.LONG) for _ in range(3)]
    result = checker.check(signals)
    assert result.contributing_signals == signals


# ---------------------------------------------------------------------------
# 가격 계산
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_suggested_entry_is_average_of_entry_prices(checker):
    """suggested_entry 는 채택된 시그널 entry_price 들의 평균이다."""
    prices = ["100000", "200000", "300000"]
    signals = [make_signal(direction=SignalDirection.LONG, entry_price=p) for p in prices]
    result = checker.check(signals)
    expected = (Decimal("100000") + Decimal("200000") + Decimal("300000")) / 3
    assert result.suggested_entry == expected


@pytest.mark.unit
def test_suggested_stop_loss_is_minimum(checker):
    """suggested_stop_loss 는 채택된 시그널 stop_loss 들 중 가장 낮은 값이다."""
    stops = ["95000", "90000", "85000"]
    signals = [make_signal(direction=SignalDirection.LONG, stop_loss=s) for s in stops]
    result = checker.check(signals)
    assert result.suggested_stop_loss == Decimal("85000")


@pytest.mark.unit
def test_suggested_take_profit_is_maximum(checker):
    """suggested_take_profit 는 채택된 시그널 take_profit 들 중 가장 높은 값이다."""
    tps = ["110000", "120000", "115000"]
    signals = [make_signal(direction=SignalDirection.LONG, take_profit=tp) for tp in tps]
    result = checker.check(signals)
    assert result.suggested_take_profit == Decimal("120000")


@pytest.mark.unit
def test_suggested_entry_is_zero_when_all_entry_prices_are_zero(checker):
    """모든 시그널의 entry_price 가 0 이면 suggested_entry 는 0 이다."""
    signals = [make_signal(direction=SignalDirection.LONG, entry_price="0") for _ in range(3)]
    result = checker.check(signals)
    assert result.suggested_entry == Decimal("0")


@pytest.mark.unit
def test_suggested_stop_is_zero_when_all_stop_losses_are_zero(checker):
    """모든 시그널의 stop_loss 가 0 이면 suggested_stop_loss 는 0 이다."""
    signals = [make_signal(direction=SignalDirection.LONG, stop_loss="0") for _ in range(3)]
    result = checker.check(signals)
    assert result.suggested_stop_loss == Decimal("0")


@pytest.mark.unit
def test_suggested_tp_is_zero_when_all_take_profits_are_zero(checker):
    """모든 시그널의 take_profit 이 0 이면 suggested_take_profit 은 0 이다."""
    signals = [make_signal(direction=SignalDirection.LONG, take_profit="0") for _ in range(3)]
    result = checker.check(signals)
    assert result.suggested_take_profit == Decimal("0")

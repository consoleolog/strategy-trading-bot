"""SignalAggregator 단위 테스트."""

import pytest
from src.models.signal import Signal
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import SignalDirection, SignalType, SignalValue

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_signal(
    market: str = "KRW-BTC",
    strategy_id: str = "strategy-1",
    direction: SignalDirection = SignalDirection.LONG,
) -> Signal:
    """테스트용 Signal 객체를 생성한다."""
    return Signal(
        strategy_id=strategy_id,
        indicator_id="indicator-1",
        type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=direction,
        market=market,
        timeframe="1h",
    )


# ---------------------------------------------------------------------------
# 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_initial_state_is_empty():
    """초기 상태에서 시그널이 없어야 한다."""
    aggregator = SignalAggregator()
    assert aggregator.get_all_signals() == {}


@pytest.mark.unit
def test_initial_signal_count_is_zero():
    """초기 상태에서 signal_count는 0이어야 한다."""
    aggregator = SignalAggregator()
    assert aggregator.signal_count == 0


# ---------------------------------------------------------------------------
# add_signal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_add_signal_stores_signal():
    """add_signal() 후 해당 마켓에 시그널이 저장된다."""
    aggregator = SignalAggregator()
    signal = _make_signal(market="KRW-BTC")

    aggregator.add_signal(signal)

    assert aggregator.get_signals("KRW-BTC") == [signal]


@pytest.mark.unit
def test_add_multiple_signals_same_market():
    """동일 마켓에 여러 시그널을 추가하면 순서대로 누적된다."""
    aggregator = SignalAggregator()
    s1 = _make_signal(market="KRW-BTC", strategy_id="strategy-1")
    s2 = _make_signal(market="KRW-BTC", strategy_id="strategy-2")

    aggregator.add_signal(s1)
    aggregator.add_signal(s2)

    assert aggregator.get_signals("KRW-BTC") == [s1, s2]


@pytest.mark.unit
def test_add_signals_different_markets():
    """서로 다른 마켓의 시그널은 각각 독립적으로 저장된다."""
    aggregator = SignalAggregator()
    btc = _make_signal(market="KRW-BTC")
    eth = _make_signal(market="KRW-ETH")

    aggregator.add_signal(btc)
    aggregator.add_signal(eth)

    assert aggregator.get_signals("KRW-BTC") == [btc]
    assert aggregator.get_signals("KRW-ETH") == [eth]


# ---------------------------------------------------------------------------
# get_signals
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_signals_returns_empty_list_for_unknown_market():
    """등록되지 않은 마켓 조회 시 빈 리스트를 반환한다."""
    aggregator = SignalAggregator()
    assert aggregator.get_signals("KRW-XRP") == []


@pytest.mark.unit
def test_get_signals_does_not_mutate_internal_state():
    """get_signals()가 반환한 리스트를 수정해도 내부 상태에 영향을 주지 않는다."""
    aggregator = SignalAggregator()
    aggregator.add_signal(_make_signal(market="KRW-BTC"))

    result = aggregator.get_signals("KRW-BTC")
    result.clear()

    assert len(aggregator.get_signals("KRW-BTC")) == 1


# ---------------------------------------------------------------------------
# get_all_signals
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_all_signals_returns_all_markets():
    """get_all_signals()는 추가된 모든 마켓의 시그널을 반환한다."""
    aggregator = SignalAggregator()
    aggregator.add_signal(_make_signal(market="KRW-BTC"))
    aggregator.add_signal(_make_signal(market="KRW-ETH"))

    all_signals = aggregator.get_all_signals()

    assert set(all_signals.keys()) == {"KRW-BTC", "KRW-ETH"}


# ---------------------------------------------------------------------------
# signal_count
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_signal_count_increases_per_signal():
    """시그널을 추가할 때마다 signal_count가 1씩 증가한다."""
    aggregator = SignalAggregator()

    aggregator.add_signal(_make_signal(market="KRW-BTC"))
    assert aggregator.signal_count == 1

    aggregator.add_signal(_make_signal(market="KRW-BTC"))
    assert aggregator.signal_count == 2

    aggregator.add_signal(_make_signal(market="KRW-ETH"))
    assert aggregator.signal_count == 3


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clear_removes_all_signals():
    """clear() 후 모든 시그널이 제거된다."""
    aggregator = SignalAggregator()
    aggregator.add_signal(_make_signal(market="KRW-BTC"))
    aggregator.add_signal(_make_signal(market="KRW-ETH"))

    aggregator.clear()

    assert aggregator.get_all_signals() == {}
    assert aggregator.signal_count == 0


@pytest.mark.unit
def test_clear_then_add_signal_works():
    """clear() 이후 다시 시그널을 추가할 수 있다."""
    aggregator = SignalAggregator()
    aggregator.add_signal(_make_signal(market="KRW-BTC"))
    aggregator.clear()

    signal = _make_signal(market="KRW-ETH")
    aggregator.add_signal(signal)

    assert aggregator.get_signals("KRW-ETH") == [signal]
    assert aggregator.signal_count == 1

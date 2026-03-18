"""MacdRsiStochasticStrategy 단위 테스트."""

from unittest.mock import MagicMock

import pytest
from src.repositories.signal_repository import SignalRepository
from src.strategies.macd_rsi_stochastic import MacdRsiStochasticStrategy
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import MarketRegime

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_strategy(config: dict | None = None) -> MacdRsiStochasticStrategy:
    return MacdRsiStochasticStrategy(
        config=config or {},
        aggregator=MagicMock(spec=SignalAggregator),
        signal_repository=MagicMock(spec=SignalRepository),
    )


# ---------------------------------------------------------------------------
# __init__ — 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_macd_periods():
    """MACD 관련 파라미터가 기본값으로 초기화된다."""
    strategy = _make_strategy()
    assert strategy.macd_upper_period == 3
    assert strategy.macd_mid_period == 5
    assert strategy.macd_lower_period == 8
    assert strategy.macd_signal_period == 9


@pytest.mark.unit
def test_default_rsi_params():
    """RSI 관련 파라미터가 기본값으로 초기화된다."""
    strategy = _make_strategy()
    assert strategy.rsi_period == 14
    assert strategy.rsi_signal_period == 9
    assert strategy.rsi_overbought == 75
    assert strategy.rsi_oversold == 25


@pytest.mark.unit
def test_default_stoch_params():
    """Stochastic 관련 파라미터가 기본값으로 초기화된다."""
    strategy = _make_strategy()
    assert strategy.stoch_k_len == 10
    assert strategy.stoch_k_smooth == 3
    assert strategy.stoch_d_smooth == 3
    assert strategy.stoch_overbought == 80
    assert strategy.stoch_oversold == 20


# ---------------------------------------------------------------------------
# __init__ — config 오버라이드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_config_overrides_macd_periods():
    """config에 명시된 MACD 파라미터가 기본값을 덮어쓴다."""
    strategy = _make_strategy(
        {
            "macd_upper_period": 6,
            "macd_mid_period": 13,
            "macd_lower_period": 26,
            "macd_signal_period": 5,
        }
    )
    assert strategy.macd_upper_period == 6
    assert strategy.macd_mid_period == 13
    assert strategy.macd_lower_period == 26
    assert strategy.macd_signal_period == 5


@pytest.mark.unit
def test_config_overrides_rsi_params():
    """config에 명시된 RSI 파라미터가 기본값을 덮어쓴다."""
    strategy = _make_strategy(
        {
            "rsi_period": 7,
            "rsi_signal_period": 4,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
        }
    )
    assert strategy.rsi_period == 7
    assert strategy.rsi_signal_period == 4
    assert strategy.rsi_overbought == 70
    assert strategy.rsi_oversold == 30


@pytest.mark.unit
def test_config_overrides_stoch_params():
    """config에 명시된 Stochastic 파라미터가 기본값을 덮어쓴다."""
    strategy = _make_strategy(
        {
            "stoch_k_len": 14,
            "stoch_k_smooth": 5,
            "stoch_d_smooth": 5,
            "stoch_overbought": 85,
            "stoch_oversold": 15,
        }
    )
    assert strategy.stoch_k_len == 14
    assert strategy.stoch_k_smooth == 5
    assert strategy.stoch_d_smooth == 5
    assert strategy.stoch_overbought == 85
    assert strategy.stoch_oversold == 15


# ---------------------------------------------------------------------------
# get_supported_regimes
# ---------------------------------------------------------------------------


_SUPPORTED_REGIMES = {
    MarketRegime.STABLE_BULL,
    MarketRegime.END_OF_BULL,
    MarketRegime.START_OF_BEAR,
    MarketRegime.STABLE_BEAR,
    MarketRegime.END_OF_BEAR,
    MarketRegime.START_OF_BULL,
}


@pytest.mark.unit
def test_get_supported_regimes_contains_all_active_regimes():
    """get_supported_regimes()가 UNKNOWN을 제외한 모든 국면을 반환한다."""
    strategy = _make_strategy()
    assert set(strategy.get_supported_regimes()) == _SUPPORTED_REGIMES


@pytest.mark.unit
def test_get_supported_regimes_excludes_unknown():
    """get_supported_regimes()에 UNKNOWN 국면이 포함되지 않는다."""
    strategy = _make_strategy()
    assert MarketRegime.UNKNOWN not in strategy.get_supported_regimes()


@pytest.mark.unit
def test_should_run_true_for_supported_regimes():
    """should_run()이 지원 국면에서 True를 반환한다."""
    strategy = _make_strategy()
    for regime in _SUPPORTED_REGIMES:
        assert strategy.should_run(regime) is True


@pytest.mark.unit
def test_should_run_false_for_unknown():
    """should_run()이 UNKNOWN 국면에서 False를 반환한다."""
    strategy = _make_strategy()
    assert strategy.should_run(MarketRegime.UNKNOWN) is False


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_evaluate_returns_none():
    """evaluate()가 현재 None을 반환한다 (미구현)."""
    strategy = _make_strategy()
    result = await strategy.evaluate(candles=[], regime=MarketRegime.STABLE_BULL, portfolio=MagicMock())
    assert result is None

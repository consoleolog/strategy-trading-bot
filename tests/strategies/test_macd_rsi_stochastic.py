"""MacdRsiStochasticStrategy 단위 테스트."""

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from src.repositories.signal_repository import SignalRepository
from src.strategies.macd_rsi_stochastic import MacdRsiStochasticStrategy
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import CandleType, MarketRegime

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_strategy(config: dict | None = None) -> MacdRsiStochasticStrategy:
    return MacdRsiStochasticStrategy(
        config=config or {},
        aggregator=MagicMock(spec=SignalAggregator),
        signal_repository=MagicMock(spec=SignalRepository),
    )


def _make_candle(code: str = "KRW-BTC", candle_type: CandleType = CandleType.MINUTE_1) -> MagicMock:
    candle = MagicMock()
    candle.code = code
    candle.type = candle_type
    return candle


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
# setup_macd
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_setup_macd_returns_three_band_keys(mocker):
    """setup_macd()가 upper/mid/lower 키를 가진 딕셔너리를 반환한다."""
    strategy = _make_strategy()
    empty_macd = {"macd": np.array([]), "signal": np.array([]), "histogram": np.array([])}
    mocker.patch.object(MacdRsiStochasticStrategy, "calculate_macd", return_value=empty_macd)

    result = strategy.setup_macd([])

    assert set(result.keys()) == {"upper", "mid", "lower"}


@pytest.mark.unit
def test_setup_macd_calls_calculate_macd_three_times(mocker):
    """setup_macd()가 calculate_macd를 세 번 호출한다."""
    strategy = _make_strategy()
    empty_macd = {"macd": np.array([]), "signal": np.array([]), "histogram": np.array([])}
    mock_calc = mocker.patch.object(MacdRsiStochasticStrategy, "calculate_macd", return_value=empty_macd)

    strategy.setup_macd([])

    assert mock_calc.call_count == 3


@pytest.mark.unit
def test_setup_macd_uses_correct_period_combinations(mocker):
    """upper/mid/lower 밴드가 올바른 fast/slow 기간 조합으로 계산된다."""
    strategy = _make_strategy()
    calls = []

    def side_effect(candles, fast_period, slow_period, signal_period):
        calls.append((fast_period, slow_period))
        return {"macd": np.array([]), "signal": np.array([]), "histogram": np.array([])}

    mocker.patch.object(MacdRsiStochasticStrategy, "calculate_macd", side_effect=side_effect)
    strategy.setup_macd([])

    # upper: (upper, mid), mid: (upper, lower), lower: (mid, lower)
    assert calls[0] == (3, 5)
    assert calls[1] == (3, 8)
    assert calls[2] == (5, 8)


# ---------------------------------------------------------------------------
# update_macd
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_update_macd_adds_non_none_signals_to_aggregator(mocker):
    """교차 신호가 발생하면 aggregator.add_signal()을 밴드당 한 번씩 호출한다."""
    strategy = _make_strategy()
    mock_signal = MagicMock()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=mock_signal))

    macds = {
        "upper": {"macd": np.array([]), "signal": np.array([])},
        "mid": {"macd": np.array([]), "signal": np.array([])},
        "lower": {"macd": np.array([]), "signal": np.array([])},
    }
    await strategy.update_macd(macds, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    assert strategy.aggregator.add_signal.call_count == 3


@pytest.mark.unit
async def test_update_macd_skips_none_signals(mocker):
    """교차 신호가 None이면 aggregator.add_signal()을 호출하지 않는다."""
    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))

    macds = {
        "upper": {"macd": np.array([]), "signal": np.array([])},
        "mid": {"macd": np.array([]), "signal": np.array([])},
        "lower": {"macd": np.array([]), "signal": np.array([])},
    }
    await strategy.update_macd(macds, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    strategy.aggregator.add_signal.assert_not_called()


@pytest.mark.unit
async def test_update_macd_returns_dict_with_correct_keys(mocker):
    """update_macd()가 upper/mid/lower 키를 가진 딕셔너리를 반환한다."""
    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))

    macds = {
        "upper": {"macd": np.array([]), "signal": np.array([])},
        "mid": {"macd": np.array([]), "signal": np.array([])},
        "lower": {"macd": np.array([]), "signal": np.array([])},
    }
    result = await strategy.update_macd(macds, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    assert set(result.keys()) == {"upper", "mid", "lower"}


@pytest.mark.unit
async def test_update_macd_passes_indicator_ids(mocker):
    """각 밴드에 macd_upper/macd_mid/macd_lower indicator_id가 전달된다."""
    strategy = _make_strategy()
    indicator_ids = []

    async def capture(*args, indicator_id, **kwargs):
        indicator_ids.append(indicator_id)
        return None

    mocker.patch.object(strategy, "check_crossover", side_effect=capture)

    macds = {
        "upper": {"macd": np.array([]), "signal": np.array([])},
        "mid": {"macd": np.array([]), "signal": np.array([])},
        "lower": {"macd": np.array([]), "signal": np.array([])},
    }
    await strategy.update_macd(macds, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    assert indicator_ids == ["macd_upper", "macd_mid", "macd_lower"]


# ---------------------------------------------------------------------------
# setup_rsi
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_setup_rsi_returns_rsi_and_signal_keys(mocker):
    """setup_rsi()가 rsi와 signal 키를 가진 딕셔너리를 반환한다."""
    strategy = _make_strategy()
    rsi_values = np.array([50.0, 55.0, 60.0])
    mocker.patch.object(MacdRsiStochasticStrategy, "calculate_rsi", return_value=rsi_values)
    mocker.patch("src.strategies.macd_rsi_stochastic.talib.EMA", return_value=np.array([52.0, 55.0, 58.0]))

    result = strategy.setup_rsi([])

    assert set(result.keys()) == {"rsi", "signal"}
    np.testing.assert_array_equal(result["rsi"], rsi_values)


@pytest.mark.unit
def test_setup_rsi_uses_rsi_period(mocker):
    """setup_rsi()가 rsi_period로 calculate_rsi를 호출한다."""
    strategy = _make_strategy({"rsi_period": 7})
    mock_rsi = mocker.patch.object(MacdRsiStochasticStrategy, "calculate_rsi", return_value=np.array([50.0]))
    mocker.patch("src.strategies.macd_rsi_stochastic.talib.EMA", return_value=np.array([50.0]))

    strategy.setup_rsi([])

    mock_rsi.assert_called_once_with([], 7)


@pytest.mark.unit
def test_setup_rsi_signal_is_ema_of_rsi(mocker):
    """setup_rsi()의 signal은 rsi에 EMA를 적용한 값이다."""
    strategy = _make_strategy({"rsi_signal_period": 4})
    rsi_values = np.array([50.0, 55.0, 60.0])
    signal_values = np.array([52.0, 54.0, 57.0])
    mocker.patch.object(MacdRsiStochasticStrategy, "calculate_rsi", return_value=rsi_values)
    mock_ema = mocker.patch("src.strategies.macd_rsi_stochastic.talib.EMA", return_value=signal_values)

    result = strategy.setup_rsi([])

    mock_ema.assert_called_once_with(rsi_values, 4)
    np.testing.assert_array_equal(result["signal"], signal_values)


# ---------------------------------------------------------------------------
# update_rsi
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_update_rsi_uses_rsi_key_for_crossover(mocker):
    """update_rsi()가 check_crossover에 'rsi' 키의 값을 전달한다."""
    strategy = _make_strategy()
    rsi_values = np.array([40.0, 60.0])
    signal_values = np.array([50.0, 50.0])
    captured = []

    async def capture(one, two, **kwargs):
        captured.append((list(one), list(two)))
        return None

    mocker.patch.object(strategy, "check_crossover", side_effect=capture)
    mocker.patch.object(strategy, "check_level_break", new=AsyncMock(return_value=None))

    await strategy.update_rsi(
        {"rsi": rsi_values, "signal": signal_values},
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        regime=MarketRegime.STABLE_BULL,
    )

    assert captured[0] == ([40.0, 60.0], [50.0, 50.0])


@pytest.mark.unit
async def test_update_rsi_uses_rsi_key_for_level_break(mocker):
    """update_rsi()가 check_level_break에 'rsi' 키의 마지막 값을 전달한다."""
    from decimal import Decimal

    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))
    captured_values = []

    async def capture(value, **kwargs):
        captured_values.append(value)
        return None

    mocker.patch.object(strategy, "check_level_break", side_effect=capture)

    await strategy.update_rsi(
        {"rsi": np.array([30.0, 55.0, 80.0]), "signal": np.array([50.0, 52.0, 54.0])},
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        regime=MarketRegime.STABLE_BULL,
    )

    assert captured_values[0] == Decimal("80.0")


@pytest.mark.unit
async def test_update_rsi_returns_dict_with_correct_keys(mocker):
    """update_rsi()가 crossover/level_break 키를 가진 딕셔너리를 반환한다."""
    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))
    mocker.patch.object(strategy, "check_level_break", new=AsyncMock(return_value=None))

    result = await strategy.update_rsi(
        {"rsi": np.array([50.0]), "signal": np.array([50.0])},
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        regime=MarketRegime.STABLE_BULL,
    )

    assert set(result.keys()) == {"crossover", "level_break"}


@pytest.mark.unit
async def test_update_rsi_passes_correct_indicator_id(mocker):
    """check_crossover와 check_level_break에 'rsi' indicator_id가 전달된다."""
    strategy = _make_strategy()
    crossover_ids = []
    level_break_ids = []

    async def capture_crossover(*args, indicator_id, **kwargs):
        crossover_ids.append(indicator_id)
        return None

    async def capture_level_break(*args, indicator_id, **kwargs):
        level_break_ids.append(indicator_id)
        return None

    mocker.patch.object(strategy, "check_crossover", side_effect=capture_crossover)
    mocker.patch.object(strategy, "check_level_break", side_effect=capture_level_break)

    await strategy.update_rsi(
        {"rsi": np.array([50.0]), "signal": np.array([50.0])},
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        regime=MarketRegime.STABLE_BULL,
    )

    assert crossover_ids == ["rsi"]
    assert level_break_ids == ["rsi"]


# ---------------------------------------------------------------------------
# setup_stoch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_setup_stoch_returns_k_slow_and_d_slow_keys(mocker):
    """setup_stoch()가 k_slow와 d_slow 키를 가진 딕셔너리를 반환한다."""
    strategy = _make_strategy()
    expected = {"k_slow": np.array([50.0]), "d_slow": np.array([48.0])}
    mocker.patch.object(MacdRsiStochasticStrategy, "calculate_stoch", return_value=expected)

    result = strategy.setup_stoch([])

    assert set(result.keys()) == {"k_slow", "d_slow"}


@pytest.mark.unit
def test_setup_stoch_uses_stoch_params(mocker):
    """setup_stoch()가 stoch_k_len/k_smooth/d_smooth 파라미터로 calculate_stoch를 호출한다."""
    strategy = _make_strategy({"stoch_k_len": 14, "stoch_k_smooth": 5, "stoch_d_smooth": 5})
    mock_stoch = mocker.patch.object(
        MacdRsiStochasticStrategy,
        "calculate_stoch",
        return_value={"k_slow": np.array([]), "d_slow": np.array([])},
    )

    strategy.setup_stoch([])

    mock_stoch.assert_called_once_with([], k_len=14, k_smooth=5, d_smooth=5)


# ---------------------------------------------------------------------------
# update_stoch
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_update_stoch_adds_crossover_signal_to_aggregator(mocker):
    """스토캐스틱 교차 신호가 발생하면 aggregator.add_signal()을 호출한다."""
    strategy = _make_strategy()
    mock_signal = MagicMock()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=mock_signal))
    mocker.patch.object(strategy, "check_level_break", new=AsyncMock(return_value=None))

    stoch = {"k_slow": np.array([20.0, 25.0]), "d_slow": np.array([22.0, 22.0])}
    await strategy.update_stoch(stoch, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    strategy.aggregator.add_signal.assert_any_call(mock_signal)


@pytest.mark.unit
async def test_update_stoch_adds_level_break_signals_to_aggregator(mocker):
    """레벨 돌파 신호가 발생하면 k_slow/d_slow 각각 aggregator.add_signal()을 호출한다."""
    strategy = _make_strategy()
    mock_signal = MagicMock()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))
    mocker.patch.object(strategy, "check_level_break", new=AsyncMock(return_value=mock_signal))

    stoch = {"k_slow": np.array([85.0]), "d_slow": np.array([82.0])}
    await strategy.update_stoch(stoch, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    assert strategy.aggregator.add_signal.call_count == 2


@pytest.mark.unit
async def test_update_stoch_skips_none_signals(mocker):
    """모든 신호가 None이면 aggregator.add_signal()을 호출하지 않는다."""
    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))
    mocker.patch.object(strategy, "check_level_break", new=AsyncMock(return_value=None))

    stoch = {"k_slow": np.array([50.0]), "d_slow": np.array([50.0])}
    await strategy.update_stoch(stoch, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    strategy.aggregator.add_signal.assert_not_called()


@pytest.mark.unit
async def test_update_stoch_passes_correct_indicator_ids(mocker):
    """check_level_break에 stoch_k_slow/stoch_d_slow indicator_id가 전달된다."""
    strategy = _make_strategy()
    mocker.patch.object(strategy, "check_crossover", new=AsyncMock(return_value=None))
    indicator_ids = []

    async def capture(*args, indicator_id, **kwargs):
        indicator_ids.append(indicator_id)
        return None

    mocker.patch.object(strategy, "check_level_break", side_effect=capture)

    stoch = {"k_slow": np.array([50.0]), "d_slow": np.array([50.0])}
    await strategy.update_stoch(stoch, "KRW-BTC", CandleType.MINUTE_1, MarketRegime.STABLE_BULL)

    assert indicator_ids == ["stoch_k_slow", "stoch_d_slow"]


# ---------------------------------------------------------------------------
# evaluate
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_evaluate_returns_none(mocker):
    """evaluate()는 None을 반환한다."""
    strategy = _make_strategy()
    candle = _make_candle()
    mocker.patch.object(strategy, "setup_macd", return_value={"upper": {}, "mid": {}, "lower": {}})
    mocker.patch.object(strategy, "update_macd", new=AsyncMock())
    mocker.patch.object(strategy, "setup_rsi", return_value={"rsi": np.array([]), "signal": np.array([])})
    mocker.patch.object(strategy, "update_rsi", new=AsyncMock())
    mocker.patch.object(strategy, "setup_stoch", return_value={"k_slow": np.array([]), "d_slow": np.array([])})
    mocker.patch.object(strategy, "update_stoch", new=AsyncMock())

    result = await strategy.evaluate(candles=[candle], regime=MarketRegime.STABLE_BULL, portfolio=MagicMock())

    assert result is None


@pytest.mark.unit
async def test_evaluate_calls_all_setup_and_update_methods(mocker):
    """evaluate()가 MACD·RSI·스토캐스틱 setup/update를 모두 호출한다."""
    strategy = _make_strategy()
    candle = _make_candle()

    mock_setup_macd = mocker.patch.object(strategy, "setup_macd", return_value={"upper": {}, "mid": {}, "lower": {}})
    mock_update_macd = mocker.patch.object(strategy, "update_macd", new=AsyncMock())
    mock_setup_rsi = mocker.patch.object(
        strategy, "setup_rsi", return_value={"rsi": np.array([]), "signal": np.array([])}
    )
    mock_update_rsi = mocker.patch.object(strategy, "update_rsi", new=AsyncMock())
    mock_setup_stoch = mocker.patch.object(
        strategy, "setup_stoch", return_value={"k_slow": np.array([]), "d_slow": np.array([])}
    )
    mock_update_stoch = mocker.patch.object(strategy, "update_stoch", new=AsyncMock())

    await strategy.evaluate(candles=[candle], regime=MarketRegime.STABLE_BULL, portfolio=MagicMock())

    mock_setup_macd.assert_called_once_with([candle])
    mock_update_macd.assert_called_once()
    mock_setup_rsi.assert_called_once_with([candle])
    mock_update_rsi.assert_called_once()
    mock_setup_stoch.assert_called_once_with([candle])
    mock_update_stoch.assert_called_once()


@pytest.mark.unit
async def test_evaluate_uses_last_candle_market_and_type(mocker):
    """evaluate()가 마지막 캔들의 code와 type을 market/candle_type으로 사용한다."""
    strategy = _make_strategy()
    candle = _make_candle(code="KRW-ETH", candle_type=CandleType.MINUTE_5)

    mocker.patch.object(strategy, "setup_macd", return_value={"upper": {}, "mid": {}, "lower": {}})
    mock_update_macd = mocker.patch.object(strategy, "update_macd", new=AsyncMock())
    mocker.patch.object(strategy, "setup_rsi", return_value={"rsi": np.array([]), "signal": np.array([])})
    mocker.patch.object(strategy, "update_rsi", new=AsyncMock())
    mocker.patch.object(strategy, "setup_stoch", return_value={"k_slow": np.array([]), "d_slow": np.array([])})
    mocker.patch.object(strategy, "update_stoch", new=AsyncMock())

    await strategy.evaluate(candles=[candle], regime=MarketRegime.STABLE_BULL, portfolio=MagicMock())

    _, market_arg, candle_type_arg, _ = mock_update_macd.call_args.args
    assert market_arg == "KRW-ETH"
    assert candle_type_arg == CandleType.MINUTE_5

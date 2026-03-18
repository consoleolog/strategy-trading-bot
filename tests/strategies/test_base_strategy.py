"""BaseStrategy 단위 테스트."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from src.models.signal import Signal
from src.repositories.signal_repository import SignalRepository
from src.strategies.base_strategy import BaseStrategy
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import (
    CandleType,
    MarketRegime,
    SignalDirection,
    SignalType,
    SignalValue,
)

# ---------------------------------------------------------------------------
# 테스트용 구체 클래스
# ---------------------------------------------------------------------------


class BullOnlyStrategy(BaseStrategy):
    """상승장 국면만 지원하는 최소 구현 전략."""

    async def evaluate(self, candles, regime, portfolio):
        raise NotImplementedError

    def get_supported_regimes(self) -> list[MarketRegime]:
        return [MarketRegime.STABLE_BULL, MarketRegime.START_OF_BULL]


class AllRegimeStrategy(BaseStrategy):
    """모든 국면을 지원하는 전략."""

    async def evaluate(self, candles, regime, portfolio):
        raise NotImplementedError

    def get_supported_regimes(self) -> list[MarketRegime]:
        return list(MarketRegime)


def _make_repo() -> MagicMock:
    return MagicMock(spec=SignalRepository)


def _make_aggregator() -> MagicMock:
    return MagicMock(spec=SignalAggregator)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_name_from_config_strategy_id():
    """config에 strategy_id가 있으면 그 값을 name으로 사용한다."""
    strategy = BullOnlyStrategy(
        config={"strategy_id": "my_bull_v1"},
        aggregator=_make_aggregator(),
        signal_repository=_make_repo(),
    )
    assert strategy.name == "my_bull_v1"


@pytest.mark.unit
def test_name_defaults_to_class_name():
    """config에 strategy_id가 없으면 클래스명을 name으로 사용한다."""
    strategy = BullOnlyStrategy(
        config={},
        aggregator=_make_aggregator(),
        signal_repository=_make_repo(),
    )
    assert strategy.name == "BullOnlyStrategy"


@pytest.mark.unit
def test_aggregator_assigned():
    """aggregator가 인스턴스 속성으로 할당된다."""
    aggregator = _make_aggregator()
    strategy = BullOnlyStrategy(
        config={},
        aggregator=aggregator,
        signal_repository=_make_repo(),
    )
    assert strategy.aggregator is aggregator


@pytest.mark.unit
def test_signal_repository_assigned():
    """signal_repository가 인스턴스 속성으로 할당된다."""
    repo = _make_repo()
    strategy = BullOnlyStrategy(
        config={},
        aggregator=_make_aggregator(),
        signal_repository=repo,
    )
    assert strategy.signal_repository is repo


# ---------------------------------------------------------------------------
# should_run
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_should_run_returns_true_for_supported_regime():
    """지원 국면이면 should_run()이 True를 반환한다."""
    strategy = BullOnlyStrategy(
        config={},
        aggregator=_make_aggregator(),
        signal_repository=_make_repo(),
    )
    assert strategy.should_run(MarketRegime.STABLE_BULL) is True
    assert strategy.should_run(MarketRegime.START_OF_BULL) is True


@pytest.mark.unit
def test_should_run_returns_false_for_unsupported_regime():
    """지원하지 않는 국면이면 should_run()이 False를 반환한다."""
    strategy = BullOnlyStrategy(
        config={},
        aggregator=_make_aggregator(),
        signal_repository=_make_repo(),
    )
    assert strategy.should_run(MarketRegime.STABLE_BEAR) is False
    assert strategy.should_run(MarketRegime.START_OF_BEAR) is False


@pytest.mark.unit
def test_should_run_all_regimes():
    """모든 국면을 지원하면 어떤 국면에서도 should_run()이 True를 반환한다."""
    strategy = AllRegimeStrategy(
        config={},
        aggregator=_make_aggregator(),
        signal_repository=_make_repo(),
    )
    for regime in MarketRegime:
        assert strategy.should_run(regime) is True


# ---------------------------------------------------------------------------
# 추상 메서드 강제
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cannot_instantiate_without_evaluate():
    """evaluate를 구현하지 않으면 인스턴스 생성 시 TypeError가 발생한다."""

    class IncompleteStrategy(BaseStrategy):
        def get_supported_regimes(self) -> list[MarketRegime]:
            return []

    with pytest.raises(TypeError):
        IncompleteStrategy(config={}, aggregator=_make_aggregator(), signal_repository=_make_repo())


@pytest.mark.unit
def test_cannot_instantiate_without_get_supported_regimes():
    """get_supported_regimes를 구현하지 않으면 인스턴스 생성 시 TypeError가 발생한다."""

    class IncompleteStrategy(BaseStrategy):
        async def evaluate(self, candles, regime, portfolio):
            raise NotImplementedError

    with pytest.raises(TypeError):
        IncompleteStrategy(config={}, aggregator=_make_aggregator(), signal_repository=_make_repo())


# ---------------------------------------------------------------------------
# create_signal
# ---------------------------------------------------------------------------


def _make_strategy(name: str = "test_strategy") -> BullOnlyStrategy:
    repo = MagicMock(spec=SignalRepository)
    return BullOnlyStrategy(
        config={"strategy_id": name},
        aggregator=_make_aggregator(),
        signal_repository=repo,
    )


@pytest.mark.unit
def test_create_signal_returns_signal():
    """create_signal()이 Signal 인스턴스를 반환한다."""
    strategy = _make_strategy()
    signal = strategy.create_signal(
        indicator_id="ema_5_20",
        signal_type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=SignalDirection.LONG,
        regime=MarketRegime.STABLE_BULL,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        metadata={},
    )
    assert isinstance(signal, Signal)


@pytest.mark.unit
def test_create_signal_strategy_id_matches_name():
    """create_signal()이 생성한 신호의 strategy_id는 전략 name과 일치한다."""
    strategy = _make_strategy("my_strategy")
    signal = strategy.create_signal(
        indicator_id="ema_5_20",
        signal_type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=SignalDirection.LONG,
        regime=MarketRegime.STABLE_BULL,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        metadata={},
    )
    assert signal.strategy_id == "my_strategy"


@pytest.mark.unit
def test_create_signal_timeframe_from_candle_type():
    """create_signal()의 timeframe은 candle_type.value로 설정된다."""
    strategy = _make_strategy()
    signal = strategy.create_signal(
        indicator_id="ema_5_20",
        signal_type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=SignalDirection.LONG,
        regime=MarketRegime.STABLE_BULL,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        metadata={},
    )
    assert signal.timeframe == CandleType.MINUTE_1.value


@pytest.mark.unit
def test_create_signal_fields_preserved():
    """create_signal()이 전달된 모든 필드를 신호에 올바르게 담는다."""
    strategy = _make_strategy()
    signal = strategy.create_signal(
        indicator_id="rsi_14",
        signal_type=SignalType.LEVEL_BREAK,
        value=SignalValue.OVER_SOLD,
        direction=SignalDirection.LONG,
        regime=MarketRegime.STABLE_BEAR,
        market="KRW-ETH",
        candle_type=CandleType.MINUTE_1,
        metadata={"rsi": 28.3},
    )
    assert signal.indicator_id == "rsi_14"
    assert signal.type is SignalType.LEVEL_BREAK
    assert signal.value is SignalValue.OVER_SOLD
    assert signal.direction is SignalDirection.LONG
    assert signal.regime is MarketRegime.STABLE_BEAR
    assert signal.market == "KRW-ETH"
    assert signal.metadata == {"rsi": 28.3}


# ---------------------------------------------------------------------------
# check_crossover
# ---------------------------------------------------------------------------


def _make_strategy_with_mock_repo() -> tuple[BullOnlyStrategy, AsyncMock]:
    """저장소가 AsyncMock인 전략과 해당 mock을 함께 반환한다."""
    saved_signal = Signal(
        strategy_id="test_strategy",
        indicator_id="ema_5_20",
        type=SignalType.CROSS_OVER,
        value=SignalValue.GOLDEN_CROSS,
        direction=SignalDirection.LONG,
        regime=MarketRegime.STABLE_BULL,
        market="KRW-BTC",
        timeframe=CandleType.MINUTE_1.value,
    )
    mock_save = AsyncMock(return_value=saved_signal)
    mock_repo = MagicMock(spec=SignalRepository)
    mock_repo.save = mock_save
    strategy = BullOnlyStrategy(
        config={"strategy_id": "test_strategy"},
        aggregator=_make_aggregator(),
        signal_repository=mock_repo,
    )
    return strategy, mock_save


@pytest.mark.unit
async def test_check_crossover_golden_cross_saves_and_returns_signal():
    """골든 크로스 발생 시 GOLDEN_CROSS 신호를 저장하고 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    one = np.array([1.0, 3.0])  # 이전 < two, 현재 > two → 상향 돌파
    two = np.array([2.0, 2.0])

    result = await strategy.check_crossover(
        one_values=one,
        two_values=two,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert saved.value is SignalValue.GOLDEN_CROSS
    assert saved.direction is SignalDirection.LONG
    assert isinstance(result, Signal)


@pytest.mark.unit
async def test_check_crossover_dead_cross_saves_and_returns_signal():
    """데드 크로스 발생 시 DEAD_CROSS 신호를 저장하고 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    one = np.array([3.0, 1.0])  # 이전 > two, 현재 < two → 하향 돌파
    two = np.array([2.0, 2.0])

    await strategy.check_crossover(
        one_values=one,
        two_values=two,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BEAR,
    )

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert saved.value is SignalValue.DEAD_CROSS
    assert saved.direction is SignalDirection.CLOSE


@pytest.mark.unit
async def test_check_crossover_no_cross_returns_none():
    """교차가 없으면 None을 반환하고 저장소를 호출하지 않는다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    one = np.array([1.0, 1.5])  # 항상 two보다 작음
    two = np.array([2.0, 2.0])

    result = await strategy.check_crossover(
        one_values=one,
        two_values=two,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_not_called()
    assert result is None


@pytest.mark.unit
async def test_check_crossover_insufficient_data_returns_none():
    """값이 1개 이하이면 None을 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    result = await strategy.check_crossover(
        one_values=np.array([1.0]),
        two_values=np.array([2.0]),
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_not_called()
    assert result is None


@pytest.mark.unit
async def test_check_crossover_metadata_contains_values():
    """check_crossover()가 생성한 신호의 metadata에 이전/현재 값이 포함된다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    one = np.array([1.0, 3.0])
    two = np.array([2.0, 2.0])

    await strategy.check_crossover(
        one_values=one,
        two_values=two,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BULL,
    )

    saved = mock_save.call_args.args[0]
    assert saved.metadata["prev_one"] == 1.0
    assert saved.metadata["curr_one"] == 3.0
    assert saved.metadata["prev_two"] == 2.0
    assert saved.metadata["curr_two"] == 2.0


@pytest.mark.unit
async def test_check_crossover_regime_passed_to_signal():
    """check_crossover()가 생성한 신호에 regime이 올바르게 전달된다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    one = np.array([1.0, 3.0])
    two = np.array([2.0, 2.0])

    await strategy.check_crossover(
        one_values=one,
        two_values=two,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="ema_5_20",
        regime=MarketRegime.STABLE_BULL,
    )

    saved = mock_save.call_args.args[0]
    assert saved.regime is MarketRegime.STABLE_BULL


# ---------------------------------------------------------------------------
# check_level_break
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_check_level_break_overbought_saves_and_returns_signal():
    """value > overbought 이면 OVER_BOUGHT 신호를 저장하고 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    result = await strategy.check_level_break(
        value=Decimal("75"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert saved.value is SignalValue.OVER_BOUGHT
    assert saved.type is SignalType.LEVEL_BREAK
    assert isinstance(result, Signal)


@pytest.mark.unit
async def test_check_level_break_oversold_saves_and_returns_signal():
    """value < oversold 이면 OVER_SOLD 신호를 저장하고 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    await strategy.check_level_break(
        value=Decimal("25"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BEAR,
    )

    mock_save.assert_called_once()
    saved = mock_save.call_args.args[0]
    assert saved.value is SignalValue.OVER_SOLD
    assert saved.type is SignalType.LEVEL_BREAK


@pytest.mark.unit
async def test_check_level_break_within_range_returns_none():
    """value가 과매수/과매도 범위 안이면 None을 반환하고 저장소를 호출하지 않는다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    result = await strategy.check_level_break(
        value=Decimal("50"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_not_called()
    assert result is None


@pytest.mark.unit
async def test_check_level_break_metadata_contains_values():
    """check_level_break()가 생성한 신호의 metadata에 value/임계값이 포함된다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    await strategy.check_level_break(
        value=Decimal("75"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BULL,
    )

    saved = mock_save.call_args.args[0]
    assert saved.metadata["value"] == 75.0
    assert saved.metadata["overbought"] == 70
    assert saved.metadata["oversold"] == 30


@pytest.mark.unit
async def test_check_level_break_regime_passed_to_signal():
    """check_level_break()가 생성한 신호에 regime이 올바르게 전달된다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    await strategy.check_level_break(
        value=Decimal("75"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BEAR,
    )

    saved = mock_save.call_args.args[0]
    assert saved.regime is MarketRegime.STABLE_BEAR


@pytest.mark.unit
async def test_check_level_break_exact_threshold_returns_none():
    """value == overbought 또는 value == oversold 이면 None을 반환한다."""
    strategy, mock_save = _make_strategy_with_mock_repo()

    result_ob = await strategy.check_level_break(
        value=Decimal("70"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BULL,
    )
    result_os = await strategy.check_level_break(
        value=Decimal("30"),
        overbought=70,
        oversold=30,
        market="KRW-BTC",
        candle_type=CandleType.MINUTE_1,
        indicator_id="rsi_14",
        regime=MarketRegime.STABLE_BULL,
    )

    mock_save.assert_not_called()
    assert result_ob is None
    assert result_os is None


# ---------------------------------------------------------------------------
# 캔들 헬퍼
# ---------------------------------------------------------------------------


def _make_candles(prices: list[float]) -> list:
    """trade_price / high_price / low_price 가 모두 동일한 단순 캔들 목록을 생성한다."""
    candles = []
    for p in prices:
        c = MagicMock()
        c.trade_price = Decimal(str(p))
        c.high_price = Decimal(str(p))
        c.low_price = Decimal(str(p))
        candles.append(c)
    return candles


# ---------------------------------------------------------------------------
# calculate_ema
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_ema_insufficient_candles_returns_empty():
    """캔들 수가 period 미만이면 빈 배열을 반환한다."""
    candles = _make_candles([100.0, 200.0])
    result = BullOnlyStrategy.calculate_ema(candles, period=9)
    assert len(result) == 0


@pytest.mark.unit
def test_calculate_ema_calls_talib_with_trade_prices(mocker):
    """talib.EMA를 캔들의 trade_price 배열로 호출한다."""
    mock_ema = mocker.patch("src.strategies.base_strategy.talib.EMA", return_value=np.array([1.0]))
    candles = _make_candles([100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0])
    BullOnlyStrategy.calculate_ema(candles, period=9)

    mock_ema.assert_called_once()
    prices_arg = mock_ema.call_args.args[0]
    np.testing.assert_array_equal(prices_arg, [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0])


@pytest.mark.unit
def test_calculate_ema_returns_talib_result(mocker):
    """talib.EMA 반환값을 그대로 반환한다."""
    expected = np.array([150.0, 155.0])
    mocker.patch("src.strategies.base_strategy.talib.EMA", return_value=expected)
    candles = _make_candles([100.0] * 9)

    result = BullOnlyStrategy.calculate_ema(candles, period=9)

    np.testing.assert_array_equal(result, expected)


# ---------------------------------------------------------------------------
# calculate_macd
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_macd_insufficient_candles_returns_empty_dict():
    """캔들 수가 slow_period 미만이면 빈 배열 딕셔너리를 반환한다."""
    candles = _make_candles([100.0] * 10)
    result = BullOnlyStrategy.calculate_macd(candles, fast_period=13, slow_period=26)
    assert len(result["macd"]) == 0
    assert len(result["signal"]) == 0
    assert len(result["histogram"]) == 0


@pytest.mark.unit
def test_calculate_macd_calls_talib_with_correct_periods(mocker):
    """talib.MACD를 fast_period/slow_period/signal_period로 호출한다."""
    mock_macd = mocker.patch(
        "src.strategies.base_strategy.talib.MACD",
        return_value=(np.array([1.0]), np.array([0.5]), np.array([0.5])),
    )
    candles = _make_candles([100.0] * 26)
    BullOnlyStrategy.calculate_macd(candles, fast_period=13, slow_period=26, signal_period=9)

    mock_macd.assert_called_once()
    kwargs = mock_macd.call_args.kwargs
    assert kwargs["fastperiod"] == 13
    assert kwargs["slowperiod"] == 26
    assert kwargs["signalperiod"] == 9


@pytest.mark.unit
def test_calculate_macd_returns_correct_keys(mocker):
    """반환 딕셔너리가 macd, signal, histogram 키를 포함한다."""
    mocker.patch(
        "src.strategies.base_strategy.talib.MACD",
        return_value=(np.array([1.0]), np.array([0.5]), np.array([0.5])),
    )
    candles = _make_candles([100.0] * 26)
    result = BullOnlyStrategy.calculate_macd(candles)

    assert set(result.keys()) == {"macd", "signal", "histogram"}
    assert len(result["macd"]) == 1


# ---------------------------------------------------------------------------
# calculate_rsi
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_rsi_insufficient_candles_returns_empty():
    """캔들 수가 period 미만이면 빈 배열을 반환한다."""
    candles = _make_candles([100.0] * 5)
    result = BullOnlyStrategy.calculate_rsi(candles, period=14)
    assert len(result) == 0


@pytest.mark.unit
def test_calculate_rsi_calls_talib_with_trade_prices(mocker):
    """talib.RSI를 캔들의 trade_price 배열과 period로 호출한다."""
    mock_rsi = mocker.patch("src.strategies.base_strategy.talib.RSI", return_value=np.array([55.0]))
    candles = _make_candles([100.0] * 14)
    BullOnlyStrategy.calculate_rsi(candles, period=14)

    mock_rsi.assert_called_once()
    assert mock_rsi.call_args.args[1] == 14


@pytest.mark.unit
def test_calculate_rsi_returns_talib_result(mocker):
    """talib.RSI 반환값을 그대로 반환한다."""
    expected = np.array([55.0, 60.0])
    mocker.patch("src.strategies.base_strategy.talib.RSI", return_value=expected)
    candles = _make_candles([100.0] * 14)

    result = BullOnlyStrategy.calculate_rsi(candles, period=14)

    np.testing.assert_array_equal(result, expected)


# ---------------------------------------------------------------------------
# calculate_stoch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_stoch_insufficient_candles_returns_empty_dict():
    """캔들 수가 k_len 미만이면 빈 배열 딕셔너리를 반환한다."""
    candles = _make_candles([100.0] * 5)
    result = BullOnlyStrategy.calculate_stoch(candles, k_len=10, k_smooth=3, d_smooth=3)
    assert len(result["k_slow"]) == 0
    assert len(result["d_slow"]) == 0


@pytest.mark.unit
def test_calculate_stoch_calls_talib_with_correct_params(mocker):
    """talib.STOCH을 올바른 파라미터로 호출한다."""
    mock_stoch = mocker.patch(
        "src.strategies.base_strategy.talib.STOCH",
        return_value=(np.array([50.0]), np.array([48.0])),
    )
    candles = _make_candles([100.0] * 10)
    BullOnlyStrategy.calculate_stoch(candles, k_len=10, k_smooth=3, d_smooth=3)

    mock_stoch.assert_called_once()
    kwargs = mock_stoch.call_args.kwargs
    assert kwargs["fastk_period"] == 10
    assert kwargs["slowk_period"] == 3
    assert kwargs["slowd_period"] == 3


@pytest.mark.unit
def test_calculate_stoch_returns_correct_keys(mocker):
    """반환 딕셔너리가 k_slow, d_slow 키를 포함한다."""
    mocker.patch(
        "src.strategies.base_strategy.talib.STOCH",
        return_value=(np.array([50.0]), np.array([48.0])),
    )
    candles = _make_candles([100.0] * 10)
    result = BullOnlyStrategy.calculate_stoch(candles, k_len=10, k_smooth=3, d_smooth=3)

    assert set(result.keys()) == {"k_slow", "d_slow"}
    assert len(result["k_slow"]) == 1
    assert len(result["d_slow"]) == 1

"""BaseStrategy 단위 테스트."""

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

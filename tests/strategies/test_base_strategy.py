"""BaseStrategy 단위 테스트."""

from unittest.mock import MagicMock

import pytest
from src.repositories.signal_repository import SignalRepository
from src.strategies.base_strategy import BaseStrategy
from src.strategies.signal_aggregator import SignalAggregator
from src.utils.constants import MarketRegime

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

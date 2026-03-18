from abc import ABC, abstractmethod

import numpy as np
import structlog

from ..models import Candle, PortfolioState, Signal, TradeCandidate
from ..repositories import SignalRepository
from ..utils.constants import CandleType, MarketRegime, SignalDirection, SignalType, SignalValue
from .signal_aggregator import SignalAggregator

logger = structlog.get_logger(__name__)


class BaseStrategy(ABC):
    """트레이딩 전략의 추상 기반 클래스.

    모든 전략은 이 클래스를 상속하고 :meth:`evaluate` 와
    :meth:`get_supported_regimes` 를 구현해야 한다.

    Attributes:
        name: 전략 식별자. ``config["strategy_id"]`` 가 없으면 클래스명을 사용한다.
        aggregator: 신호 집계기. 여러 지표 신호를 하나의 판단으로 합산한다.
        signal_repository: 신호 저장소. 생성된 신호를 영속화하는 데 사용된다.
    """

    def __init__(
        self,
        config: dict,
        aggregator: SignalAggregator,
        signal_repository: SignalRepository,
    ):
        """전략을 초기화한다.

        Args:
            config: 전략 설정 딕셔너리. ``strategy_id`` 키로 전략명을 지정할 수 있다.
            aggregator: 신호 집계기 인스턴스.
            signal_repository: 신호 저장소 인스턴스.
        """
        self.name = config.get("strategy_id", self.__class__.__name__)
        self.aggregator = aggregator
        self.signal_repository = signal_repository

    # ========================================================================
    # ABSTRACT METHODS
    # ========================================================================

    @abstractmethod
    async def evaluate(self, candles: list[Candle], regime: MarketRegime, portfolio: PortfolioState) -> TradeCandidate:
        """현재 시장 상황을 평가하고 거래 후보를 반환한다.

        Args:
            candles: 평가에 사용할 캔들 목록.
            regime: 현재 시장 국면.
            portfolio: 현재 포트폴리오 상태.

        Returns:
            전략이 판단한 거래 후보.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_supported_regimes(self) -> list[MarketRegime]:
        """이 전략이 동작하는 시장 국면 목록을 반환한다.

        Returns:
            전략이 지원하는 :class:`MarketRegime` 목록.
        """
        raise NotImplementedError()

    # ========================================================================
    # PUBLIC METHODS
    # ========================================================================

    def should_run(self, regime: MarketRegime) -> bool:
        """현재 시장 국면에서 이 전략을 실행해야 하는지 판단한다.

        Args:
            regime: 현재 시장 국면.

        Returns:
            지원 국면 목록에 포함되면 ``True``, 아니면 ``False``.
        """
        return regime in self.get_supported_regimes()

    def create_signal(
        self,
        indicator_id: str,
        signal_type: SignalType,
        value: SignalValue,
        direction: SignalDirection,
        regime: MarketRegime,
        market: str,
        candle_type: CandleType,
        metadata: dict,
    ) -> Signal:
        """Signal 객체를 생성해 반환한다.

        Args:
            indicator_id: 신호를 생성한 지표 식별자.
            signal_type: 신호 종류.
            value: 신호 값.
            direction: 포지션 방향.
            regime: 신호 생성 시점의 시장 국면.
            market: 대상 마켓 코드 (예: KRW-BTC).
            candle_type: 캔들 타입 (타임프레임 결정에 사용).
            metadata: 추가 분석 데이터.

        Returns:
            생성된 :class:`Signal` 인스턴스.
        """
        return Signal(
            strategy_id=self.name,
            indicator_id=indicator_id,
            type=signal_type,
            value=value,
            direction=direction,
            regime=regime,
            market=market,
            timeframe=candle_type.value,
            metadata=metadata,
        )

    async def check_crossover(
        self,
        one_values: np.ndarray,
        two_values: np.ndarray,
        market: str,
        candle_type: CandleType,
        indicator_id: str,
        regime: MarketRegime,
    ) -> Signal | None:
        """두 값 시리즈 간의 교차(crossover)를 감지하고 신호를 저장한다.

        이전 값과 현재 값을 비교해 골든 크로스(``one``이 ``two``를 상향 돌파) 또는
        데드 크로스(``one``이 ``two``를 하향 돌파)를 판단한다.
        교차가 발생하면 신호를 생성해 저장소에 저장하고 반환한다.
        교차가 없으면 ``None``을 반환한다.

        Args:
            one_values: 비교 기준 첫 번째 값 시리즈 (예: 단기 이동평균).
            two_values: 비교 기준 두 번째 값 시리즈 (예: 장기 이동평균).
            market: 대상 마켓 코드.
            candle_type: 캔들 타입 (타임프레임 결정에 사용).
            indicator_id: 지표 식별자.
            regime: 현재 시장 국면.

        Returns:
            교차 발생 시 저장된 :class:`Signal`, 아니면 ``None``.
        """
        if len(one_values) < 2 or len(two_values) < 2:
            return None

        prev_one, curr_one = one_values[-2], one_values[-1]
        prev_two, curr_two = two_values[-2], two_values[-1]

        metadata = {
            "prev_one": float(prev_one),
            "curr_one": float(curr_one),
            "prev_two": float(prev_two),
            "curr_two": float(curr_two),
        }

        # 과거 (one < two) and 현재 (one > two) -> GOLDEN CROSS
        if prev_one < prev_two and curr_one > curr_two:
            signal = self.create_signal(
                indicator_id=indicator_id,
                signal_type=SignalType.CROSS_OVER,
                value=SignalValue.GOLDEN_CROSS,
                direction=SignalDirection.LONG,
                regime=regime,
                market=market,
                candle_type=candle_type,
                metadata=metadata,
            )
            return await self.signal_repository.save(signal)
        # 과거 (one > two) and 현재 (one < two) -> DEAD CROSS
        elif prev_one > prev_two and curr_one < curr_two:
            signal = self.create_signal(
                indicator_id=indicator_id,
                signal_type=SignalType.CROSS_OVER,
                value=SignalValue.DEAD_CROSS,
                direction=SignalDirection.CLOSE,
                regime=regime,
                market=market,
                candle_type=candle_type,
                metadata=metadata,
            )
            return await self.signal_repository.save(signal)
        else:
            return None

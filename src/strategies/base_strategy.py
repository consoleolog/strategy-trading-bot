from abc import ABC, abstractmethod

import structlog

from ..models import Candle, PortfolioState, TradeCandidate
from ..repositories import SignalRepository
from ..utils.constants import MarketRegime
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

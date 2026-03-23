from decimal import Decimal

import structlog

from ..models import Decision, PortfolioState, RiskLimitsConfig
from ..strategies import SignalAggregator
from .confluence_checker import ConfluenceChecker
from .position_sizer import PositionSizer

logger = structlog.get_logger(__name__)


class DecisionEngine:
    """시그널 집계 → 컨플루언스 검증 → 포지션 산정의 전체 의사결정 파이프라인을 조율하는 클래스.

    :class:`~strategies.SignalAggregator`에서 수집된 시그널을
    :class:`~decision.ConfluenceChecker`로 검증하고,
    조건을 충족한 거래 후보에 대해 :class:`~decision.PositionSizer`로 수량을 산정하여
    :class:`~models.Decision` 목록을 반환한다.

    Attributes:
        aggregator (SignalAggregator): 전략별 시그널을 보관하는 집계기.
        position_sizer (PositionSizer): 리스크 기반 포지션 수량 계산기.
        confluence_checker (ConfluenceChecker): 방향 컨플루언스 검증기.
    """

    def __init__(
        self,
        risk_config: RiskLimitsConfig,
        aggregator: SignalAggregator,
        confluence_checker: ConfluenceChecker,
    ):
        """DecisionEngine을 초기화한다.

        Args:
            risk_config: 포지션 산정에 사용할 리스크 한도 설정값.
            aggregator: 시그널을 마켓별로 집계하는 객체.
            confluence_checker: 시그널 방향 일치 여부를 검증하는 객체.
        """
        self.aggregator = aggregator
        self.position_sizer = PositionSizer(risk_config)
        self.confluence_checker = confluence_checker

    def process(self, portfolio: PortfolioState, price: Decimal) -> list[Decision]:
        """집계된 시그널을 처리하여 실행 가능한 Decision 목록을 반환한다.

        마켓별로 시그널을 순회하며 다음 단계를 수행한다:

        1. 이미 보유 중인 포지션이면 건너뜀
        2. 컨플루언스 조건 미충족 시 건너뜀
        3. 유효 가격이 없으면 건너뜀
        4. 포지션 수량이 0이면 건너뜀

        처리가 끝나면 집계기를 초기화한다.

        Args:
            portfolio: 현재 포트폴리오 상태. 보유 포지션 확인 및 수량 산정에 사용.
            price: 거래 실행에 사용할 현재 가격. 0 이하이면 ``candidate.suggested_entry`` 를
                폴백으로 사용한다.

        Returns:
            실행 대기 상태(PENDING)의 :class:`~models.Decision` 목록.
        """
        decisions = []
        all_signals = self.aggregator.get_all_signals()

        logger.info("decision.process.started", market_count=len(all_signals))

        for market, signals in all_signals.items():
            # 이미 보유 중인 포지션은 중복 진입 방지를 위해 건너뜀
            if market in portfolio.positions:
                logger.debug("decision.skipped.existing_position", market=market)
                continue

            # 컨플루언스 조건 미충족 시 거래 후보 없음
            candidate = self.confluence_checker.check(signals)
            if not candidate:
                continue

            logger.info(
                "decision.confluence.passed",
                market=market,
                direction=candidate.direction.value,
                signal_count=len(signals),
            )

            # price 가 0 이하이면 거래 후보의 제안 진입가를 폴백으로 사용
            price = price or candidate.suggested_entry
            if price <= 0:
                logger.warning("decision.skipped.no_price", market=market)
                continue

            decision = self.position_sizer.calculate(candidate, portfolio, price)

            # 수량이 0이면 실질적으로 실행 불가능한 결정이므로 제외
            if decision.volume > 0:
                decisions.append(decision)
            else:
                logger.warning("decision.skipped.zero_volume", market=market)

        # 처리 완료 후 집계기 초기화 (다음 사이클을 위해 시그널 비움)
        self.aggregator.clear()

        logger.info("decision.engine.completed", decision_count=len(decisions))
        return decisions

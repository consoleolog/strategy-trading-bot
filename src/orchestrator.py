from datetime import datetime, timedelta
from decimal import Decimal

import structlog

from connections import MarketDataFeed, PostgresPool, RedisClient, UpbitAdapter
from decision import DecisionEngine
from decision.confluence_checker import ConfluenceChecker
from models import PortfolioState, RiskLimitsConfig
from repositories import SignalRepository
from risk import RiskEngine
from risk.risk_rule import RiskRule
from risk.rules import (
    DailyLossLimitRule,
    MaxDrawdownRule,
    MaxPositionsRule,
    PortfolioExposureRule,
    PositionSizeRule,
    WeeklyLossLimitRule,
)
from strategies import MacdRsiStochasticStrategy, RegimeDetector, SignalAggregator
from strategies.base_strategy import BaseStrategy

logger = structlog.get_logger(__name__)


class Orchestrator:
    """트레이딩 봇의 전체 생애주기를 관리하는 최상위 오케스트레이터.

    연결(DB·Redis·거래소), 전략, 의사결정 엔진, 리스크 엔진 등
    모든 컴포넌트를 초기화하고 조율한다.

    Attributes:
        mode (str): 트레이딩 실행 모드. ``DRY_RUN`` | ``PAPER`` | ``LIVE``
        markets (list[str]): 감시할 마켓 코드 목록.
        candle_types (list[str]): 구독할 타임프레임 목록.
        config (dict): 컴포넌트별 설정 딕셔너리.
    """

    def __init__(
        self,
        mode: str,
        markets: list[str],
        candle_types: list[str],
        config: dict,
    ):
        """Orchestrator 를 초기화한다.

        Args:
            mode: 트레이딩 실행 모드. ``DRY_RUN`` | ``PAPER`` | ``LIVE``
            markets: 감시할 마켓 코드 목록.
            candle_types: 구독할 타임프레임 목록.
            config: 컴포넌트별 설정 딕셔너리.
        """
        self.mode = mode
        self.markets = markets
        self.candle_types = candle_types
        self.config = config or config

        # 런타임 상태
        self._running = False
        self._started_at: datetime | None = None
        self._candles_processed = 0
        self._signals_generated = 0
        self._trades_executed = 0

        # Connections
        self._pool: PostgresPool | None = None
        self._redis: RedisClient | None = None
        self._market_feed: MarketDataFeed | None = None
        self._adapter: UpbitAdapter | None = None

        # Strategies
        self._regime_detector: RegimeDetector | None = None
        self._aggregator: SignalAggregator | None = None
        self._strategies: list[BaseStrategy] = []
        self._signal_count: int = 3

        # Decision
        self._confluence_checker: ConfluenceChecker | None = None
        self._decision_engine: DecisionEngine | None = None

        # Repositories
        self._signal_repository: SignalRepository | None = None

        # Risk
        self._risk_engine: RiskEngine | None = None
        self._risk_config = RiskLimitsConfig(
            max_drawdown=0.20,  # 최대 낙폭 20%
            daily_loss_limit=0.05,  # 일일 손실 한도 5%
            weekly_loss_limit=0.10,  # 주간 손실 한도 10%
            max_position_size=0.30,  # 단일 포지션 최대 비중 30%
            max_risk_per_trade=0.02,  # 거래당 최대 리스크 2%
            max_positions=5,  # 동시 보유 최대 포지션 수 5개
            max_portfolio_exposure=0.80,  # 포트폴리오 최대 노출도 80%
        )

        # Portfolio State
        self._portfolio: PortfolioState | None = None

    async def setup(self) -> bool:
        """모든 컴포넌트를 순서대로 초기화한다.

        DB 풀 → Redis → 거래소 어댑터 → 포트폴리오 → 시장 데이터 피드 →
        레짐 감지기 → 신호 집계기 → 컨플루언스 체커 → 의사결정 엔진 →
        리스크 엔진 → 전략 순으로 초기화한다.

        Returns:
            초기화 성공 시 ``True``, 예외 발생 시 ``False``.
        """
        logger.info("orchestrator.setup.started")

        try:
            # 1. DB Pool 초기화
            self._pool = PostgresPool(self.config.get("database"))
            await self._pool.connect()
            logger.info("orchestrator.setup.postgres_ready")

            # 1.1 Repositories 초기화
            self._signal_repository = SignalRepository(pool=self._pool)

            # 2. Redis 초기화
            self._redis = RedisClient(self.config.get("redis"))
            await self._redis.connect()
            logger.info("orchestrator.setup.redis_ready")

            # 3. UpbitAdapter 초기화
            self._adapter = UpbitAdapter(self.config.get("upbit"))
            await self._adapter.connect()
            logger.info("orchestrator.setup.adapter_ready")

            # 3.1. Portfolio state 초기화 — 거래소에서 KRW 잔고를 조회하여 초기화
            krw = await self._adapter.get_krw()
            total_capital = krw.balance + krw.locked
            self._portfolio = PortfolioState(
                total_capital=total_capital,
                available_capital=krw.balance,
                high_water_mark=krw.balance,
                daily_pnl=Decimal("0"),
                weekly_pnl=Decimal("0"),
                total_pnl=Decimal("0"),
            )

            # 4. MarketDataFeed 초기화
            self._market_feed = MarketDataFeed(
                codes=self.markets,
                types=self.candle_types,
            )
            logger.info("orchestrator.setup.market_feed_ready")

            # 5. RegimeDetector 초기화
            self._regime_detector = RegimeDetector(self.config.get("regime_detector"))

            # 6. SignalAggregator 초기화
            self._aggregator = SignalAggregator()
            logger.info("orchestrator.setup.aggregator_ready")

            # 7. ConfluenceChecker 초기화
            self._confluence_checker = ConfluenceChecker()
            logger.info("orchestrator.setup.confluence_checker_ready")

            # 8. DecisionEngine 초기화
            self._decision_engine = DecisionEngine(
                risk_config=self._risk_config,
                aggregator=self._aggregator,
                confluence_checker=self._confluence_checker,
            )
            logger.info("orchestrator.setup.decision_engine_ready")

            # 9. RiskEngine 초기화
            risk_rules: list[RiskRule] = [
                DailyLossLimitRule(),
                MaxDrawdownRule(),
                MaxPositionsRule(),
                PortfolioExposureRule(),
                PositionSizeRule(),
                WeeklyLossLimitRule(),
            ]
            self._risk_engine = RiskEngine(rules=risk_rules)
            logger.info("orchestrator.setup.risk_engine_ready", rule_count=len(risk_rules))

            # 10. Strategies 초기화
            self._setup_strategies()
            logger.info("orchestrator.setup.strategies_ready", strategy_count=len(self._strategies))

            logger.info("orchestrator.setup.completed")
            return True

        except Exception as e:
            logger.exception("orchestrator.setup.failed", error=str(e))
            return False

    def _setup_strategies(self) -> None:
        """트레이딩 전략 인스턴스를 생성하여 전략 목록에 등록한다."""
        # MACD·RSI·스토캐스틱 복합 전략 등록
        macd_rsi_stoch_strategy = MacdRsiStochasticStrategy(
            config=self.config.get("macd_rsi_stochastic_strategy"),
            aggregator=self._aggregator,
            signal_repository=self._signal_repository,
        )
        self._strategies.append(macd_rsi_stoch_strategy)

        logger.info(
            "orchestrator.strategies.registered",
            strategies=[s.name for s in self._strategies],
        )

    async def shutdown(self) -> None:
        """모든 컴포넌트 연결을 해제하고 운용 요약을 출력한다.

        이미 중지 상태이면 아무 동작도 하지 않는다.
        """
        if not self._running:
            return

        logger.info("orchestrator.shutdown.started")
        self._running = False

        # MarketDataFeed 연결 해제
        if self._market_feed:
            try:
                await self._market_feed.disconnect()
            except Exception as e:
                logger.warning("orchestrator.shutdown.market_feed_error", error=str(e))

        # UpbitAdapter 연결 해제
        if self._adapter:
            try:
                await self._adapter.disconnect()
            except Exception as e:
                logger.warning("orchestrator.shutdown.adapter_error", error=str(e))

        # DB Pool 연결 해제
        if self._pool:
            try:
                await self._pool.disconnect()
            except Exception as e:
                logger.warning("orchestrator.shutdown.pool_error", error=str(e))

        # Redis 연결 해제
        if self._redis:
            try:
                await self._redis.disconnect()
            except Exception as e:
                logger.warning("orchestrator.shutdown.redis_error", error=str(e))

        # Print summary
        runtime = datetime.now() - self._started_at if self._started_at else timedelta(0)
        logger.info(
            "orchestrator.shutdown.completed",
            runtime=str(runtime),
            candles_processed=self._candles_processed,
            signals_generated=self._signals_generated,
            trades_executed=self._trades_executed,
            final_portfolio=str(self._portfolio.total_capital) if self._portfolio else None,
        )

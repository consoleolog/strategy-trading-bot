"""Orchestrator 단위 테스트."""

import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# orchestrator.py 는 절대 임포트(from connections import ...)를 사용하므로
# 테스트 환경에서 해당 모듈들을 sys.modules 에 미리 등록해 ImportError 를 방지한다.
# models 는 실제 src.models 를 사용해 RiskLimitsConfig 등의 타입이 정상 동작하도록 한다.
import src.models as _src_models
import src.risk as _src_risk
import src.risk.risk_rule as _src_risk_rule
import src.risk.rules as _src_risk_rules
import src.utils as _src_utils
import src.utils.constants as _src_utils_constants
from src.models import Decision, ExecutionResult, PortfolioState, Position
from src.utils.constants import DecisionState, ExecutionState, OrderState, RiskDecision, SignalDirection

sys.modules.setdefault("models", _src_models)
sys.modules.setdefault("risk", _src_risk)
sys.modules.setdefault("risk.risk_rule", _src_risk_rule)
sys.modules.setdefault("risk.rules", _src_risk_rules)
sys.modules.setdefault("utils", _src_utils)
sys.modules.setdefault("utils.constants", _src_utils_constants)

_STUB_MODULES = [
    "connections",
    "decision",
    "decision.confluence_checker",
    "repositories",
    "strategies",
    "strategies.base_strategy",
]
for _mod in _STUB_MODULES:
    sys.modules.setdefault(_mod, MagicMock())

from src.orchestrator import Orchestrator  # noqa: E402

# ---------------------------------------------------------------------------
# 헬퍼 팩토리
# ---------------------------------------------------------------------------


def make_orchestrator(**kwargs) -> Orchestrator:
    """기본값으로 Orchestrator 인스턴스를 생성한다."""
    defaults = {
        "mode": "DRY_RUN",
        "markets": ["KRW-BTC"],
        "candle_types": ["1m"],
        "config": {},
    }
    defaults.update(kwargs)
    return Orchestrator(**defaults)


def make_krw_mock(balance: str = "10000000", locked: str = "0"):
    """UpbitAdapter.get_krw() 반환값 Mock 을 생성한다."""
    krw = MagicMock()
    krw.balance = Decimal(balance)
    krw.locked = Decimal(locked)
    return krw


@pytest.fixture
def mocked_setup_deps():
    """setup() 에 필요한 모든 외부 의존성을 AsyncMock / MagicMock 으로 대체하는 픽스처."""
    krw = make_krw_mock()
    adapter = AsyncMock()
    adapter.get_krw = AsyncMock(return_value=krw)
    pool = AsyncMock()
    redis = AsyncMock()
    market_feed = MagicMock()
    market_feed_cls = MagicMock(return_value=market_feed)
    strategy = MagicMock()
    strategy.name = "MacdRsiStochasticStrategy"

    with patch.multiple(
        "src.orchestrator",
        PostgresPool=MagicMock(return_value=pool),
        RedisClient=MagicMock(return_value=redis),
        UpbitAdapter=MagicMock(return_value=adapter),
        MarketDataFeed=market_feed_cls,
        SignalRepository=MagicMock(),
        RegimeDetector=MagicMock(),
        SignalAggregator=MagicMock(),
        ConfluenceChecker=MagicMock(),
        DecisionEngine=MagicMock(),
        RiskEngine=MagicMock(),
        MacdRsiStochasticStrategy=MagicMock(return_value=strategy),
    ):
        yield {
            "pool": pool,
            "redis": redis,
            "adapter": adapter,
            "market_feed": market_feed,
            "market_feed_cls": market_feed_cls,
            "krw": krw,
            "strategy": strategy,
        }


# ---------------------------------------------------------------------------
# __init__ — 초기화 상태
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_stores_mode():
    """mode 가 인스턴스 속성으로 저장된다."""
    orch = make_orchestrator(mode="LIVE")
    assert orch.mode == "LIVE"


@pytest.mark.unit
def test_init_stores_markets():
    """markets 가 인스턴스 속성으로 저장된다."""
    orch = make_orchestrator(markets=["KRW-BTC", "KRW-ETH"])
    assert orch.markets == ["KRW-BTC", "KRW-ETH"]


@pytest.mark.unit
def test_init_stores_candle_types():
    """candle_types 가 인스턴스 속성으로 저장된다."""
    orch = make_orchestrator(candle_types=["1m", "5m"])
    assert orch.candle_types == ["1m", "5m"]


@pytest.mark.unit
def test_init_initial_capital_is_none():
    """초기 _initial_capital 은 None 이다."""
    assert make_orchestrator()._initial_capital is None


@pytest.mark.unit
def test_init_running_is_false():
    """초기 _running 상태는 False 이다."""
    assert make_orchestrator()._running is False


@pytest.mark.unit
def test_init_counters_are_zero():
    """초기 카운터(candles, signals, trades)가 모두 0 이다."""
    orch = make_orchestrator()
    assert orch._candles_processed == 0
    assert orch._signals_generated == 0
    assert orch._trades_executed == 0


@pytest.mark.unit
def test_init_started_at_is_none():
    """초기 _started_at 은 None 이다."""
    assert make_orchestrator()._started_at is None


@pytest.mark.unit
def test_init_connections_are_none():
    """초기 연결 컴포넌트(pool, redis, feed, adapter)는 모두 None 이다."""
    orch = make_orchestrator()
    assert orch._pool is None
    assert orch._redis is None
    assert orch._market_feed is None
    assert orch._adapter is None


@pytest.mark.unit
def test_init_engines_are_none():
    """초기 엔진 컴포넌트(decision, risk, confluence)는 모두 None 이다."""
    orch = make_orchestrator()
    assert orch._decision_engine is None
    assert orch._risk_engine is None
    assert orch._confluence_checker is None


@pytest.mark.unit
def test_init_strategies_is_empty_list():
    """초기 전략 목록은 빈 리스트이다."""
    assert make_orchestrator()._strategies == []


@pytest.mark.unit
def test_init_portfolio_is_none():
    """초기 _portfolio 는 None 이다."""
    assert make_orchestrator()._portfolio is None


@pytest.mark.unit
def test_init_risk_config_values():
    """_risk_config 에 설정된 리스크 한도 값이 올바르다."""
    orch = make_orchestrator()
    assert orch._risk_config.max_drawdown == 0.20
    assert orch._risk_config.daily_loss_limit == 0.05
    assert orch._risk_config.weekly_loss_limit == 0.10
    assert orch._risk_config.max_positions == 5


# ---------------------------------------------------------------------------
# setup() — 성공
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_returns_true_on_success(mocked_setup_deps):
    """모든 컴포넌트 초기화에 성공하면 True 를 반환한다."""
    orch = make_orchestrator()
    result = await orch.setup()
    assert result is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_connects_pool(mocked_setup_deps):
    """setup() 후 DB 풀이 connect 된다."""
    orch = make_orchestrator()
    await orch.setup()
    mocked_setup_deps["pool"].connect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_connects_redis(mocked_setup_deps):
    """setup() 후 Redis 가 connect 된다."""
    orch = make_orchestrator()
    await orch.setup()
    mocked_setup_deps["redis"].connect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_connects_adapter(mocked_setup_deps):
    """setup() 후 거래소 어댑터가 connect 된다."""
    orch = make_orchestrator()
    await orch.setup()
    mocked_setup_deps["adapter"].connect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_portfolio_initialized_with_krw_balance(mocked_setup_deps):
    """setup() 후 포트폴리오가 KRW 잔고로 초기화된다."""
    krw = mocked_setup_deps["krw"]
    orch = make_orchestrator()
    await orch.setup()

    assert orch._portfolio is not None
    assert orch._portfolio.total_capital == krw.balance + krw.locked
    assert orch._portfolio.available_capital == krw.balance


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_risk_engine_initialized(mocked_setup_deps):
    """setup() 후 _risk_engine 이 초기화된다."""
    orch = make_orchestrator()
    await orch.setup()
    assert orch._risk_engine is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_strategies_registered(mocked_setup_deps):
    """setup() 후 전략이 하나 이상 등록된다."""
    orch = make_orchestrator()
    await orch.setup()
    assert len(orch._strategies) >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_signal_repository_initialized(mocked_setup_deps):
    """setup() 후 _signal_repository 가 초기화된다."""
    orch = make_orchestrator()
    await orch.setup()
    assert orch._signal_repository is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_decision_engine_initialized(mocked_setup_deps):
    """setup() 후 _decision_engine 이 초기화된다."""
    orch = make_orchestrator()
    await orch.setup()
    assert orch._decision_engine is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_stores_initial_capital(mocked_setup_deps):
    """setup() 후 _initial_capital 이 KRW 총 잔고(balance + locked)로 저장된다."""
    krw = mocked_setup_deps["krw"]
    orch = make_orchestrator()
    await orch.setup()
    assert orch._initial_capital == krw.balance + krw.locked


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_market_feed_receives_on_candle_close(mocked_setup_deps):
    """setup() 시 MarketDataFeed 에 on_candle_close 콜백이 전달된다."""
    orch = make_orchestrator()
    await orch.setup()
    _, kwargs = mocked_setup_deps["market_feed_cls"].call_args
    assert "on_candle_close" in kwargs
    assert kwargs["on_candle_close"] == orch._on_candle_close


# ---------------------------------------------------------------------------
# setup() — 실패
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_returns_false_when_pool_connect_fails():
    """DB 풀 connect 에서 예외가 발생하면 False 를 반환한다."""
    pool_mock = AsyncMock()
    pool_mock.connect.side_effect = ConnectionError("DB 연결 실패")

    with patch("src.orchestrator.PostgresPool", return_value=pool_mock):
        orch = make_orchestrator()
        result = await orch.setup()

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_returns_false_when_redis_connect_fails(mocked_setup_deps):
    """Redis connect 에서 예외가 발생하면 False 를 반환한다."""
    mocked_setup_deps["redis"].connect.side_effect = ConnectionError("Redis 연결 실패")
    orch = make_orchestrator()
    result = await orch.setup()
    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_returns_false_when_adapter_connect_fails(mocked_setup_deps):
    """거래소 어댑터 connect 에서 예외가 발생하면 False 를 반환한다."""
    mocked_setup_deps["adapter"].connect.side_effect = ConnectionError("어댑터 연결 실패")
    orch = make_orchestrator()
    result = await orch.setup()
    assert result is False


# ---------------------------------------------------------------------------
# shutdown() — 중지 상태
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_does_nothing_when_not_running():
    """_running 이 False 이면 shutdown() 은 아무 동작도 하지 않는다."""
    orch = make_orchestrator()
    feed = AsyncMock()
    orch._market_feed = feed

    await orch.shutdown()  # _running=False 이므로 조기 반환

    feed.disconnect.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_sets_running_to_false():
    """shutdown() 호출 후 _running 이 False 로 설정된다."""
    orch = make_orchestrator()
    orch._running = True
    await orch.shutdown()
    assert orch._running is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_disconnects_all_components():
    """_running=True 일 때 모든 컴포넌트의 disconnect 가 호출된다."""
    orch = make_orchestrator()
    orch._running = True
    orch._market_feed = AsyncMock()
    orch._adapter = AsyncMock()
    orch._pool = AsyncMock()
    orch._redis = AsyncMock()

    await orch.shutdown()

    orch._market_feed.disconnect.assert_awaited_once()
    orch._adapter.disconnect.assert_awaited_once()
    orch._pool.disconnect.assert_awaited_once()
    orch._redis.disconnect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_skips_none_components():
    """연결되지 않은(None) 컴포넌트는 disconnect 를 호출하지 않는다."""
    orch = make_orchestrator()
    orch._running = True
    # 모든 컴포넌트를 None 으로 유지

    await orch.shutdown()  # AttributeError 없이 정상 완료되어야 함


# ---------------------------------------------------------------------------
# shutdown() — 부분 실패 시 계속 진행
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_continues_when_market_feed_fails():
    """market_feed.disconnect() 실패 시 나머지 컴포넌트 해제가 계속 실행된다."""
    orch = make_orchestrator()
    orch._running = True
    orch._market_feed = AsyncMock()
    orch._market_feed.disconnect.side_effect = Exception("피드 해제 실패")
    orch._adapter = AsyncMock()
    orch._pool = AsyncMock()
    orch._redis = AsyncMock()

    await orch.shutdown()

    orch._adapter.disconnect.assert_awaited_once()
    orch._pool.disconnect.assert_awaited_once()
    orch._redis.disconnect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_continues_when_adapter_fails():
    """adapter.disconnect() 실패 시 pool, redis 해제가 계속 실행된다."""
    orch = make_orchestrator()
    orch._running = True
    orch._market_feed = AsyncMock()
    orch._adapter = AsyncMock()
    orch._adapter.disconnect.side_effect = Exception("어댑터 해제 실패")
    orch._pool = AsyncMock()
    orch._redis = AsyncMock()

    await orch.shutdown()

    orch._pool.disconnect.assert_awaited_once()
    orch._redis.disconnect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_continues_when_pool_fails():
    """pool.disconnect() 실패 시 redis 해제가 계속 실행된다."""
    orch = make_orchestrator()
    orch._running = True
    orch._market_feed = AsyncMock()
    orch._adapter = AsyncMock()
    orch._pool = AsyncMock()
    orch._pool.disconnect.side_effect = Exception("풀 해제 실패")
    orch._redis = AsyncMock()

    await orch.shutdown()

    orch._redis.disconnect.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_all_fail_no_exception_raised():
    """모든 disconnect 가 실패해도 shutdown() 자체는 예외를 발생시키지 않는다."""
    orch = make_orchestrator()
    orch._running = True
    for attr in ("_market_feed", "_adapter", "_pool", "_redis"):
        mock = AsyncMock()
        mock.disconnect.side_effect = Exception("해제 실패")
        setattr(orch, attr, mock)

    await orch.shutdown()  # 예외 없이 완료되어야 함


# ---------------------------------------------------------------------------
# shutdown() — 요약 로그 (started_at 설정 여부)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_runtime_calculated_when_started_at_set():
    """_started_at 이 설정된 경우 runtime 이 계산된다 (예외 없음)."""
    orch = make_orchestrator()
    orch._running = True
    orch._started_at = datetime.now()

    await orch.shutdown()  # 예외 없이 완료되어야 함


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shutdown_runtime_zero_when_started_at_none():
    """_started_at 이 None 이면 runtime 이 timedelta(0) 으로 처리된다 (예외 없음)."""
    orch = make_orchestrator()
    orch._running = True
    orch._started_at = None

    await orch.shutdown()  # 예외 없이 완료되어야 함


# ---------------------------------------------------------------------------
# run() — 중복 실행 방지
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_does_not_start_when_already_running():
    """_running=True 이면 run() 은 조기 반환하여 feed.start() 를 호출하지 않는다."""
    orch = make_orchestrator()
    orch._running = True
    orch._pool = AsyncMock()  # setup() 스킵 조건
    orch._market_feed = AsyncMock()

    await orch.run()

    orch._market_feed.start.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sets_running_true_and_records_started_at(mocked_setup_deps):
    """run() 호출 시 _running=True 로 설정되고 _started_at 이 기록된다."""
    orch = make_orchestrator()
    await orch.setup()

    feed = mocked_setup_deps["market_feed"]
    feed.start = AsyncMock()

    await orch.run()

    assert orch._started_at is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_calls_setup_when_pool_is_none(mocked_setup_deps):
    """_pool 이 None 이면 run() 이 setup() 을 자동으로 호출한다."""
    orch = make_orchestrator()

    mocked_setup_deps["market_feed"].start = AsyncMock()

    await orch.run()

    assert orch._pool is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_raises_when_setup_fails():
    """setup() 이 False 를 반환하면 RuntimeError 가 발생한다."""
    pool_mock = AsyncMock()
    pool_mock.connect.side_effect = ConnectionError("DB 실패")

    with patch("src.orchestrator.PostgresPool", return_value=pool_mock):
        orch = make_orchestrator()
        with pytest.raises(RuntimeError):
            await orch.run()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_calls_shutdown_on_cancelled_error(mocked_setup_deps):
    """CancelledError 발생 시 finally 블록에서 shutdown() 이 호출된다."""
    orch = make_orchestrator()
    await orch.setup()

    mocked_setup_deps["market_feed"].start = AsyncMock(side_effect=asyncio.CancelledError())

    await orch.run()

    assert orch._running is False  # shutdown() 이 호출되어 False 로 변경됨


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_calls_shutdown_on_unexpected_error(mocked_setup_deps):
    """예상치 못한 예외 발생 시 finally 블록에서 shutdown() 이 호출된다."""
    orch = make_orchestrator()
    await orch.setup()

    mocked_setup_deps["market_feed"].start = AsyncMock(side_effect=RuntimeError("피드 오류"))

    await orch.run()

    assert orch._running is False  # shutdown() 이 호출되어 False 로 변경됨


# ---------------------------------------------------------------------------
# _on_ticker() — 실시간 Ticker 캐시
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_ticker_stores_to_redis():
    """_running=True 일 때 _on_ticker() 가 Redis 에 ticker 를 저장한다."""
    orch = make_orchestrator()
    orch._running = True
    orch._redis = AsyncMock()

    ticker = MagicMock()
    ticker.code = "KRW-BTC"
    ticker.type = "trade"

    await orch._on_ticker(ticker)

    orch._redis.hset.assert_awaited_once_with("ticker", "KRW-BTC:trade", ticker)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_ticker_does_nothing_when_not_running():
    """_running=False 이면 _on_ticker() 는 Redis 에 저장하지 않는다."""
    orch = make_orchestrator()
    orch._running = False
    orch._redis = AsyncMock()

    ticker = MagicMock()
    ticker.code = "KRW-BTC"
    ticker.type = "trade"

    await orch._on_ticker(ticker)

    orch._redis.hset.assert_not_awaited()


# ---------------------------------------------------------------------------
# _on_candle() — 캔들 수신 및 레짐 감지
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_increments_counter():
    """_on_candle() 호출 시 _candles_processed 가 1 증가한다."""
    from src.utils.constants import CandleType

    orch = make_orchestrator()
    orch._running = True
    orch._redis = AsyncMock()
    orch._adapter = AsyncMock()
    orch._adapter.get_candles = AsyncMock(return_value=[MagicMock(), MagicMock()])
    orch._regime_detector = MagicMock()
    orch._regime_detector.detect.return_value = MagicMock(value="BULL")

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = CandleType.HOUR_4
    candle.trade_price = Decimal("100000")

    await orch._on_candle(candle)

    assert orch._candles_processed == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_does_nothing_when_not_running():
    """_running=False 이면 _on_candle() 은 아무 동작도 하지 않는다."""
    orch = make_orchestrator()
    orch._running = False
    orch._redis = AsyncMock()

    candle = MagicMock()
    await orch._on_candle(candle)

    orch._redis.hset.assert_not_awaited()
    assert orch._candles_processed == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_stores_updated_candles_to_redis():
    """candles[-1] 교체 후 Redis 에 저장하여 최신 캔들이 반영된다."""
    from src.utils.constants import CandleType

    orch = make_orchestrator()
    orch._running = True
    orch._redis = AsyncMock()

    old_last = MagicMock()
    candles = [MagicMock(), old_last]
    orch._adapter = AsyncMock()
    orch._adapter.get_candles = AsyncMock(return_value=candles)
    orch._regime_detector = MagicMock()
    orch._regime_detector.detect.return_value = MagicMock(value="SIDEWAYS")

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = CandleType.HOUR_4
    candle.trade_price = Decimal("105000")

    await orch._on_candle(candle)

    # candles[-1] 이 수신 캔들로 교체된 상태로 Redis 저장 확인
    stored_candles = orch._redis.hset.call_args_list[-1][0][2]
    assert stored_candles[-1] is candle


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_calls_regime_detector():
    """_on_candle() 이 regime_detector.detect() 를 호출한다."""
    from src.utils.constants import CandleType

    orch = make_orchestrator()
    orch._running = True
    orch._redis = AsyncMock()
    orch._adapter = AsyncMock()
    orch._adapter.get_candles = AsyncMock(return_value=[MagicMock(), MagicMock()])
    orch._regime_detector = MagicMock()
    orch._regime_detector.detect.return_value = MagicMock(value="BEAR")

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = CandleType.MINUTE_1  # HOUR_4 외 분기 — else 경로 실행
    candle.trade_price = Decimal("90000")

    await orch._on_candle(candle)

    orch._regime_detector.detect.assert_called_once()


# ---------------------------------------------------------------------------
# 헬퍼 팩토리 — _execute_decision / _place_order / _update_portfolio_after_trade
# ---------------------------------------------------------------------------


def _make_decision(
    market: str = "KRW-BTC",
    direction: SignalDirection = SignalDirection.LONG,
    volume: str = "0.001",
    entry_price: str = "100000000",
) -> Decision:
    """테스트용 Decision 인스턴스를 생성한다."""
    return Decision(
        market=market,
        direction=direction,
        volume=Decimal(volume),
        entry_price=Decimal(entry_price),
        stop_loss=Decimal("95000000"),
        take_profit=Decimal("110000000"),
        risk_amount=Decimal("50000"),
    )


def _make_execution_result(
    decision_id=None,
    order_uuid=None,
    filled_quantity: str = "0.001",
    average_price: str = "100000000",
    fee: str = "500",
) -> ExecutionResult:
    """테스트용 ExecutionResult 인스턴스를 생성한다."""
    return ExecutionResult(
        success=True,
        decision_id=decision_id or uuid4(),
        order_uuid=order_uuid or uuid4(),
        filled_quantity=Decimal(filled_quantity),
        average_price=Decimal(average_price),
        fee=Decimal(fee),
        state=ExecutionState.FILLED,
    )


def _make_portfolio(
    total_capital: str = "10000000",
    available_capital: str = "10000000",
) -> PortfolioState:
    """테스트용 PortfolioState 인스턴스를 생성한다."""
    return PortfolioState(
        total_capital=Decimal(total_capital),
        available_capital=Decimal(available_capital),
        daily_pnl=Decimal("0"),
        weekly_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        high_water_mark=Decimal(total_capital),
    )


def _make_risk_record(
    decision: RiskDecision = RiskDecision.ALLOW,
    reason: str = "OK",
    max_allowed_size_krw=None,
) -> MagicMock:
    """테스트용 RiskRecord Mock 을 생성한다."""
    record = MagicMock()
    record.risk_decision = decision
    record.reason = reason
    record.max_allowed_size_krw = max_allowed_size_krw
    record.triggered_rules = []
    return record


def _make_order_mock(
    executed_volume: str = "0.001",
    price: str = "100000000",
    paid_fee: str = "500",
    state: OrderState = OrderState.WAIT,
) -> MagicMock:
    """테스트용 Order Mock 을 생성한다."""
    order = MagicMock()
    order.uuid = uuid4()
    order.executed_volume = Decimal(executed_volume)
    order.price = Decimal(price)
    order.paid_fee = Decimal(paid_fee)
    order.state = state
    return order


# ---------------------------------------------------------------------------
# _on_candle_close() — 캔들 종가 처리
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_close_does_nothing_when_not_running():
    """_running=False 이면 _on_candle_close() 는 아무 동작도 하지 않는다."""
    orch = make_orchestrator()
    orch._running = False
    orch._redis = AsyncMock()

    await orch._on_candle_close(MagicMock())

    orch._redis.hget.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_close_calls_strategy_evaluate_for_matching_regime():
    """현재 레짐이 전략의 지원 레짐에 포함되면 strategy.evaluate() 가 호출된다."""
    orch = make_orchestrator()
    orch._running = True

    candles = [MagicMock(), MagicMock()]
    ticker = MagicMock()
    orch._redis = AsyncMock()
    orch._redis.hget.side_effect = [candles, ticker]

    regime = MagicMock()
    orch._regime_detector = MagicMock()
    orch._regime_detector.current_regime = regime

    # get_supported_regimes 는 동기 메서드이므로 MagicMock 사용, evaluate 만 async
    strategy = MagicMock()
    strategy.get_supported_regimes.return_value = [regime]
    strategy.evaluate = AsyncMock()
    orch._strategies = [strategy]

    orch._decision_engine = MagicMock()
    orch._decision_engine.process.return_value = []
    orch._portfolio = MagicMock()

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = MagicMock()

    await orch._on_candle_close(candle)

    strategy.evaluate.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_close_skips_strategy_for_unsupported_regime():
    """현재 레짐이 전략의 지원 레짐에 없으면 strategy.evaluate() 가 호출되지 않는다."""
    orch = make_orchestrator()
    orch._running = True

    candles = [MagicMock(), MagicMock()]
    ticker = MagicMock()
    orch._redis = AsyncMock()
    orch._redis.hget.side_effect = [candles, ticker]

    regime = MagicMock()
    orch._regime_detector = MagicMock()
    orch._regime_detector.current_regime = regime

    # get_supported_regimes 는 동기 메서드이므로 MagicMock 사용, evaluate 만 async
    strategy = MagicMock()
    strategy.get_supported_regimes.return_value = [MagicMock()]  # 다른 레짐만 지원
    strategy.evaluate = AsyncMock()
    orch._strategies = [strategy]

    orch._decision_engine = MagicMock()
    orch._decision_engine.process.return_value = []
    orch._portfolio = MagicMock()

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = MagicMock()

    await orch._on_candle_close(candle)

    strategy.evaluate.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_on_candle_close_calls_execute_decision_for_each_decision():
    """decision_engine 이 반환한 각 Decision 마다 _execute_decision() 이 호출된다."""
    orch = make_orchestrator()
    orch._running = True

    candles = [MagicMock(), MagicMock()]
    ticker = MagicMock()
    orch._redis = AsyncMock()
    orch._redis.hget.side_effect = [candles, ticker]

    orch._regime_detector = MagicMock()
    orch._strategies = []
    orch._portfolio = MagicMock()

    d1, d2 = MagicMock(), MagicMock()
    orch._decision_engine = MagicMock()
    orch._decision_engine.process.return_value = [d1, d2]

    orch._execute_decision = AsyncMock(return_value=None)

    candle = MagicMock()
    candle.code = "KRW-BTC"
    candle.type = MagicMock()

    await orch._on_candle_close(candle)

    assert orch._execute_decision.await_count == 2


# ---------------------------------------------------------------------------
# _execute_decision() — 리스크 검증 및 주문 실행
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_calls_risk_engine():
    """_execute_decision() 이 risk_engine.evaluate() 를 호출한다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    orch._risk_engine.evaluate.return_value = _make_risk_record(RiskDecision.ALLOW)
    orch._place_order = AsyncMock(return_value=None)

    await orch._execute_decision(_make_decision())

    orch._risk_engine.evaluate.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_sets_state_executed_on_success():
    """주문 성공 시 decision.state 가 EXECUTED 로 설정된다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    orch._risk_engine.evaluate.return_value = _make_risk_record(RiskDecision.ALLOW)
    orch._place_order = AsyncMock(return_value=_make_execution_result())
    orch._update_portfolio_after_trade = AsyncMock()

    decision = _make_decision()
    await orch._execute_decision(decision)

    assert decision.state == DecisionState.EXECUTED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_increments_trades_executed_on_success():
    """주문 성공 시 _trades_executed 카운터가 1 증가한다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    orch._risk_engine.evaluate.return_value = _make_risk_record(RiskDecision.ALLOW)
    orch._place_order = AsyncMock(return_value=_make_execution_result())
    orch._update_portfolio_after_trade = AsyncMock()

    await orch._execute_decision(_make_decision())

    assert orch._trades_executed == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_calls_update_portfolio_on_success():
    """주문 성공 시 _update_portfolio_after_trade() 가 호출된다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    orch._risk_engine.evaluate.return_value = _make_risk_record(RiskDecision.ALLOW)
    result = _make_execution_result()
    orch._place_order = AsyncMock(return_value=result)
    orch._update_portfolio_after_trade = AsyncMock()

    decision = _make_decision()
    await orch._execute_decision(decision)

    orch._update_portfolio_after_trade.assert_awaited_once_with(decision, result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_sets_rejected_when_risk_blocks():
    """리스크 거부(FORCE_NO_ACTION) 시 decision.state 가 REJECTED 로 설정된다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    orch._risk_engine.evaluate.return_value = _make_risk_record(RiskDecision.FORCE_NO_ACTION)

    decision = _make_decision()
    await orch._execute_decision(decision)

    assert decision.state == DecisionState.REJECTED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_decision_reduces_volume_on_reduce_size():
    """REDUCE_SIZE 시 max_allowed_size_krw 에 맞게 decision.volume 이 축소된다."""
    orch = make_orchestrator()
    orch._initial_capital = Decimal("10000000")
    orch._portfolio = _make_portfolio()
    orch._risk_engine = MagicMock()
    # max_allowed = 50000 KRW, entry_price = 100000000 → max_vol = 0.0005 < 0.001
    orch._risk_engine.evaluate.return_value = _make_risk_record(
        RiskDecision.REDUCE_SIZE, max_allowed_size_krw=Decimal("50000")
    )
    orch._place_order = AsyncMock(return_value=None)

    decision = _make_decision(volume="0.001", entry_price="100000000")
    await orch._execute_decision(decision)

    assert decision.volume == Decimal("50000") / Decimal("100000000")


# ---------------------------------------------------------------------------
# _place_order() — 거래소 주문 제출
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_long_calls_adapter_with_bid():
    """LONG 방향이면 adapter.limit_order() 에 side=BID 가 전달된다."""
    from src.utils.constants import OrderSide

    orch = make_orchestrator()
    orch._adapter = AsyncMock()
    orch._adapter.limit_order = AsyncMock(return_value=_make_order_mock())

    await orch._place_order(_make_decision(direction=SignalDirection.LONG))

    _, kwargs = orch._adapter.limit_order.call_args
    assert kwargs["side"] == OrderSide.BID


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_close_calls_adapter_with_ask():
    """CLOSE 방향이면 adapter.limit_order() 에 side=ASK 가 전달된다."""
    from src.utils.constants import OrderSide

    orch = make_orchestrator()
    orch._adapter = AsyncMock()
    orch._adapter.limit_order = AsyncMock(return_value=_make_order_mock())

    await orch._place_order(_make_decision(direction=SignalDirection.CLOSE))

    _, kwargs = orch._adapter.limit_order.call_args
    assert kwargs["side"] == OrderSide.ASK


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_hold_returns_none():
    """HOLD 방향은 지원하지 않으므로 None 을 반환한다."""
    orch = make_orchestrator()
    orch._adapter = AsyncMock()

    result = await orch._place_order(_make_decision(direction=SignalDirection.HOLD))

    assert result is None
    orch._adapter.limit_order.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_returns_execution_result_on_success():
    """주문 성공 시 success=True 인 ExecutionResult 를 반환한다."""
    orch = make_orchestrator()
    orch._adapter = AsyncMock()
    orch._adapter.limit_order = AsyncMock(return_value=_make_order_mock())

    result = await orch._place_order(_make_decision())

    assert result is not None
    assert result.success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_uses_entry_price_when_order_price_is_none():
    """order.price 가 None 이면 decision.entry_price 를 average_price 폴백으로 사용한다."""
    orch = make_orchestrator()
    orch._adapter = AsyncMock()
    order = _make_order_mock(price="100000000")
    order.price = None  # 가격 없음 — 폴백 적용
    orch._adapter.limit_order = AsyncMock(return_value=order)

    decision = _make_decision(entry_price="99000000")
    result = await orch._place_order(decision)

    assert result.average_price == Decimal("99000000")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_place_order_returns_none_on_exception():
    """adapter.limit_order() 에서 예외가 발생하면 None 을 반환한다."""
    orch = make_orchestrator()
    orch._adapter = AsyncMock()
    orch._adapter.limit_order = AsyncMock(side_effect=RuntimeError("거래소 오류"))

    result = await orch._place_order(_make_decision())

    assert result is None


# ---------------------------------------------------------------------------
# _update_portfolio_after_trade() — 포트폴리오 상태 갱신
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_long_adds_position():
    """LONG 체결 후 portfoliop.positions 에 새 포지션이 추가된다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()

    decision = _make_decision(market="KRW-BTC", direction=SignalDirection.LONG)
    result = _make_execution_result()
    await orch._update_portfolio_after_trade(decision, result)

    assert "KRW-BTC" in orch._portfolio.positions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_long_deducts_available_capital():
    """LONG 체결 후 available_capital 이 (체결금액 + 수수료) 만큼 감소한다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio(available_capital="10000000")

    result = _make_execution_result(filled_quantity="0.001", average_price="100000000", fee="500")
    expected = Decimal("10000000") - Decimal("0.001") * Decimal("100000000") - Decimal("500")

    await orch._update_portfolio_after_trade(_make_decision(direction=SignalDirection.LONG), result)

    assert orch._portfolio.available_capital == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_close_removes_position():
    """CLOSE 체결 후 portfolio.positions 에서 해당 마켓 포지션이 삭제된다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()
    orch._portfolio.positions["KRW-BTC"] = Position(
        market="KRW-BTC",
        direction=SignalDirection.LONG,
        entry_price=Decimal("90000000"),
        current_price=Decimal("100000000"),
        volume=Decimal("0.001"),
        stop_loss=Decimal("85000000"),
        take_profit=Decimal("110000000"),
        strategy_id="test",
    )

    decision = _make_decision(market="KRW-BTC", direction=SignalDirection.CLOSE)
    await orch._update_portfolio_after_trade(decision, _make_execution_result())

    assert "KRW-BTC" not in orch._portfolio.positions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_close_updates_pnl():
    """CLOSE 체결 후 total_pnl / daily_pnl / weekly_pnl 이 실현 손익만큼 증가한다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()
    orch._portfolio.positions["KRW-BTC"] = Position(
        market="KRW-BTC",
        direction=SignalDirection.LONG,
        entry_price=Decimal("90000000"),
        current_price=Decimal("100000000"),
        volume=Decimal("0.001"),
        stop_loss=Decimal("85000000"),
        take_profit=Decimal("110000000"),
        strategy_id="test",
    )

    result = _make_execution_result(filled_quantity="0.001", average_price="100000000", fee="500")
    # pnl = (100000000 - 90000000) * 0.001 - 500 = 10000 - 500 = 9500
    expected_pnl = Decimal("9500")

    await orch._update_portfolio_after_trade(_make_decision(direction=SignalDirection.CLOSE), result)

    assert orch._portfolio.total_pnl == expected_pnl
    assert orch._portfolio.daily_pnl == expected_pnl
    assert orch._portfolio.weekly_pnl == expected_pnl


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_close_without_position_does_not_raise():
    """CLOSE 대상 포지션이 없어도 예외가 발생하지 않는다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()  # positions 비어 있음

    decision = _make_decision(market="KRW-BTC", direction=SignalDirection.CLOSE)
    await orch._update_portfolio_after_trade(decision, _make_execution_result())
    # 예외 없이 완료되어야 함


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_short_does_not_modify_positions():
    """SHORT 방향은 미구현이므로 positions 에 변화가 없다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()

    decision = _make_decision(direction=SignalDirection.SHORT)
    await orch._update_portfolio_after_trade(decision, _make_execution_result())

    assert len(orch._portfolio.positions) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_updates_total_capital():
    """체결 후 total_capital 이 available_capital + positions_value 로 갱신된다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio(total_capital="10000000", available_capital="10000000")

    decision = _make_decision(direction=SignalDirection.LONG)
    result = _make_execution_result(filled_quantity="0.001", average_price="100000000", fee="500")
    await orch._update_portfolio_after_trade(decision, result)

    expected = orch._portfolio.available_capital + orch._portfolio.positions_value
    assert orch._portfolio.total_capital == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_updates_high_water_mark():
    """total_capital 이 high_water_mark 를 초과하면 high_water_mark 가 갱신된다."""
    orch = make_orchestrator()
    # available_capital 이 충분히 커서 total_capital 이 high_water_mark 를 넘도록 설정
    orch._portfolio = _make_portfolio(total_capital="20000000", available_capital="20000000")
    orch._portfolio.high_water_mark = Decimal("1")  # 매우 낮은 기존 고점

    await orch._update_portfolio_after_trade(
        _make_decision(direction=SignalDirection.LONG),
        _make_execution_result(),
    )

    assert orch._portfolio.high_water_mark == orch._portfolio.total_capital


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_portfolio_increments_trade_count():
    """체결 후 trade_count_today 가 1 증가한다."""
    orch = make_orchestrator()
    orch._portfolio = _make_portfolio()

    before = orch._portfolio.trade_count_today
    await orch._update_portfolio_after_trade(
        _make_decision(direction=SignalDirection.LONG),
        _make_execution_result(),
    )

    assert orch._portfolio.trade_count_today == before + 1

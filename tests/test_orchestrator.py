"""Orchestrator 단위 테스트."""

import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# orchestrator.py 는 절대 임포트(from connections import ...)를 사용하므로
# 테스트 환경에서 해당 모듈들을 sys.modules 에 미리 등록해 ImportError 를 방지한다.
# models 는 실제 src.models 를 사용해 RiskLimitsConfig 등의 타입이 정상 동작하도록 한다.
import src.models as _src_models
import src.risk as _src_risk
import src.risk.risk_rule as _src_risk_rule
import src.risk.rules as _src_risk_rules

sys.modules.setdefault("models", _src_models)
sys.modules.setdefault("risk", _src_risk)
sys.modules.setdefault("risk.risk_rule", _src_risk_rule)
sys.modules.setdefault("risk.rules", _src_risk_rules)

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
    strategy = MagicMock()
    strategy.name = "MacdRsiStochasticStrategy"

    with patch.multiple(
        "src.orchestrator",
        PostgresPool=MagicMock(return_value=pool),
        RedisClient=MagicMock(return_value=redis),
        UpbitAdapter=MagicMock(return_value=adapter),
        MarketDataFeed=MagicMock(return_value=market_feed),
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

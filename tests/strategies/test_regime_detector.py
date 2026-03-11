"""RegimeDetector 단위 테스트.

talib.EMA를 mock하여 EMA 최신값([-1])의 대소 관계를 직접 제어한 뒤,
각 시장 국면이 올바르게 반환되는지 검증한다.
"""

from unittest.mock import patch

import numpy as np
import pytest
from src.models.candle import Candle
from src.strategies.regime_detector import RegimeDetector
from src.utils.constants import MarketRegime

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

_CANDLE_BASE = {
    "type": "candle.1m",
    "code": "KRW-BTC",
    "candle_date_time_utc": "2025-01-02T00:00:00",
    "candle_date_time_kst": "2025-01-02T09:00:00",
    "opening_price": 100_000_000,
    "high_price": 100_000_000,
    "low_price": 100_000_000,
    "trade_price": 100_000_000,
    "candle_acc_trade_volume": 1,
    "candle_acc_trade_price": 100_000_000,
    "timestamp": 1735776000000,
    "stream_type": "REALTIME",
}


def _make_candles(n: int, price: float = 100_000_000) -> list[Candle]:
    """price가 모두 동일한 더미 캔들 n개를 반환한다."""
    base = {**_CANDLE_BASE, "trade_price": price}
    return [Candle.from_dict(base) for _ in range(n)]


def _mock_ema(short: float, mid: float, long: float):
    """talib.EMA가 short/mid/long 순서로 호출될 때 각 값을 마지막 원소로 가진
    배열을 반환하도록 side_effect를 구성한다."""

    def _side_effect(prices, period):
        mapping = {5: short, 20: mid, 40: long}
        value = mapping[period]
        arr = np.zeros(len(prices))
        arr[-1] = value
        return arr

    return _side_effect


# ---------------------------------------------------------------------------
# 초기화
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_regime_is_unknown():
    """config=None일 때 초기 국면은 UNKNOWN이다."""
    detector = RegimeDetector(config=None)
    assert detector.current_regime == MarketRegime.UNKNOWN


@pytest.mark.unit
def test_default_regime_can_be_overridden():
    """default_regime 인수가 current_regime 초기값으로 설정된다."""
    detector = RegimeDetector(config={}, default_regime=MarketRegime.STABLE_BULL)
    assert detector.current_regime == MarketRegime.STABLE_BULL


@pytest.mark.unit
def test_custom_ema_periods_are_stored():
    """config의 EMA 기간이 private 속성에 올바르게 저장된다."""
    detector = RegimeDetector(config={"ema_short_period": 3, "ema_mid_period": 10, "ema_long_period": 30})
    assert detector._ema_short_period == 3
    assert detector._ema_mid_period == 10
    assert detector._ema_long_period == 30


# ---------------------------------------------------------------------------
# 캔들 수 부족 — 이전 국면 유지
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_returns_current_regime_when_insufficient_candles():
    """캔들 수 < 장기 EMA 기간이면 이전 국면을 반환한다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(39)  # ema_long_period=40 미만
    assert detector.detect(candles) == MarketRegime.UNKNOWN


@pytest.mark.unit
def test_detect_does_not_update_regime_when_insufficient_candles():
    """캔들 수 부족 시 current_regime이 변경되지 않는다."""
    detector = RegimeDetector(config={}, default_regime=MarketRegime.STABLE_BULL)
    detector.detect(_make_candles(10))
    assert detector.current_regime == MarketRegime.STABLE_BULL


@pytest.mark.unit
def test_detect_exactly_at_threshold_proceeds(monkeypatch):
    """캔들 수 == 장기 EMA 기간이면 EMA 계산을 진행한다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(40)

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(30, 20, 10)):
        result = detector.detect(candles)

    assert result == MarketRegime.STABLE_BULL


# ---------------------------------------------------------------------------
# NaN 처리
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_returns_current_regime_on_nan():
    """EMA 결과에 NaN이 있으면 이전 국면을 반환한다."""
    detector = RegimeDetector(config={}, default_regime=MarketRegime.STABLE_BEAR)
    candles = _make_candles(40)

    def _nan_ema(prices, _period):
        arr = np.full(len(prices), np.nan)
        return arr

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_nan_ema):
        result = detector.detect(candles)

    assert result == MarketRegime.STABLE_BEAR


# ---------------------------------------------------------------------------
# 6가지 시장 국면 — EMA 대소 관계 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "short,mid,long,expected",
    [
        # short > mid > long → STABLE_BULL (정배열)
        (30, 20, 10, MarketRegime.STABLE_BULL),
        # mid > short > long → END_OF_BULL (단기선 꺾임)
        (20, 30, 10, MarketRegime.END_OF_BULL),
        # mid > long > short → START_OF_BEAR (단기선 장기선 하향 이탈)
        (10, 30, 20, MarketRegime.START_OF_BEAR),
        # long > mid > short → STABLE_BEAR (역배열)
        (10, 20, 30, MarketRegime.STABLE_BEAR),
        # long > short > mid → END_OF_BEAR (단기선 반등)
        (20, 10, 30, MarketRegime.END_OF_BEAR),
        # short > long > mid → START_OF_BULL (단기선 장기선 상향 돌파)
        (30, 10, 20, MarketRegime.START_OF_BULL),
    ],
)
def test_detect_regime_by_ema_order(short, mid, long, expected):
    """EMA 대소 관계에 따라 올바른 시장 국면이 반환된다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(40)

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(short, mid, long)):
        result = detector.detect(candles)

    assert result == expected


# ---------------------------------------------------------------------------
# current_regime 갱신
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_updates_current_regime():
    """detect() 호출 후 current_regime이 반환값으로 갱신된다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(40)

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(10, 20, 30)):
        detector.detect(candles)

    assert detector.current_regime == MarketRegime.STABLE_BEAR


@pytest.mark.unit
def test_detect_regime_changes_across_calls():
    """연속 호출 시 EMA 배열 변화에 따라 국면이 올바르게 전환된다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(40)

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(30, 20, 10)):
        assert detector.detect(candles) == MarketRegime.STABLE_BULL

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(10, 20, 30)):
        assert detector.detect(candles) == MarketRegime.STABLE_BEAR

    assert detector.current_regime == MarketRegime.STABLE_BEAR


# ---------------------------------------------------------------------------
# UNKNOWN — 동일값 등 정의되지 않은 배열
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_returns_unknown_when_ema_values_are_equal():
    """EMA 세 값이 모두 동일하면 UNKNOWN을 반환한다."""
    detector = RegimeDetector(config={})
    candles = _make_candles(40)

    with patch("src.strategies.regime_detector.talib.EMA", side_effect=_mock_ema(10, 10, 10)):
        result = detector.detect(candles)

    assert result == MarketRegime.UNKNOWN

import numpy as np
import structlog
import talib

from ..models import Candle
from ..utils.constants import MarketRegime

logger = structlog.get_logger(__name__)


class RegimeDetector:
    """EMA 배열 정렬을 기반으로 현재 시장 국면(regime)을 감지하는 클래스.

    단기(short), 중기(mid), 장기(long) EMA의 대소 관계를 비교하여
    6가지 시장 국면(STABLE_BULL, END_OF_BULL, START_OF_BEAR,
    STABLE_BEAR, END_OF_BEAR, START_OF_BULL)을 식별한다.

    Attributes:
        _ema_short_period (int): 단기 EMA 기간 (기본값: 5).
        _ema_mid_period (int): 중기 EMA 기간 (기본값: 20).
        _ema_long_period (int): 장기 EMA 기간 (기본값: 40).
    """

    def __init__(self, config: dict, default_regime: MarketRegime = MarketRegime.UNKNOWN):
        """RegimeDetector를 초기화한다.

        Args:
            config (dict): EMA 기간 설정을 담은 딕셔너리.
                - ema_short_period (int): 단기 EMA 기간 (기본값: 5)
                - ema_mid_period (int): 중기 EMA 기간 (기본값: 20)
                - ema_long_period (int): 장기 EMA 기간 (기본값: 40)
            default_regime (MarketRegime): 초기 시장 국면 (기본값: UNKNOWN).
        """
        config = config or {}
        self._current_regime = default_regime

        self._ema_short_period = config.get("ema_short_period", 5)
        self._ema_mid_period = config.get("ema_mid_period", 20)
        self._ema_long_period = config.get("ema_long_period", 40)

    @property
    def current_regime(self) -> MarketRegime:
        """가장 최근에 감지된 시장 국면을 반환한다."""
        return self._current_regime

    def detect(self, candles: list[Candle]) -> MarketRegime:
        """캔들 목록을 분석하여 현재 시장 국면을 감지하고 반환한다.

        EMA 배열의 마지막 값(최신 값)을 비교하여 시장 국면을 결정한다.
        캔들 수가 장기 EMA 기간보다 적으면 이전 국면을 유지한다.

        Args:
            candles (list[Candle]): 분석할 캔들 목록. 오래된 것부터 최신 순으로 정렬되어야 한다.

        Returns:
            MarketRegime: 감지된 시장 국면.
        """
        if len(candles) < self._ema_long_period:
            logger.warning(
                "캔들 수가 장기 EMA 기간보다 적어 이전 국면을 유지합니다.",
                candle_count=len(candles),
                required=self._ema_long_period,
            )
            return self._current_regime

        prices = np.array([float(candle.trade_price) for candle in candles], dtype=np.float64)

        short = talib.EMA(prices, self._ema_short_period)[-1]
        mid = talib.EMA(prices, self._ema_mid_period)[-1]
        long = talib.EMA(prices, self._ema_long_period)[-1]

        # NaN 체크: talib은 초기 기간 동안 NaN을 반환할 수 있음
        if np.isnan(short) or np.isnan(mid) or np.isnan(long):
            logger.warning(
                "EMA 계산 결과에 NaN이 포함되어 이전 국면을 유지합니다.",
                ema_short=short,
                ema_mid=mid,
                ema_long=long,
            )
            return self._current_regime

        # 단기 > 중기 > 장기 -> 안정적인 상승 추세
        if short > mid > long:
            regime = MarketRegime.STABLE_BULL
        # 중기 > 단기 > 장기 -> 상승 추세의 끝
        elif mid > short > long:
            regime = MarketRegime.END_OF_BULL
        # 중기 > 장기 > 단기 -> 하락 추세의 시작
        elif mid > long > short:
            regime = MarketRegime.START_OF_BEAR
        # 장기 > 중기 > 단기 -> 안정적인 하락 추세
        elif long > mid > short:
            regime = MarketRegime.STABLE_BEAR
        # 장기 > 단기 > 중기 -> 하락 추세의 끝
        elif long > short > mid:
            regime = MarketRegime.END_OF_BEAR
        # 단기 > 장기 > 중기 -> 상승 추세의 시작
        elif short > long > mid:
            regime = MarketRegime.START_OF_BULL
        else:
            regime = MarketRegime.UNKNOWN

        self._current_regime = regime
        return self._current_regime

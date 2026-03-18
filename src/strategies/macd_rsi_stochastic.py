from ..models import Candle, PortfolioState, TradeCandidate
from ..repositories import SignalRepository
from ..utils.constants import MarketRegime
from .base_strategy import BaseStrategy
from .signal_aggregator import SignalAggregator


class MacdRsiStochasticStrategy(BaseStrategy):
    def __init__(self, config: dict, aggregator: SignalAggregator, signal_repository: SignalRepository):
        super().__init__(config, aggregator, signal_repository)

        self.macd_upper_period = config.get("macd_upper_period", 3)
        self.macd_mid_period = config.get("macd_mid_period", 5)
        self.macd_lower_period = config.get("macd_lower_period", 8)
        self.macd_signal_period = config.get("macd_signal_period", 9)

        self.rsi_period = config.get("rsi_period", 14)
        self.rsi_signal_period = config.get("rsi_signal_period", 9)
        self.rsi_overbought = config.get("rsi_overbought", 75)
        self.rsi_oversold = config.get("rsi_oversold", 25)

        self.stoch_k_len = config.get("stoch_k_len", 10)
        self.stoch_k_smooth = config.get("stoch_k_smooth", 3)
        self.stoch_d_smooth = config.get("stoch_d_smooth", 3)
        self.stoch_overbought = config.get("stoch_overbought", 80)
        self.stoch_oversold = config.get("stoch_oversold", 20)

    async def evaluate(
        self, candles: list[Candle], regime: MarketRegime, portfolio: PortfolioState
    ) -> TradeCandidate | None:
        pass

    def get_supported_regimes(self) -> list[MarketRegime]:
        return [
            MarketRegime.STABLE_BULL,
            MarketRegime.END_OF_BULL,
            MarketRegime.START_OF_BEAR,
            MarketRegime.STABLE_BEAR,
            MarketRegime.END_OF_BEAR,
            MarketRegime.START_OF_BULL,
        ]

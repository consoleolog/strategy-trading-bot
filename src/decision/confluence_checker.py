from decimal import Decimal

import structlog

from ..models import Signal, TradeCandidate
from ..utils.constants import SignalDirection

logger = structlog.get_logger(__name__)


class ConfluenceChecker:
    """여러 시그널의 방향 일치(컨플루언스)를 검증하여 거래 후보를 생성하는 클래스.

    최소 ``min_signals``개 이상의 시그널이 동일한 방향을 가리킬 때만
    :class:`~models.trade_candidate.TradeCandidate`를 반환한다.
    ``HOLD`` 방향은 집계에서 제외하며, 가장 많은 시그널이 모인 방향을 채택한다.

    Attributes:
        min_signals (int): 컨플루언스 성립에 필요한 최소 시그널 수 (기본값: 6).
    """

    def __init__(self, min_signals: int = 6):
        """ConfluenceChecker를 초기화한다.

        Args:
            min_signals: 거래 후보 생성에 필요한 최소 동일 방향 시그널 수.
        """
        self.min_signals = min_signals

    def check(self, signals: list[Signal]) -> TradeCandidate | None:
        """시그널 목록에서 방향 컨플루언스를 확인하고 거래 후보를 반환한다.

        동일 방향 시그널이 ``min_signals`` 개 이상 모이면 해당 방향으로
        :class:`~models.trade_candidate.TradeCandidate`를 생성한다.
        조건을 충족하지 못하면 ``None``을 반환한다.

        Args:
            signals: 평가할 시그널 목록.

        Returns:
            컨플루언스 조건을 충족한 경우 거래 후보 객체, 그렇지 않으면 ``None``.
        """
        if len(signals) < self.min_signals:
            return None

        # 방향별로 시그널을 분류
        direction_counts = {}
        for signal in signals:
            direction = signal.direction
            if direction not in direction_counts:
                direction_counts[direction] = []
            direction_counts[direction].append(signal)

        # 가장 많은 시그널이 모인 방향(다수결) 탐색
        best_direction = None
        best_signals = []

        for direction, dir_signals in direction_counts.items():
            # HOLD 방향은 컨플루언스 집계에서 제외
            if direction == SignalDirection.HOLD:
                continue
            if len(dir_signals) >= self.min_signals and len(dir_signals) > len(best_signals):
                best_direction = direction
                best_signals = dir_signals

        # 유효한 다수결 방향이 없으면 종료
        if not best_direction or len(best_signals) < self.min_signals:
            return None

        # 시그널별 제안 가격 수집 (0 또는 None 제외)
        entry_prices = [s.entry_price for s in best_signals if s.entry_price]
        stop_losses = [s.stop_loss for s in best_signals if s.stop_loss]
        take_profits = [s.take_profit for s in best_signals if s.take_profit]

        # 진입 가격: 유효한 값들의 평균, 없으면 0
        suggested_entry = sum(entry_prices) / len(entry_prices) if entry_prices else Decimal("0")
        # 손절 가격: 가장 보수적인(낮은) 값 채택
        suggested_stop = min(stop_losses) if stop_losses else Decimal("0")
        # 익절 가격: 가장 높은 목표가 채택
        suggested_tp = max(take_profits) if take_profits else Decimal("0")

        logger.info(f"Confluence found: {best_direction.value} {best_signals[0].market} ({len(best_signals)} signals")

        return TradeCandidate(
            market=best_signals[0].symbol,
            direction=best_direction,
            contributing_signals=best_signals,
            suggested_entry=suggested_entry,
            suggested_stop_loss=suggested_stop,
            suggested_take_profit=suggested_tp,
        )

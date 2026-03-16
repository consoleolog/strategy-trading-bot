import copy

import structlog

from ..models import Signal

logger = structlog.get_logger(__name__)


class SignalAggregator:
    """
    마켓별 시그널을 수집·관리하는 집계기.

    여러 전략에서 발생한 Signal을 마켓 코드 기준으로 분류하여 저장하고,
    조회 및 초기화 기능을 제공합니다.

    Attributes:
        _signals: 마켓 코드를 키로, 해당 마켓의 시그널 목록을 값으로 갖는 딕셔너리.
    """

    def __init__(self):
        self._signals: dict[str, list[Signal]] = {}

    def add_signal(self, signal: Signal) -> None:
        """
        시그널을 마켓별로 추가합니다.

        Args:
            signal: 추가할 시그널 객체.
        """
        if signal.market not in self._signals:
            self._signals[signal.market] = []

        self._signals[signal.market].append(signal)
        logger.debug(
            "signal.added", strategy_id=signal.strategy_id, direction=signal.direction.value, market=signal.market
        )

    def get_signals(self, market: str) -> list[Signal]:
        """
        특정 마켓의 시그널 목록을 반환합니다.

        Args:
            market: 조회할 마켓 코드 (예: KRW-BTC).

        Returns:
            해당 마켓의 시그널 목록. 없으면 빈 리스트 반환.
        """
        return copy.deepcopy(self._signals.get(market, []))

    def get_all_signals(self) -> dict[str, list[Signal]]:
        """
        전체 마켓의 시그널 딕셔너리를 반환합니다.

        Returns:
            마켓 코드를 키로, 시그널 목록을 값으로 갖는 딕셔너리.
        """
        return self._signals

    def clear(self) -> None:
        """수집된 모든 시그널을 초기화합니다."""
        self._signals.clear()

    @property
    def signal_count(self) -> int:
        """전체 마켓에 걸쳐 수집된 시그널의 총 개수."""
        return sum(len(signals) for signals in self._signals.values())

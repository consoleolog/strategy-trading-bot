from dataclasses import dataclass, field
from datetime import datetime

from .constants import SignalDirection, SignalType, SignalValue


@dataclass
class Signal:
    """
    전략 및 지표에 의해 생성된 트레이딩 신호(Signal) 모델

    Attributes:
        strategy_id (str): 신호를 생성한 전략의 식별자
        indicator_id (str): 신호를 생성한 지표의 식별자
        type (SignalType): 신호 종류 (CROSS_OVER, THRESHOLD_CROSS, LEVEL_BREAK)
        value (SignalValue): 신호의 구체적인 값 (GOLDEN_CROSS, DEAD_CROSS 등)
        direction (SignalDirection): 포지션 방향 (LONG, SHORT, CLOSE, HOLD)
        market (str): 대상 마켓 코드 (예: KRW-BTC)
        timeframe (str): 신호가 생성된 타임프레임 (예: 1m, 5m, 1h)
        timestamp (datetime): 신호 생성 시각
        metadata (dict): 추가적인 분석 데이터 또는 파라미터 정보
    """

    strategy_id: str
    indicator_id: str
    type: SignalType
    value: SignalValue
    direction: SignalDirection
    market: str
    timeframe: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = SignalType(self.type)
        if isinstance(self.value, str):
            self.value = SignalValue(self.value)
        if isinstance(self.direction, str):
            self.direction = SignalDirection(self.direction)
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        """딕셔너리 데이터를 Signal 객체로 변환합니다."""
        return cls(
            strategy_id=data.get("strategy_id"),
            indicator_id=data.get("indicator_id"),
            type=data.get("type"),
            value=data.get("value"),
            direction=data.get("direction"),
            market=data.get("market"),
            timeframe=data.get("timeframe"),
            timestamp=data.get("timestamp", datetime.now()),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        """Signal 객체를 딕셔너리로 변환합니다."""
        return {
            "strategy_id": self.strategy_id,
            "indicator_id": self.indicator_id,
            "type": self.type,
            "value": self.value,
            "direction": self.direction,
            "market": self.market,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from ..util.helpers import parse_timeframe
from .constants import CandleType, StreamType


@dataclass
class Candle:
    """
    업비트 WebSocket 캔들(Candle) 응답 데이터 모델

    Attributes:
        type (str): 캔들 종류 (예: candle.1m, candle.5m 등)
        code (str): 마켓 코드 (예: KRW-BTC)
        candle_date_time_utc (datetime): 캔들 기준 시각 (UTC 기준, ISO 8601 포맷)
        candle_date_time_kst (datetime): 캔들 기준 시각 (KST 기준, ISO 8601 포맷)
        opening_price (Decimal): 시가
        high_price (Decimal): 고가
        low_price (Decimal): 저가
        trade_price (Decimal): 종가 (현재가)
        candle_acc_trade_volume (Decimal): 해당 캔들의 누적 거래량
        candle_acc_trade_price (Decimal): 해당 캔들의 누적 거래 금액
        timestamp (int): 타임스탬프 (밀리초 단위)
        stream_type (str): 스트림 타입 (SNAPSHOT: 스냅샷, REALTIME: 실시간)
    """

    type: CandleType
    code: str
    candle_date_time_utc: datetime
    candle_date_time_kst: datetime
    opening_price: Decimal
    high_price: Decimal
    low_price: Decimal
    trade_price: Decimal
    candle_acc_trade_volume: Decimal
    candle_acc_trade_price: Decimal
    timestamp: int
    stream_type: StreamType

    def __post_init__(self):
        for field_name in [
            "opening_price",
            "high_price",
            "low_price",
            "trade_price",
            "candle_acc_trade_volume",
            "candle_acc_trade_price",
        ]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        for field_name in ["candle_date_time_utc", "candle_date_time_kst"]:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, datetime.fromisoformat(value))

        if isinstance(self.type, str):
            self.type = CandleType(self.type)
        if isinstance(self.stream_type, str):
            self.stream_type = StreamType(self.stream_type)

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        """딕셔너리 데이터를 Candle 객체로 변환합니다."""
        return cls(
            type=data.get("type"),
            code=data.get("code"),
            candle_date_time_utc=data.get("candle_date_time_utc"),
            candle_date_time_kst=data.get("candle_date_time_kst"),
            opening_price=data.get("opening_price"),
            high_price=data.get("high_price"),
            low_price=data.get("low_price"),
            trade_price=data.get("trade_price"),
            candle_acc_trade_volume=data.get("candle_acc_trade_volume"),
            candle_acc_trade_price=data.get("candle_acc_trade_price"),
            timestamp=data.get("timestamp"),
            stream_type=data.get("stream_type"),
        )

    @property
    def is_closed(self) -> bool:
        """캔들 기간이 종료되었는지 여부를 반환합니다.

        업비트 WebSocket은 is_closed 필드를 제공하지 않으므로,
        candle_date_time_utc + interval <= 현재 UTC 시각으로 판단합니다.
        """
        candle_close_time = self.candle_date_time_utc + parse_timeframe(self.type.value)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        return now_utc >= candle_close_time

    def to_dict(self) -> dict:
        """Candle 객체를 딕셔너리로 변환합니다."""
        return {
            "type": self.type,
            "code": self.code,
            "candle_date_time_utc": self.candle_date_time_utc,
            "candle_date_time_kst": self.candle_date_time_kst,
            "opening_price": self.opening_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "trade_price": self.trade_price,
            "candle_acc_trade_volume": self.candle_acc_trade_volume,
            "candle_acc_trade_price": self.candle_acc_trade_price,
            "timestamp": self.timestamp,
            "stream_type": self.stream_type,
        }

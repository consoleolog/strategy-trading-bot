from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..util.constants import AskBid, ChangeDirection, MarketState, StreamType


@dataclass
class Ticker:
    """
    업비트 WebSocket 현재가(Ticker) 응답 데이터 모델

    Attributes:
        type (str): 데이터 항목 (ticker 고정)
        code (str): 마켓 코드 (예: KRW-BTC)
        opening_price (Decimal): 시가
        high_price (Decimal): 고가
        low_price (Decimal): 저가
        trade_price (Decimal): 현재가 (종가)
        prev_closing_price (Decimal): 전일 종가
        change (ChangeDirection): 전일 대비 변동 방향 (RISE, EVEN, FALL)
        change_price (Decimal): 전일 대비 변동액의 절대값
        signed_change_price (Decimal): 전일 대비 변동액
        change_rate (Decimal): 전일 대비 등락율의 절대값
        signed_change_rate (Decimal): 전일 대비 등락율
        trade_volume (Decimal): 가장 최근 거래량
        acc_trade_volume (Decimal): 누적 거래량 (UTC 0시 기준)
        acc_trade_volume_24h (Decimal): 24시간 누적 거래량
        acc_trade_price (Decimal): 누적 거래대금 (UTC 0시 기준)
        acc_trade_price_24h (Decimal): 24시간 누적 거래대금
        trade_date (datetime): 최근 거래 일자 (UTC, yyyyMMdd)
        trade_time (datetime): 최근 거래 시각 (UTC, HHmmss)
        trade_timestamp (int): 체결 타임스탬프 (ms)
        ask_bid (AskBid): 매수/매도 구분 (ASK: 매도, BID: 매수)
        acc_ask_volume (Decimal): 누적 매도량
        acc_bid_volume (Decimal): 누적 매수량
        highest_52_week_price (Decimal | None): 52주 최고가 (신규 상장 등 데이터 부재 시 None)
        highest_52_week_date (datetime | None): 52주 최고가 달성일 (yyyy-MM-dd, 데이터 부재 시 None)
        lowest_52_week_price (Decimal | None): 52주 최저가 (신규 상장 등 데이터 부재 시 None)
        lowest_52_week_date (datetime | None): 52주 최저가 달성일 (yyyy-MM-dd, 데이터 부재 시 None)
        market_state (MarketState): 거래 상태 (ACTIVE, PREVIEW, DELISTED)
        timestamp (int): 타임스탬프 (ms)
        stream_type (StreamType): 스트림 타입 (SNAPSHOT, REALTIME)
    """

    type: str
    code: str
    opening_price: Decimal
    high_price: Decimal
    low_price: Decimal
    trade_price: Decimal
    prev_closing_price: Decimal
    change: ChangeDirection
    change_price: Decimal
    signed_change_price: Decimal
    change_rate: Decimal
    signed_change_rate: Decimal
    trade_volume: Decimal
    acc_trade_volume: Decimal
    acc_trade_volume_24h: Decimal
    acc_trade_price: Decimal
    acc_trade_price_24h: Decimal
    trade_date: datetime
    trade_time: datetime
    trade_timestamp: int
    ask_bid: AskBid
    acc_ask_volume: Decimal
    acc_bid_volume: Decimal
    highest_52_week_price: Decimal | None
    highest_52_week_date: datetime | None
    lowest_52_week_price: Decimal | None
    lowest_52_week_date: datetime | None
    market_state: MarketState
    timestamp: int
    stream_type: StreamType

    def __post_init__(self):
        for field_name in [
            "opening_price",
            "high_price",
            "low_price",
            "trade_price",
            "prev_closing_price",
            "change_price",
            "signed_change_price",
            "change_rate",
            "signed_change_rate",
            "trade_volume",
            "acc_trade_volume",
            "acc_trade_volume_24h",
            "acc_trade_price",
            "acc_trade_price_24h",
            "acc_ask_volume",
            "acc_bid_volume",
        ]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        for field_name in ["highest_52_week_price", "lowest_52_week_price"]:
            value = getattr(self, field_name)
            if value is not None and isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.trade_date, str):
            self.trade_date = datetime.strptime(self.trade_date, "%Y%m%d")
        if isinstance(self.trade_time, str):
            self.trade_time = datetime.strptime(self.trade_time, "%H%M%S")
        if isinstance(self.highest_52_week_date, str):
            self.highest_52_week_date = datetime.fromisoformat(self.highest_52_week_date)
        if isinstance(self.lowest_52_week_date, str):
            self.lowest_52_week_date = datetime.fromisoformat(self.lowest_52_week_date)

        if isinstance(self.change, str):
            self.change = ChangeDirection(self.change)
        if isinstance(self.ask_bid, str):
            self.ask_bid = AskBid(self.ask_bid)
        if isinstance(self.market_state, str):
            self.market_state = MarketState(self.market_state)
        if isinstance(self.stream_type, str):
            self.stream_type = StreamType(self.stream_type)

    @classmethod
    def from_dict(cls, data: dict) -> "Ticker":
        """딕셔너리 데이터를 Ticker 객체로 변환합니다."""
        return cls(
            type=data.get("type"),
            code=data.get("code"),
            opening_price=data.get("opening_price"),
            high_price=data.get("high_price"),
            low_price=data.get("low_price"),
            trade_price=data.get("trade_price"),
            prev_closing_price=data.get("prev_closing_price"),
            change=data.get("change"),
            change_price=data.get("change_price"),
            signed_change_price=data.get("signed_change_price"),
            change_rate=data.get("change_rate"),
            signed_change_rate=data.get("signed_change_rate"),
            trade_volume=data.get("trade_volume"),
            acc_trade_volume=data.get("acc_trade_volume"),
            acc_trade_volume_24h=data.get("acc_trade_volume_24h"),
            acc_trade_price=data.get("acc_trade_price"),
            acc_trade_price_24h=data.get("acc_trade_price_24h"),
            trade_date=data.get("trade_date"),
            trade_time=data.get("trade_time"),
            trade_timestamp=data.get("trade_timestamp"),
            ask_bid=data.get("ask_bid"),
            acc_ask_volume=data.get("acc_ask_volume"),
            acc_bid_volume=data.get("acc_bid_volume"),
            highest_52_week_price=data.get("highest_52_week_price"),
            highest_52_week_date=data.get("highest_52_week_date"),
            lowest_52_week_price=data.get("lowest_52_week_price"),
            lowest_52_week_date=data.get("lowest_52_week_date"),
            market_state=data.get("market_state"),
            timestamp=data.get("timestamp"),
            stream_type=data.get("stream_type"),
        )

    def to_dict(self) -> dict:
        """Ticker 객체를 딕셔너리로 변환합니다."""
        return {
            "type": self.type,
            "code": self.code,
            "opening_price": self.opening_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "trade_price": self.trade_price,
            "prev_closing_price": self.prev_closing_price,
            "change": self.change,
            "change_price": self.change_price,
            "signed_change_price": self.signed_change_price,
            "change_rate": self.change_rate,
            "signed_change_rate": self.signed_change_rate,
            "trade_volume": self.trade_volume,
            "acc_trade_volume": self.acc_trade_volume,
            "acc_trade_volume_24h": self.acc_trade_volume_24h,
            "acc_trade_price": self.acc_trade_price,
            "acc_trade_price_24h": self.acc_trade_price_24h,
            "trade_date": self.trade_date,
            "trade_time": self.trade_time,
            "trade_timestamp": self.trade_timestamp,
            "ask_bid": self.ask_bid,
            "acc_ask_volume": self.acc_ask_volume,
            "acc_bid_volume": self.acc_bid_volume,
            "highest_52_week_price": self.highest_52_week_price,
            "highest_52_week_date": self.highest_52_week_date,
            "lowest_52_week_price": self.lowest_52_week_price,
            "lowest_52_week_date": self.lowest_52_week_date,
            "market_state": self.market_state,
            "timestamp": self.timestamp,
            "stream_type": self.stream_type,
        }

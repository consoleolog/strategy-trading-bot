from enum import Enum

# =============================================================================
# Candle Enum
# =============================================================================


class CandleType(Enum):
    """
    업비트 캔들 종류 (WebSocket 응답의 type 필드 대응)

    Attributes:
        SECOND: 초봉 (candle.1s)
        MINUTE: 1분봉 (candle.1m)
        MINUTE_3: 3분봉 (candle.3m)
        MINUTE_5: 5분봉 (candle.5m)
        MINUTE_10: 10분봉 (candle.10m)
        MINUTE_15: 15분봉 (candle.15m)
        HALF_HOUR: 30분봉 (candle.30m)
        HOUR: 60분봉 (candle.60m)
        HOUR_4: 240분봉 (candle.240m)
    """

    SECOND = "candle.1s"
    MINUTE = "candle.1m"
    MINUTE_3 = "candle.3m"
    MINUTE_5 = "candle.5m"
    MINUTE_10 = "candle.10m"
    MINUTE_15 = "candle.15m"
    HALF_HOUR = "candle.30m"
    HOUR = "candle.60m"
    HOUR_4 = "candle.240m"


# =============================================================================
# Ticker Enum
# =============================================================================


class ChangeDirection(Enum):
    """
    전일 종가 대비 가격 변동 방향

    Attributes:
        RISE: 상승
        EVEN: 보합
        FALL: 하락
    """

    RISE = "RISE"
    EVEN = "EVEN"
    FALL = "FALL"


class MarketState(Enum):
    """
    거래 상태

    Attributes:
        PREVIEW: 입금지원
        ACTIVE: 거래지원가능
        DELISTED: 거래지원종료
    """

    PREVIEW = "PREVIEW"
    ACTIVE = "ACTIVE"
    DELISTED = "DELISTED"


class AskBid(Enum):
    """
    매수/매도 구분

    Attributes:
        ASK: 매도
        BID: 매수
    """

    ASK = "ASK"
    BID = "BID"


class StreamType(Enum):
    """
    스트림 타입

    Attributes:
        SNAPSHOT: 스냅샷
        REALTIME: 실시간
    """

    SNAPSHOT = "SNAPSHOT"
    REALTIME = "REALTIME"

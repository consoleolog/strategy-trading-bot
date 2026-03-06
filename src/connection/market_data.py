import asyncio
from collections.abc import Callable

import structlog

logger = structlog.get_logger(__name__)


class MarketDataFeed:
    """
    업비트 WebSocket 시장 데이터 수신 클래스

    지정된 마켓 코드와 스트림 타입을 구독하고, 수신된 데이터를
    콜백 함수를 통해 상위 레이어로 전달합니다.
    연결 끊김 시 지수 백오프(exponential backoff) 방식으로 자동 재연결합니다.

    Attributes:
        WS_URL_QUOTATION: 업비트 공개 시세 WebSocket 엔드포인트
        WS_URL_EXCHANGE: 업비트 인증 전용 WebSocket 엔드포인트 (자산/주문 조회)
    """

    WS_URL_QUOTATION = "wss://api.upbit.com/websocket/v1"
    WS_URL_EXCHANGE = f"{WS_URL_QUOTATION}/private"

    def __init__(
        self,
        codes: list[str],
        types: list[str],
        on_ticker: Callable | None = None,
        on_candle: Callable | None = None,
        on_candle_close: Callable | None = None,
        reconnect_delay: int = 5,
        max_reconnect_attempts: int = 10,
    ):
        """
        Args:
            codes: 구독할 마켓 코드 목록 (예: ["KRW-BTC", "KRW-ETH"])
            types: 구독할 스트림 타입 목록 (예: ["ticker"], ["candle.1m"])
            on_ticker: 티커 데이터 수신 시 호출할 콜백
            on_candle: 캔들 데이터 수신 시 호출할 콜백
            on_candle_close: 캔들 확정(봉 마감) 시 호출할 콜백
            reconnect_delay: 재연결 기본 대기 시간(초, 기본값: 5)
            max_reconnect_attempts: 최대 재연결 시도 횟수 (기본값: 10)
        """
        self.codes = [c.upper() for c in codes]
        self.types = types

        # Callbacks
        self.on_ticker = on_ticker
        self.on_candle = on_candle
        self.on_candle_close = on_candle_close

        # Reconnection settings
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts

        # State
        self._ws = None
        self._running = False
        self._reconnect_count = 0

    async def connect(self) -> None:
        """WebSocket에 연결하고 메시지 수신 루프를 시작합니다.

        연결 오류 발생 시 reconnect_delay 기반 지수 백오프로 재연결을 시도하며,
        max_reconnect_attempts 초과 시 루프를 종료합니다.
        """
        self._running = True
        logger.info("🚀 MarketDataFeed started", codes=len(self.codes))

        while self._running:
            try:
                # TODO: add main logic
                pass
            except Exception as error:
                logger.exception("💥 WebSocket 오류 발생", error=str(error))

                if self._running:
                    self._reconnect_count += 1
                    if self._reconnect_count > self.max_reconnect_attempts:
                        logger.error("❌ 최대 재연결 횟수 초과, MarketDataFeed closed")
                        break

                    delay = self.reconnect_delay * min(self._reconnect_count, 5)
                    logger.info("🔄 재연결 대기 중", delay=delay, attempt=self._reconnect_count)
                    await asyncio.sleep(delay)

    async def disconnect(self) -> None:
        """WebSocket 연결을 종료하고 수신 루프를 중단합니다."""
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("🛑 MarketDataFeed disconnected")

    @property
    def is_connected(self) -> bool:
        """WebSocket이 현재 연결된 상태인지 반환합니다."""
        return self._ws is not None and self._ws.open

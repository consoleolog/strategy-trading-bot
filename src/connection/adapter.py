import hashlib
import uuid
from decimal import Decimal
from urllib.parse import unquote, urlencode

import aiohttp
import jwt
import structlog

from ..model import Candle, Order
from ..util.constants import CandleType, OrderSide, OrderType, SmpType, StreamType, Timeframe, TimeInForce
from ..util.errors import error_handler

logger = structlog.get_logger(__name__)


class UpbitAdapter:
    def __init__(self, config: dict):
        self.base_url = "https://api.upbit.com/v1"

        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.is_test = config.get("is_test", False)

        self._session: aiohttp.ClientSession | None = None

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    async def connect(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            logger.info("🔗 Connected to Upbit")

    async def disconnect(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("🔌 Disconnected from Upbit")

    async def _ensure_session(self) -> None:
        if self._session is None or self._session.closed:
            await self.connect()

    # ========================================================================
    # REQUEST HELPERS
    # ========================================================================

    def _sign_request(self, params: dict | None = None) -> str:
        payload = {
            "access_key": self.api_key,
            "nonce": str(uuid.uuid4()),
        }
        if params:
            query_string = unquote(urlencode(params, doseq=True)).encode("utf-8")
            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()

            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        return jwt.encode(payload, self.api_secret, algorithm="HS256")

    @error_handler
    async def _request(
        self, method: str, endpoint: str, params: dict | None = None, headers: dict | None = None, signed: bool = False
    ) -> aiohttp.client.ClientResponse:
        await self._ensure_session()

        params = params or {}
        headers = headers or {}
        if signed:
            headers["Authorization"] = f"Bearer {self._sign_request(params)}"

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                return await self._session.get(url, headers=headers, params=params)
            elif method == "POST":
                return await self._session.post(url, headers=headers, json=params)
            elif method == "DELETE":
                return await self._session.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unknown method: {method}")
        except aiohttp.ClientError as error:
            logger.exception("❌ 요청 실패", error=str(error))
            raise

    # ========================================================================
    # CANDLE DATA
    # ========================================================================

    async def get_candles(
        self, market: str, timeframe: Timeframe = Timeframe.DAY, count: int = 200, to: str | None = None
    ) -> list[Candle]:
        """
        캔들 조회 (괴거 -> 최신 순)

        Args:
            market: 조회하고자 하는 페어(거래쌍)
            timeframe: 조회하고자 하는 기간
            count: 조회하고자 하는 캔들의 개수. 최대 200개의 캔들 조회를 지원하며, 기본값은 200입니다.
            to: 조회 기간의 종료 시각.
                지정한 시각 이전 캔들을 조회합니다. 미지정시 요청 시각을 기준으로 최근 캔들이 조회됩니다.

                ISO 8601 형식의 datetime으로 아래와 같이 요청 할 수 있습니다.
                실제 요청 시에는 공백 및 특수문자가 정상적으로 처리되도록 URL 인코딩을 수행해야 합니다.
                [예시]
                2025-06-24T04:56:53Z
                2025-06-24 04:56:53
                2025-06-24T13:56:53+09:00
        """
        params = {"market": market, "count": count}
        if to:
            params["to"] = to
        response = await self._request("GET", f"/candles/{timeframe.value}", params=params)
        # response 는 최신 -> 과거 데이터이기 때문에 슬라이싱으로 과거 -> 최신으로 정렬
        candles = [
            Candle(
                type=self._timeframe_to_candle_type(timeframe),
                code=r.get("market"),
                candle_date_time_utc=r.get("candle_date_time_utc"),
                candle_date_time_kst=r.get("candle_date_time_kst"),
                opening_price=r.get("opening_price"),
                high_price=r.get("high_price"),
                low_price=r.get("low_price"),
                trade_price=r.get("trade_price"),
                candle_acc_trade_volume=r.get("candle_acc_trade_volume"),
                candle_acc_trade_price=r.get("candle_acc_trade_price"),
                timestamp=r.get("timestamp"),
                stream_type=StreamType.SNAPSHOT,
            )
            for r in response[::-1]
        ]
        return candles

    @staticmethod
    def _timeframe_to_candle_type(timeframe: Timeframe) -> CandleType:
        timeframe_to_candle_type_map = {
            Timeframe.SECOND: CandleType.SECOND,
            Timeframe.MINUTE_1: CandleType.MINUTE_1,
            Timeframe.MINUTE_3: CandleType.MINUTE_3,
            Timeframe.MINUTE_5: CandleType.MINUTE_5,
            Timeframe.HALF_HOUR: CandleType.HALF_HOUR,
            Timeframe.HOUR: CandleType.HOUR,
            Timeframe.HOUR_4: CandleType.HOUR_4,
        }
        return timeframe_to_candle_type_map.get(timeframe, Timeframe.HOUR_4)

    # ========================================================================
    # ORDER OPERATIONS
    # ========================================================================

    async def create_order(
        self,
        market: str,
        side: OrderSide,
        ord_type: OrderType,
        volume: Decimal | None = None,
        price: Decimal | None = None,
        time_in_force: TimeInForce | None = None,
        smp_type: SmpType | None = None,
        identifier: str | None = None,
    ) -> Order:
        """
        주문 생성 (POST /v1/orders)

        Args:
            market: 마켓 ID (필수, 예: KRW-BTC)
            side: 주문 종류 (bid: 매수, ask: 매도) (필수)
            ord_type: 주문 유형 (limit: 지정가, price: 시장가 매수, market: 시장가 매도, best: 최유리 지정가) (필수)
            volume: 주문 수량 (지정가 전체, 시장가 매도, 최유리 매도시 필수)
            price: 주문 가격 또는 총액 (지정가 전체, 시장가 매수, 최유리 매수시 필수)
            time_in_force: 주문 체결 조건 (ioc, fok, post_only)
                - best 주문 시 ioc 또는 fok 필수
                - post_only는 limit 주문에서만 가능하며 smp_type과 함께 사용 불가
            smp_type: 자전거래 체결 방지 옵션 (cancel_maker, cancel_taker, reduce)
            identifier: 사용자 지정 주문 ID (유니크해야 함, 최대 64자)

        Returns:
            Order: 생성된 주문의 상세 정보

        Raises:
            ValueError: 필수 파라미터 누락 또는 잘못된 주문 유형 설정 시 발생
        """
        # 주문 유형별 유효성 검사
        if ord_type == OrderType.LIMIT:
            if volume is None or price is None:
                raise ValueError("지정가 주문(limit)은 `volume`과 `price`가 모두 필수입니다.")
        elif ord_type == OrderType.MARKET:
            if side != OrderSide.ASK:
                raise ValueError("시장가 매도 주문(market)은 `side=ask`여야 합니다.")
            if volume is None:
                raise ValueError("시장가 매도 주문(market)은 `volume`이 필수입니다.")
            if price is not None:
                raise ValueError("시장가 매도 주문(market)은 `price`를 입력할 수 없습니다.")
        elif ord_type == OrderType.PRICE:
            if side != OrderSide.BID:
                raise ValueError("시장가 매수 주문(price)은 `side=bid`여야 합니다.")
            if price is None:
                raise ValueError("시장가 매수 주문(price)은 `price`(총액)가 필수입니다.")
            if volume is not None:
                raise ValueError("시장가 매수 주문(price)은 `volume`을 입력할 수 없습니다.")
        elif ord_type == OrderType.BEST:
            if time_in_force not in [TimeInForce.IOC, TimeInForce.FOK]:
                raise ValueError("최유리 지정가 주문(best)은 `time_in_force`를 `ioc` 또는 `fok`로 설정해야 합니다.")
            if side == OrderSide.BID:
                if price is None:
                    raise ValueError("최유리 매수 주문(best)은 `price`(총액)가 필수입니다.")
                if volume is not None:
                    raise ValueError("최유리 매수 주문(best)은 `volume`을 입력할 수 없습니다.")
            else:  # ASK
                if volume is None:
                    raise ValueError("최유리 매도 주문(best)은 `volume`이 필수입니다.")
                if price is not None:
                    raise ValueError("최유리 매도 주문(best)은 `price`를 입력할 수 없습니다.")

        if time_in_force == TimeInForce.POST_ONLY:
            if ord_type != OrderType.LIMIT:
                raise ValueError("`post_only` 옵션은 지정가 주문(limit)에서만 사용할 수 있습니다.")
            if smp_type is not None:
                raise ValueError("`post_only` 옵션은 `smp_type` 옵션과 함께 사용할 수 없습니다.")

        params = {"market": market, "side": side.value, "ord_type": ord_type.value}

        if volume:
            params["volume"] = volume.to_eng_string()
        if price:
            params["price"] = price.to_eng_string()
        if time_in_force:
            params["time_in_force"] = time_in_force.value
        if identifier:
            params["identifier"] = identifier
        if smp_type:
            params["smp_type"] = smp_type.value

        endpoint = f"/orders{'/test' if self.is_test else ''}"

        response = await self._request("POST", endpoint, params=params, signed=True)
        order = Order.from_dict(response)
        return order

    async def limit_order(
        self,
        market: str,
        side: OrderSide,
        volume: Decimal,
        price: Decimal,
        time_in_force: TimeInForce | None = None,
        smp_type: SmpType | None = None,
        identifier: str | None = None,
    ) -> Order:
        """
        지정가 매도/매수 주문

        Args:
            market: 마켓 ID (예: KRW-BTC)
            side: 주문 종류 (bid: 매수, ask: 매도)
            volume: 주문 수량
            price: 주문 단가
            time_in_force: 주문 체결 옵션 (ioc, fok, post_only)
            smp_type: 자전거래 체결 방지 옵션
            identifier: 사용자 지정 주문 ID
        """
        return await self.create_order(
            market,
            side,
            ord_type=OrderType.LIMIT,
            volume=volume,
            price=price,
            time_in_force=time_in_force,
            smp_type=smp_type,
            identifier=identifier,
        )

    async def market_order(
        self,
        market: str,
        volume: Decimal,
        smp_type: SmpType | None = None,
        identifier: str | None = None,
    ) -> Order:
        """
        시장가 매도 주문

        Args:
            market: 마켓 ID (예: KRW-BTC)
            volume: 매도할 수량
            smp_type: 자전거래 체결 방지 옵션
            identifier: 사용자 지정 주문 ID
        """
        return await self.create_order(
            market,
            side=OrderSide.ASK,
            ord_type=OrderType.MARKET,
            volume=volume,
            smp_type=smp_type,
            identifier=identifier,
        )

    async def price_order(
        self,
        market: str,
        price: Decimal,
        smp_type: SmpType | None = None,
        identifier: str | None = None,
    ) -> Order:
        """
        시장가 매수 주문

        Args:
            market: 마켓 ID (예: KRW-BTC)
            price: 매수할 총 금액
            smp_type: 자전거래 체결 방지 옵션
            identifier: 사용자 지정 주문 ID
        """
        return await self.create_order(
            market, side=OrderSide.BID, ord_type=OrderType.PRICE, price=price, smp_type=smp_type, identifier=identifier
        )

    async def best_order(
        self,
        market: str,
        side: OrderSide,
        time_in_force: TimeInForce,
        price: Decimal | None = None,
        volume: Decimal | None = None,
        smp_type: SmpType | None = None,
        identifier: str | None = None,
    ) -> Order:
        """
        최유리 지정가 매도/매수 주문

        Args:
            market: 마켓 ID (예: KRW-BTC)
            side: 주문 종류 (bid: 매수, ask: 매도)
            time_in_force: 주문 체결 옵션 (ioc 또는 fok 필수)
            price: 매수 시 필수 (총 금액)
            volume: 매도 시 필수 (수량)
            smp_type: 자전거래 체결 방지 옵션
            identifier: 사용자 지정 주문 ID
        """
        return await self.create_order(
            market,
            side,
            ord_type=OrderType.BEST,
            price=price,
            volume=volume,
            time_in_force=time_in_force,
            smp_type=smp_type,
            identifier=identifier,
        )

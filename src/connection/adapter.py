import hashlib
import uuid
from urllib.parse import unquote, urlencode

import aiohttp
import jwt
import structlog

from ..model import Candle
from ..util.constants import CandleType, StreamType, Timeframe
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

import hashlib
import uuid
from urllib.parse import unquote, urlencode

import aiohttp
import jwt
import structlog

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
            logger.info("Connected to Upbit")

    async def disconnect(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("Disconnected from Upbit")

    async def _ensure_session(self):
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

import asyncio
import re
import time
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def parse_timeframe(timeframe: str) -> timedelta:
    """문자열을 timedelta 로 변환 (e.g., '1h', '5m', '1d', 'candle.1m', 'candle.240m')"""
    patterns = {
        r"(\d+)s": lambda x: timedelta(seconds=int(x)),
        r"(\d+)m": lambda x: timedelta(minutes=int(x)),
        r"(\d+)h": lambda x: timedelta(hours=int(x)),
        r"(\d+)d": lambda x: timedelta(days=int(x)),
        r"(\d+)w": lambda x: timedelta(weeks=int(x)),
    }

    for pattern, func in patterns.items():
        match = re.search(pattern, timeframe.lower())
        if match:
            return func(match.group(1))

    raise ValueError(f"{timeframe} 에 대한 formatting 함수를 찾을 수 없습니다.")


# ============= Decorators =============


def retry(max_retries: int = 3, delay: float = 1.0, exponential_backoff: bool = True) -> Callable:
    """
    async 및 sync 함수에 재시도 로직을 적용하는 데코레이터.

    함수 호출이 예외를 발생시키면 지정된 횟수만큼 재시도한다.
    모든 재시도가 실패하면 마지막 예외를 그대로 발생시킨다.

    Args:
        max_retries: 최대 재시도 횟수 (기본값 3)
        delay: 재시도 간 대기 시간 (초, 기본값 1.0)
        exponential_backoff: True 이면 대기 시간이 지수적으로 증가 (delay * 2^attempt)

    Returns:
        데코레이터 함수
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (Exception, asyncio.TimeoutError) as exception:
                    last_exception = exception
                    wait_time: float = delay * (2**attempt) if exponential_backoff else delay
                    logger.warning("⚠️ 재시도", attempt=attempt + 1, error=str(exception), wait_time=wait_time)
                    await asyncio.sleep(wait_time)
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exception:
                    last_exception = exception
                    wait_time: float = delay * (2**attempt) if exponential_backoff else delay
                    logger.warning("⚠️ 재시도", attempt=attempt + 1, error=str(exception), wait_time=wait_time)
                    time.sleep(wait_time)
            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

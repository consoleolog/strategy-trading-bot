import re
from datetime import timedelta


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

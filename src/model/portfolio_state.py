from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .position import Position


@dataclass
class PortfolioState:
    """
    포트폴리오 전체 상태 스냅샷 모델

    Attributes:
        total_capital (Decimal): 총 자본금 (현금 + 포지션 평가금액)
        available_capital (Decimal): 신규 주문에 사용 가능한 현금
        daily_pnl (Decimal): 당일 실현 손익
        weekly_pnl (Decimal): 주간 실현 손익
        total_pnl (Decimal): 누적 실현 손익
        high_water_mark (Decimal): 역대 최고 자본금 (드로우다운 계산 기준)
        trade_count_today (int): 당일 체결 건수 (기본값: 0)
        last_updated (datetime): 마지막 상태 갱신 시각
        positions (dict[str, Position]): 보유 중인 포지션 목록 (마켓 코드 → Position)
    """

    total_capital: Decimal
    available_capital: Decimal
    daily_pnl: Decimal
    weekly_pnl: Decimal
    total_pnl: Decimal
    high_water_mark: Decimal
    trade_count_today: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    positions: dict[str, Position] = field(default_factory=dict)

    def __post_init__(self):
        for field_name in [
            "total_capital",
            "available_capital",
            "daily_pnl",
            "weekly_pnl",
            "total_pnl",
            "high_water_mark",
        ]:
            value = getattr(self, field_name)
            if isinstance(value, (int, float, str)):
                setattr(self, field_name, Decimal(str(value)))

        if isinstance(self.last_updated, str):
            self.last_updated = datetime.fromisoformat(self.last_updated)

        self.positions = {k: Position.from_dict(v) if isinstance(v, dict) else v for k, v in self.positions.items()}

    @classmethod
    def from_dict(cls, data: dict) -> "PortfolioState":
        """딕셔너리 데이터를 PortfolioState 객체로 변환합니다."""
        return cls(
            total_capital=data.get("total_capital"),
            available_capital=data.get("available_capital"),
            daily_pnl=data.get("daily_pnl"),
            weekly_pnl=data.get("weekly_pnl"),
            total_pnl=data.get("total_pnl"),
            high_water_mark=data.get("high_water_mark"),
            trade_count_today=data.get("trade_count_today", 0),
            last_updated=data.get("last_updated", datetime.now()),
            positions=data.get("positions", {}),
        )

    def to_dict(self) -> dict:
        """PortfolioState 객체를 딕셔너리로 변환합니다."""
        return {
            "total_capital": self.total_capital,
            "available_capital": self.available_capital,
            "daily_pnl": self.daily_pnl,
            "weekly_pnl": self.weekly_pnl,
            "total_pnl": self.total_pnl,
            "high_water_mark": self.high_water_mark,
            "trade_count_today": self.trade_count_today,
            "last_updated": self.last_updated,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
        }

    @property
    def current_drawdown(self) -> float:
        """고점(high_water_mark) 대비 현재 드로우다운 비율."""
        if self.high_water_mark == 0:
            return 0.0
        return float((self.high_water_mark - self.total_capital) / self.high_water_mark)

    @property
    def positions_value(self) -> Decimal:
        """보유 포지션 전체 평가금액 합계."""
        return sum((pos.value for pos in self.positions.values()), Decimal("0"))

    @property
    def num_positions(self) -> int:
        """현재 보유 중인 포지션 수."""
        return len(self.positions)

    @property
    def portfolio_exposure(self) -> float:
        """총 자본금 대비 포지션 노출 비율."""
        if self.total_capital == 0:
            return 0.0
        return float(self.positions_value / self.total_capital)

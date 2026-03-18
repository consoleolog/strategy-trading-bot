from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskContext:
    """리스크 엔진이 규칙을 평가하기 위해 사용하는 불변 스냅샷.

    의사결정(Decision) 평가 직전에 매번 새로 생성된다.
    모든 금액 단위는 KRW.

    Attributes:
        system_state: 시스템 운영 상태. ``RUNNING`` | ``PAUSED`` | ``STOPPED``
        mode: 트레이딩 실행 모드. ``DRY_RUN`` | ``PAPER`` | ``LIVE``

        open_positions_count: 현재 보유 중인 포지션 수.
        total_position_value_krw: 보유 포지션 전체 평가 금액 (KRW).

        portfolio_value_krw: 현재 포트폴리오 총 평가 금액 (KRW).
        starting_capital_krw: 운용 시작 시점의 원금 (KRW).

        daily_pnl_krw: 당일 손익 절대값 (KRW).
        daily_pnl_percent: 당일 손익률 (%).
        weekly_pnl_krw: 주간 손익 절대값 (KRW).
        weekly_pnl_percent: 주간 손익률 (%).

        peak_portfolio_value_krw: 운용 시작 이후 포트폴리오 최고 평가 금액 (KRW).
        current_drawdown_percent: 고점 대비 현재 낙폭 (%).

        proposed_trade_size_krw: 검토 중인 주문의 거래 금액 (KRW). 포지션 사이징 평가 시 사용.
        proposed_trade_risk_percent: 검토 중인 주문의 예상 리스크 비율 (%).
    """

    # 시스템 상태
    system_state: str
    mode: str

    # 포지션 현황
    open_positions_count: int
    total_position_value_krw: Decimal

    # 포트폴리오 지표
    portfolio_value_krw: Decimal
    starting_capital_krw: Decimal

    # 손익 현황
    daily_pnl_krw: Decimal
    daily_pnl_percent: Decimal
    weekly_pnl_krw: Decimal
    weekly_pnl_percent: Decimal

    # 낙폭 추적
    peak_portfolio_value_krw: Decimal
    current_drawdown_percent: Decimal

    # 주문 검토 컨텍스트 (포지션 사이징용, 선택)
    proposed_trade_size_krw: Decimal | None = None
    proposed_trade_risk_percent: Decimal | None = None

    @property
    def total_pnl_percent(self) -> Decimal:
        """운용 시작 이후 누적 손익률 (%)."""
        if self.starting_capital_krw == 0:
            return Decimal("0")
        return (self.portfolio_value_krw - self.starting_capital_krw) / self.starting_capital_krw * 100

    @property
    def position_utilization_percent(self) -> Decimal:
        """포트폴리오 대비 포지션 비중 (%)."""
        if self.portfolio_value_krw == 0:
            return Decimal("0")
        return self.total_position_value_krw / self.portfolio_value_krw * 100

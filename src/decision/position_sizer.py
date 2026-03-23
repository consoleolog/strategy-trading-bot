from decimal import ROUND_DOWN, Decimal

import structlog

from ..models import Decision, PortfolioState, RiskLimitsConfig, TradeCandidate
from ..utils.constants import DecisionState

logger = structlog.get_logger(__name__)


class PositionSizer:
    """거래 후보에 대한 적정 포지션 크기(금액)를 계산하는 클래스.

    리스크 한도 설정(``RiskLimitsConfig``)과 현재 포트폴리오 상태(``PortfolioState``)를
    기반으로, 단일 거래에서 감수할 수 있는 최대 손실액을 초과하지 않는 포지션 금액을 산출한다.

    손절 가격이 유효한 경우 리스크 기반 산식을 사용하고,
    손절 가격이 없거나 0인 경우 고정 비율(max_position_size)로 폴백(fallback)한다.

    Attributes:
        max_risk_per_trade (float): 단일 거래당 허용 최대 리스크 비율 (예: 0.02 = 2%).
        max_position_size (float): 단일 포지션의 최대 비율 (예: 0.40 = 40%).
        max_portfolio_exposure (float): 전체 포트폴리오 대비 최대 노출 비율.
    """

    def __init__(self, risk_config: RiskLimitsConfig):
        """PositionSizer를 초기화한다.

        Args:
            risk_config: 적용할 리스크 한도 설정값.
        """
        self.max_risk_per_trade = risk_config.max_risk_per_trade
        self.max_position_size = risk_config.max_position_size
        self.max_portfolio_exposure = risk_config.max_portfolio_exposure

    def calculate(
        self,
        candidate: TradeCandidate,
        portfolio: PortfolioState,
        current_price: Decimal,
    ) -> Decision:
        """거래 후보의 적정 포지션 금액을 계산하여 Decision 객체로 반환한다.

        진입 가격 대비 손절 가격 비율(stop_percent)로 리스크 기반 포지션 금액을 산출하며,
        손절 정보가 없는 경우 고정 비율로 대체한다.

        Args:
            candidate: 수량을 계산할 거래 후보. ``suggested_entry``, ``suggested_stop_loss``,
                ``suggested_take_profit`` 필드를 사용한다.
            portfolio: 현재 포트폴리오 상태. ``available_capital`` 필드를 사용한다.
            current_price: 현재 시장 가격. ``suggested_entry``가 0일 때 대체 진입 가격으로 사용.

        Returns:
            포지션 금액이 반영된 :class:`~models.decision.Decision` 객체.
        """
        # suggested_entry가 없으면 현재 시장가를 진입 가격으로 사용
        entry_price = candidate.suggested_entry if candidate.suggested_entry > 0 else current_price
        stop_loss = candidate.suggested_stop_loss
        take_profit = candidate.suggested_take_profit

        if stop_loss > 0 and entry_price > 0:
            # 진입 가격과 손절 가격 사이의 절대 거리
            stop_distance = abs(entry_price - stop_loss)
            # 진입 가격 대비 손절 비율 (소수)
            stop_percent = stop_distance / entry_price

            if stop_percent > 0:
                # 리스크 기반 포지션 산식: 허용 손실 금액 / 손절 비율 = 포지션 금액
                risk_amount = portfolio.available_capital * Decimal(str(self.max_risk_per_trade))
                position_value = risk_amount / stop_percent
            else:
                # 손절 비율이 0이면 최대 포지션 비율로 폴백
                position_value = portfolio.available_capital * Decimal(str(self.max_position_size))
        else:
            # 손절 정보가 없으면 고정 비율로 포지션 크기 결정
            position_value = portfolio.available_capital * Decimal(str(self.max_position_size))

        # 단일 포지션 최대 비율을 초과하지 않도록 상한 적용
        max_position_value = portfolio.available_capital * Decimal(str(self.max_position_size))
        position_value = min(position_value, max_position_value)

        # 현재 포지션 노출 총액과 허용 잔여 노출 한도 계산
        current_exposure = portfolio.positions_value
        max_total_exposure = portfolio.total_capital * Decimal(str(self.max_portfolio_exposure))
        remaining_exposure = max_total_exposure - current_exposure

        # 포트폴리오 노출 한도 초과 시 잔여 허용치로 축소 (음수 방지)
        if remaining_exposure < position_value:
            position_value = max(Decimal("0"), remaining_exposure)

        # 포지션 금액을 진입 가격으로 나눠 수량 산출 (소수점 8자리, 절사)
        if entry_price > 0:
            volume = (position_value / entry_price).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
        else:
            volume = Decimal("0")

        # 실제 리스크 금액·비율 계산 (손절 정보가 있으면 정밀 계산, 없으면 추정값 사용)
        if stop_loss > 0 and entry_price > 0 and volume > 0:
            risk_amount = abs(entry_price - stop_loss) * volume
            risk_percent = float(risk_amount / portfolio.total_capital)
        else:
            risk_amount = position_value * Decimal(str(self.max_risk_per_trade))
            risk_percent = self.max_risk_per_trade

        logger.info(
            "position.sized",
            market=candidate.market,
            volume=str(volume),
            value=float(position_value),
            risk_percent=round(risk_percent, 6),
        )

        return Decision(
            market=candidate.market,
            direction=candidate.direction,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            contributing_signals=candidate.contributing_signals,
            state=DecisionState.PENDING,
        )

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimitsConfig:
    """리스크 엔진에 적용되는 한도 설정값 모음.

    모든 비율 값은 소수(0.0 ~ 1.0) 기준이다 (예: 0.05 = 5%).
    인스턴스 생성 후 값이 변경되지 않도록 불변(frozen)으로 관리된다.

    Attributes:
        max_drawdown: 고점 대비 최대 허용 낙폭 비율. 초과 시 ``EMERGENCY_STOP`` 판정.
            기본값 ``0.20`` (20%).
        daily_loss_limit: 당일 최대 허용 손실 비율. 초과 시 ``FORCE_NO_ACTION`` 판정.
            기본값 ``0.05`` (5%).
        weekly_loss_limit: 주간 최대 허용 손실 비율. 초과 시 ``FORCE_NO_ACTION`` 판정.
            기본값 ``0.10`` (10%).
        max_position_size: 단일 포지션이 포트폴리오에서 차지할 수 있는 최대 비율.
            기본값 ``0.40`` (40%).
        max_risk_per_trade: 단일 거래에서 감수할 수 있는 최대 리스크 비율.
            기본값 ``0.02`` (2%).
        max_positions: 동시에 보유할 수 있는 최대 포지션 수.
            기본값 ``5``.
        max_portfolio_exposure: 전체 포트폴리오 대비 최대 포지션 노출 비율.
            기본값 ``0.40`` (40%).
    """

    max_drawdown: float = 0.20
    daily_loss_limit: float = 0.05
    weekly_loss_limit: float = 0.10
    max_position_size: float = 0.40
    max_risk_per_trade: float = 0.02
    max_positions: int = 5
    max_portfolio_exposure: float = 0.40

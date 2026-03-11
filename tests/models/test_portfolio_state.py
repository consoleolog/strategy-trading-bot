from datetime import datetime
from decimal import Decimal

import pytest
from src.models.portfolio_state import PortfolioState
from src.models.position import Position

SAMPLE_POSITION_DICT = {
    "market": "KRW-BTC",
    "direction": "long",
    "entry_price": "140000000",
    "current_price": "142000000",
    "volume": "0.01",
    "stop_loss": "138000000",
    "take_profit": "146000000",
    "strategy_id": "ma_crossover_v1",
    "opened_at": "2025-01-02T04:28:05",
}

SAMPLE_DICT = {
    "total_capital": "10000000",
    "available_capital": "8580000",
    "daily_pnl": "20000",
    "weekly_pnl": "50000",
    "total_pnl": "200000",
    "high_water_mark": "10200000",
    "trade_count_today": 3,
    "last_updated": "2025-01-02T04:28:05",
    "positions": {"KRW-BTC": SAMPLE_POSITION_DICT},
}


# ---------------------------------------------------------------------------
# from_dict — 기본 필드
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_from_dict_trade_count_today():
    """trade_count_today 필드가 올바르게 매핑된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert state.trade_count_today == 3


# ---------------------------------------------------------------------------
# Decimal 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_decimal_fields_are_decimal_type():
    """자본금/손익 필드들이 모두 Decimal 타입으로 변환된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    for field in ["total_capital", "available_capital", "daily_pnl", "weekly_pnl", "total_pnl", "high_water_mark"]:
        assert isinstance(getattr(state, field), Decimal), f"{field} should be Decimal"


@pytest.mark.unit
def test_decimal_values():
    """자본금/손익 필드들이 올바른 값을 가진다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert state.total_capital == Decimal("10000000")
    assert state.available_capital == Decimal("8580000")
    assert state.daily_pnl == Decimal("20000")
    assert state.weekly_pnl == Decimal("50000")
    assert state.total_pnl == Decimal("200000")
    assert state.high_water_mark == Decimal("10200000")


@pytest.mark.unit
def test_decimal_converted_from_int():
    """int로 전달된 Decimal 필드가 Decimal로 변환된다."""
    state = PortfolioState.from_dict({**SAMPLE_DICT, "total_capital": 10000000})
    assert isinstance(state.total_capital, Decimal)
    assert state.total_capital == Decimal("10000000")


@pytest.mark.unit
def test_decimal_converted_from_float():
    """float로 전달된 Decimal 필드가 Decimal로 변환된다."""
    state = PortfolioState.from_dict({**SAMPLE_DICT, "daily_pnl": 20000.0})
    assert isinstance(state.daily_pnl, Decimal)


# ---------------------------------------------------------------------------
# datetime 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_last_updated_is_datetime_type():
    """문자열 last_updated가 datetime 타입으로 변환된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert isinstance(state.last_updated, datetime)


@pytest.mark.unit
def test_last_updated_value():
    """last_updated가 ISO 8601 문자열과 동일한 값을 가진다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert state.last_updated == datetime(2025, 1, 2, 4, 28, 5)


@pytest.mark.unit
def test_last_updated_defaults_to_now_when_absent():
    """last_updated가 dict에 없으면 현재 시각으로 설정된다."""
    before = datetime.now()
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "last_updated"}
    state = PortfolioState.from_dict(data)
    after = datetime.now()
    assert before <= state.last_updated <= after


# ---------------------------------------------------------------------------
# 기본값
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_trade_count_today_defaults_to_zero():
    """trade_count_today가 dict에 없으면 0으로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "trade_count_today"}
    state = PortfolioState.from_dict(data)
    assert state.trade_count_today == 0


@pytest.mark.unit
def test_positions_defaults_to_empty_dict():
    """positions가 dict에 없으면 빈 딕셔너리로 설정된다."""
    data = {k: v for k, v in SAMPLE_DICT.items() if k != "positions"}
    state = PortfolioState.from_dict(data)
    assert state.positions == {}


# ---------------------------------------------------------------------------
# positions 변환
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_positions_dict_converted_to_position():
    """dict로 전달된 positions의 값이 Position 객체로 변환된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert isinstance(state.positions["KRW-BTC"], Position)


@pytest.mark.unit
def test_positions_already_position_skips_conversion():
    """이미 Position 객체인 경우 그대로 유지된다."""
    pos = Position.from_dict(SAMPLE_POSITION_DICT)
    data = {**SAMPLE_DICT, "positions": {"KRW-BTC": pos}}
    state = PortfolioState.from_dict(data)
    assert state.positions["KRW-BTC"] is pos


@pytest.mark.unit
def test_positions_market_key():
    """positions 딕셔너리의 키가 마켓 코드와 일치한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert "KRW-BTC" in state.positions


# ---------------------------------------------------------------------------
# property — positions_value
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_positions_value_is_decimal_type():
    """positions_value는 Decimal 타입을 반환한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert isinstance(state.positions_value, Decimal)


@pytest.mark.unit
def test_positions_value_sum():
    """positions_value가 보유 포지션 평가금액의 합계를 반환한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    # current_price=142000000, volume=0.01 → value=1420000
    assert state.positions_value == Decimal("142000000") * Decimal("0.01")


@pytest.mark.unit
def test_positions_value_empty_is_zero():
    """포지션이 없으면 positions_value는 Decimal('0')을 반환한다."""
    data = {**SAMPLE_DICT, "positions": {}}
    state = PortfolioState.from_dict(data)
    assert state.positions_value == Decimal("0")
    assert isinstance(state.positions_value, Decimal)


# ---------------------------------------------------------------------------
# property — num_positions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_num_positions_count():
    """num_positions가 보유 포지션 수를 반환한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert state.num_positions == 1


@pytest.mark.unit
def test_num_positions_empty():
    """포지션이 없으면 num_positions는 0을 반환한다."""
    data = {**SAMPLE_DICT, "positions": {}}
    state = PortfolioState.from_dict(data)
    assert state.num_positions == 0


# ---------------------------------------------------------------------------
# property — current_drawdown
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_current_drawdown_calculation():
    """드로우다운이 (고점 - 현재) / 고점으로 계산된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    # high_water_mark=10200000, total_capital=10000000
    expected = float((Decimal("10200000") - Decimal("10000000")) / Decimal("10200000"))
    assert state.current_drawdown == pytest.approx(expected)


@pytest.mark.unit
def test_current_drawdown_zero_when_high_water_mark_is_zero():
    """high_water_mark가 0이면 current_drawdown은 0.0을 반환한다."""
    state = PortfolioState.from_dict({**SAMPLE_DICT, "high_water_mark": "0"})
    assert state.current_drawdown == 0.0


@pytest.mark.unit
def test_current_drawdown_returns_float():
    """current_drawdown은 float 타입을 반환한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert isinstance(state.current_drawdown, float)


# ---------------------------------------------------------------------------
# property — portfolio_exposure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_portfolio_exposure_calculation():
    """포지션 노출 비율이 positions_value / total_capital로 계산된다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    expected = float(state.positions_value / state.total_capital)
    assert state.portfolio_exposure == pytest.approx(expected)


@pytest.mark.unit
def test_portfolio_exposure_zero_when_total_capital_is_zero():
    """total_capital이 0이면 portfolio_exposure는 0.0을 반환한다."""
    state = PortfolioState.from_dict({**SAMPLE_DICT, "total_capital": "0"})
    assert state.portfolio_exposure == 0.0


@pytest.mark.unit
def test_portfolio_exposure_returns_float():
    """portfolio_exposure는 float 타입을 반환한다."""
    state = PortfolioState.from_dict(SAMPLE_DICT)
    assert isinstance(state.portfolio_exposure, float)


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_to_dict_has_all_keys():
    """to_dict()가 모든 필드 키를 포함한다."""
    result = PortfolioState.from_dict(SAMPLE_DICT).to_dict()
    expected_keys = {
        "total_capital",
        "available_capital",
        "daily_pnl",
        "weekly_pnl",
        "total_pnl",
        "high_water_mark",
        "trade_count_today",
        "last_updated",
        "positions",
    }
    assert result.keys() == expected_keys


@pytest.mark.unit
def test_to_dict_decimal_fields_are_decimal():
    """to_dict()의 Decimal 필드는 Decimal 타입으로 반환된다."""
    result = PortfolioState.from_dict(SAMPLE_DICT).to_dict()
    for field in ["total_capital", "available_capital", "daily_pnl", "weekly_pnl", "total_pnl", "high_water_mark"]:
        assert isinstance(result[field], Decimal), f"{field} should be Decimal"


@pytest.mark.unit
def test_to_dict_last_updated_is_datetime():
    """to_dict()의 last_updated는 ISO 8601 문자열로 반환된다."""
    result = PortfolioState.from_dict(SAMPLE_DICT).to_dict()
    assert isinstance(result["last_updated"], str)


@pytest.mark.unit
def test_to_dict_positions_are_dicts():
    """to_dict()의 positions 값은 dict로 직렬화된다."""
    result = PortfolioState.from_dict(SAMPLE_DICT).to_dict()
    assert all(isinstance(v, dict) for v in result["positions"].values())


@pytest.mark.unit
def test_to_dict_trade_count_today():
    """to_dict()의 trade_count_today 값이 원본과 일치한다."""
    result = PortfolioState.from_dict(SAMPLE_DICT).to_dict()
    assert result["trade_count_today"] == 3

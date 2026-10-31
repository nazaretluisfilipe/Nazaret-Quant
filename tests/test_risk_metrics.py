"""Risk-metric tests use fictional amounts; no market data or broker access."""
import pytest
from nazaret_quant.risk_metrics import (
    expectancy_from_closed_trades, maximum_drawdown, size_for_fixed_stop,
)


def test_expectancy_matches_probability_weighted_payoffs():
    # 2 winners, 2 losers, 1 break-even. Net P&L already includes costs.
    r = expectancy_from_closed_trades([5, 5, -2, -2, 0])
    assert r["wins"] == 2 and r["losses"] == 2 and r["breakeven"] == 1
    assert r["win_rate"] == 0.4 and r["loss_rate"] == 0.4
    assert r["mean_win_brl"] == 5 and r["mean_loss_brl"] == 2
    assert r["expectancy_brl"] == pytest.approx(1.2)
    assert r["total_net_pnl_brl"] == 6
    assert r["payoff_ratio"] == pytest.approx(2.5)
    assert r["profit_factor"] == pytest.approx(2.5)
    assert r["status"] == "DESCRIPTIVE_ONLY_NOT_VALIDATED"


def test_no_closed_trades_never_claims_expectancy():
    r = expectancy_from_closed_trades([])
    assert r["expectancy_brl"] is None and r["status"] == "INSUFFICIENT_DATA"


def test_no_winners_and_no_losers_handle_undefined_ratios():
    loss = expectancy_from_closed_trades([-3, 0])
    win = expectancy_from_closed_trades([3, 0])
    assert loss["payoff_ratio"] is None and loss["profit_factor"] == 0
    assert win["payoff_ratio"] is None and win["profit_factor"] is None


def test_drawdown_uses_running_peak_including_initial_capital():
    r = maximum_drawdown([250, 260, 230, 240, 225, 270, 265])
    assert r["max_drawdown_brl"] == 35
    assert r["max_drawdown_fraction"] == pytest.approx(35/260)
    assert (r["peak_index"], r["trough_index"]) == (1, 4)


def test_drawdown_can_capture_total_ruin():
    r = maximum_drawdown([250, 200, 0])
    assert r["max_drawdown_fraction"] == 1.0


def test_fixed_stop_sizing_limited_by_risk_not_notional():
    r = size_for_fixed_stop(
        entry_price=10, stop_price=9.50, cash_available=250, reserve=100,
        remaining_exposure=150, risk_budget=5)
    assert r["quantity"] == 10
    assert r["estimated_loss_at_stop_brl"] == 5
    assert r["estimated_entry_outlay_brl"] == 100
    assert r["status"] == "HYPOTHETICAL_SIZE_ONLY_NO_ORDER"


def test_fees_and_spread_cannot_increase_quantity():
    base = size_for_fixed_stop(entry_price=10, stop_price=9.50,
                               cash_available=250, reserve=100,
                               remaining_exposure=150, risk_budget=5)
    costly = size_for_fixed_stop(entry_price=10, stop_price=9.50,
                                 cash_available=250, reserve=100,
                                 remaining_exposure=150, risk_budget=5,
                                 entry_cost_bps=10, exit_cost_bps=20,
                                 fixed_fee_per_order=0.50)
    assert costly["quantity"] < base["quantity"]
    assert costly["estimated_loss_at_stop_brl"] <= 5


def test_no_martingale_risk_growth_is_encoded():
    small = size_for_fixed_stop(entry_price=10, stop_price=9,
                               cash_available=250, reserve=100,
                               remaining_exposure=150, risk_budget=2)
    large = size_for_fixed_stop(entry_price=10, stop_price=9,
                               cash_available=250, reserve=100,
                               remaining_exposure=150, risk_budget=4)
    assert small["quantity"] < large["quantity"]
    assert any("martingale" in warning for warning in small["warnings"])
    # Caller must hold the risk_budget constant; this module never uses loss history.


def test_lot_constraint_no_fractional_quantity():
    result = size_for_fixed_stop(entry_price=10, stop_price=9.50,
                                  cash_available=250, reserve=100,
                                  remaining_exposure=150, risk_budget=5, lot_size=4)
    assert result["quantity"] == 8


@pytest.mark.parametrize("kwargs", [
    {"stop_price": 10},
    {"stop_price": 11},
    {"stop_price": 0},
    {"entry_price": float("nan")},
    {"risk_budget": -2},
    {"entry_cost_bps": -1},
    {"exit_cost_bps": 10000},
    {"lot_size": 0},
    {"lot_size": 1.5},
])
def test_invalid_sizing_rejected(kwargs):
    values = dict(entry_price=10, stop_price=9, cash_available=250,
                  reserve=100, remaining_exposure=150, risk_budget=5)
    values.update(kwargs)
    with pytest.raises(ValueError):
        size_for_fixed_stop(**values)


@pytest.mark.parametrize("bad", [[1, float("inf")], [1, float("nan")], [True, 2]])
def test_invalid_pnl_rejected(bad):
    with pytest.raises(ValueError):
        expectancy_from_closed_trades(bad)


@pytest.mark.parametrize("bad", [[], [0, 100], [100, -1], [100, float("nan")]])
def test_invalid_curve_rejected(bad):
    with pytest.raises(ValueError):
        maximum_drawdown(bad)

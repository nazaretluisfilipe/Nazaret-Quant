"""Descriptive trading-risk diagnostics. No brokerage calls or order execution.

All outputs are diagnostic; they do not establish a positive expected return,
prevent gap losses, authorize live trading, or use the 2026 lockbox.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_FLOOR
import math


def _number(value, field: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite number")
    return result


def expectancy_from_closed_trades(net_pnls) -> dict:
    """Descriptive expectancy from CLOSED, net-of-all-cost trade P&Ls in BRL.

    One observation must represent a closed *trade/position*, not a fill;
    combining partial fills, fees, taxes and corporate actions is the caller's
    responsibility. Break-even outcomes contribute probability mass but zero.
    """
    try:
        pnl = [_number(p, "net_pnl") for p in net_pnls]
    except TypeError as exc:
        raise ValueError("Expected an iterable of net P&Ls") from exc
    if not pnl:
        return {"status": "INSUFFICIENT_DATA", "n_closed_trades": 0,
                "expectancy_brl": None,
                "warning": "No closed trade results; cannot infer win rate or expectancy"}
    wins = [p for p in pnl if p > 0]
    losses = [-p for p in pnl if p < 0]
    flats = len(pnl) - len(wins) - len(losses)
    n = len(pnl)
    prob_win = Decimal(len(wins)) / n
    prob_loss = Decimal(len(losses)) / n
    gain = sum(wins, Decimal(0)) / len(wins) if wins else Decimal(0)
    loss = sum(losses, Decimal(0)) / len(losses) if losses else Decimal(0)
    # A directly summed arithmetic mean is numerically stable for n=3, 7, etc.
    # Weighted terms are algebraically identical, but Decimal division creates
    # repeating expansions, so asserting exact equality would be incorrect.
    expectancy = sum(pnl, Decimal(0)) / n
    ratio = gain / loss if wins and losses else None
    profit_factor = (sum(wins, Decimal(0)) / sum(losses, Decimal(0))
                     if losses else None)
    return {
        "status": "DESCRIPTIVE_ONLY_NOT_VALIDATED",
        "n_closed_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": flats,
        "win_rate": float(prob_win),
        "loss_rate": float(prob_loss),
        "breakeven_rate": flats / n,
        "mean_win_brl": float(gain) if wins else None,
        "mean_loss_brl": float(loss) if losses else None,
        "expectancy_brl": float(expectancy),
        "total_net_pnl_brl": float(sum(pnl, Decimal(0))),
        "payoff_ratio": float(ratio) if ratio is not None else None,
        "profit_factor": float(profit_factor) if profit_factor is not None else None,
        "warnings": [
            "Results are descriptive; no independence, confidence interval or statistical power assumed.",
            "Inputs must be closed trades net of spread, fees, slippage and applicable taxes.",
            "Partially closed positions must be consolidated into complete trades before calculating win rate.",
            "Open positions, opportunity cost and changes of market regime are not included.",
        ],
    }


def maximum_drawdown(equity_curve) -> dict:
    """Peak-to-trough decline on a chronological equity curve INCLUDING initial capital."""
    try:
        values = [_number(e, "equity") for e in equity_curve]
    except TypeError as exc:
        raise ValueError("Expected an iterable of equity observations") from exc
    if not values or values[0] <= 0 or any(v < 0 for v in values):
        raise ValueError("Include positive initial equity and nonnegative subsequent equity")
    peak = values[0]
    max_loss = Decimal(0)
    max_ratio = Decimal(0)
    peak_index = trough_index = 0
    current_peak_index = 0
    for index, value in enumerate(values):
        if value > peak:
            peak = value
            current_peak_index = index
        drop = peak - value
        ratio = drop / peak
        if ratio > max_ratio:
            max_ratio, max_loss = ratio, drop
            peak_index, trough_index = current_peak_index, index
    return {
        "status": "DESCRIPTIVE_ONLY_NOT_VALIDATED",
        "n_equity_marks": len(values),
        "max_drawdown_brl": float(max_loss),
        "max_drawdown_fraction": float(max_ratio),
        "peak_index": peak_index,
        "trough_index": trough_index,
        "warning": "Mark-to-market drawdown may exceed protective loss limits on gaps or unfillable exits.",
    }


def size_for_fixed_stop(*, entry_price, stop_price, cash_available,
                        reserve, remaining_exposure, risk_budget,
                        entry_cost_bps=0, exit_cost_bps=0,
                        fixed_fee_per_order=0, lot_size=1) -> dict:
    """Conservative integer sizing for a HYPOTHETICAL long order.

    Estimated loss uses entry with estimated BUY friction, stop with estimated
    SELL friction, and two fixed commissions. Cash/exposure also bind quantity.
    Does NOT place or guarantee a fill, stop loss, execution price, or liquidity.
    """
    inputs = {
        "entry_price": entry_price, "stop_price": stop_price,
        "cash_available": cash_available, "reserve": reserve,
        "remaining_exposure": remaining_exposure, "risk_budget": risk_budget,
        "entry_cost_bps": entry_cost_bps, "exit_cost_bps": exit_cost_bps,
        "fixed_fee_per_order": fixed_fee_per_order,
    }
    values = {name: _number(v, name) for name, v in inputs.items()}
    entry = values["entry_price"]
    stop = values["stop_price"]
    cash = values["cash_available"]
    reserve = values["reserve"]
    exposure = values["remaining_exposure"]
    risk_budget = values["risk_budget"]
    entry_bps = values["entry_cost_bps"]
    exit_bps = values["exit_cost_bps"]
    fee = values["fixed_fee_per_order"]
    if not 0 < stop < entry:
        raise ValueError("A positive long stop must be below entry")
    if cash < 0 or reserve < 0 or exposure < 0 or risk_budget < 0:
        raise ValueError("Cash, reserve, exposure and risk budget cannot be negative")
    if not 0 <= entry_bps < 10000 or not 0 <= exit_bps < 10000 or fee < 0:
        raise ValueError("Invalid execution friction")
    if type(lot_size) is not int or lot_size < 1:
        raise ValueError("lot_size must be a strictly positive integer")

    buy_unit = entry * (1 + entry_bps / 10000)
    exit_unit = stop * (1 - exit_bps / 10000)
    risk_unit = buy_unit - exit_unit
    available = max(Decimal(0), min(cash - reserve, exposure))
    risk_left = risk_budget - 2*fee
    cash_left = available - fee
    qty = 0
    if available > 0 and risk_left > 0 and cash_left > 0:
        by_risk = int((risk_left / risk_unit).to_integral_value(rounding=ROUND_FLOOR))
        by_cash = int((cash_left / buy_unit).to_integral_value(rounding=ROUND_FLOOR))
        qty = max(0, min(by_risk, by_cash))
        qty = (qty // lot_size) * lot_size

    estimated_loss = risk_unit * qty + 2*fee if qty else Decimal(0)
    estimated_entry_cost = buy_unit * qty + fee if qty else Decimal(0)
    assert estimated_loss <= risk_budget and estimated_entry_cost <= available
    return {
        "status": "HYPOTHETICAL_SIZE_ONLY_NO_ORDER",
        "quantity": qty,
        "estimated_loss_at_stop_brl": float(estimated_loss),
        "estimated_entry_outlay_brl": float(estimated_entry_cost),
        "risk_budget_brl": float(risk_budget),
        "cash_or_exposure_budget_brl": float(available),
        "unfilled_stop_gap_risk": "UNBOUNDED_BY_THIS_ESTIMATE",
        "warnings": [
            "Do not increase per-trade risk after losses; no martingale or doubling-down.",
            "A stop level is a planning parameter, not a guaranteed execution price.",
            "Historical OHLCV cannot establish executable spread, fill or liquidity.",
            "Does not include uncertain taxation, corporate actions, or overnight gaps.",
        ],
    }

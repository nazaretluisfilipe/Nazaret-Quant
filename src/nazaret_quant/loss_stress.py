"""Deterministic loss-streak stress testing. No predictive ruin probabilities.

Consumes only fictional scenarios. No broker access, no signal generation, no
2026 confirmation data. An executed stop is not assumed: gap multipliers can
cause realized simulated loss to overshoot the planned risk and thresholds.
"""
from __future__ import annotations

from decimal import Decimal
from .risk_metrics import _number, maximum_drawdown


def loss_streak_stress(*, capital, reserve, fixed_risk_per_attempt,
                       daily_loss_trigger, total_loss_trigger, scenarios):
    """Simulate an ordered sequence (session_label, loss_multiplier).

    Each candidate attempt uses the SAME planned BRL risk, regardless of
    prior losses. A daily halt resets only at the next supplied session.
    Permanent halt and reserve stop remain latched. These are post-loss
    controls, NOT price or liquidity guarantees.
    """
    cash = _number(capital, "capital")
    reserve = _number(reserve, "reserve")
    risk = _number(fixed_risk_per_attempt, "fixed_risk_per_attempt")
    daily_limit = _number(daily_loss_trigger, "daily_loss_trigger")
    total_limit = _number(total_loss_trigger, "total_loss_trigger")
    if not cash > 0 or not 0 <= reserve < cash or risk <= 0:
        raise ValueError("Capital, reserve and fixed risk invalid")
    if daily_limit <= 0 or total_limit <= 0:
        raise ValueError("Loss triggers must be positive")
    try:
        steps = list(scenarios)
    except TypeError as exc:
        raise ValueError("Scenarios must be a sequence") from exc
    if not 1 <= len(steps) <= 500:
        raise ValueError("Scenarios must contain 1 to 500 ordered attempts")
    prepared = []
    seen_sessions = set()
    latest = None
    for item in steps:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("Each scenario must be (session, loss_multiplier)")
        session, multiplier = item
        if not isinstance(session, str) or not session.strip():
            raise ValueError("Invalid session label")
        loss_multiplier = _number(multiplier, "loss_multiplier")
        if not 0 <= loss_multiplier <= 100:
            raise ValueError("Gap/loss multiplier outside stress test bounds")
        if session != latest:
            if session in seen_sessions:
                raise ValueError("Non-contiguous session identifiers")
            seen_sessions.add(session)
            latest = session
        prepared.append((session, loss_multiplier))

    equity = cash
    initial = cash
    day_initial = cash
    current_session = None
    daily_halt = False
    permanent_halt = False
    marks = [float(cash)]
    events = []
    for session, multiplier in prepared:
        if session != current_session:
            current_session = session
            day_initial = equity
            daily_halt = False
        reason = None
        if permanent_halt:
            reason = "PERMANENT_LOSS_HALT"
        elif equity <= reserve or equity - reserve < risk:
            reason = "RESERVE_OR_RISK_BUDGET"
        elif daily_halt:
            reason = "DAILY_LOSS_HALT"
        if reason is not None:
            events.append({"session": session, "executed": False, "reason": reason,
                           "fixed_planned_risk_brl": float(risk),
                           "equity_after_brl": float(equity)})
            marks.append(float(equity))
            continue
        actual = min(equity, risk * multiplier)
        equity -= actual
        daily_halt = day_initial-equity >= daily_limit
        permanent_halt = initial-equity >= total_limit
        events.append({
            "session": session, "executed": True,
            "fixed_planned_risk_brl": float(risk),
            "loss_multiplier": float(multiplier),
            "hypothetical_loss_brl": float(actual),
            "equity_after_brl": float(equity),
            "daily_halt_after": daily_halt,
            "permanent_halt_after": permanent_halt,
            "reserve_breached_after": equity < reserve,
            "nominal_risk_exceeded": actual > risk,
        })
        marks.append(float(equity))
    drawdown = maximum_drawdown(marks)
    return {
        "status": "DETERMINISTIC_STRESS_ONLY_NO_RUIN_PROBABILITY",
        "initial_capital_brl": float(initial),
        "final_equity_brl": float(equity),
        "fixed_risk_per_attempt_brl": float(risk),
        "executed_attempts": sum(1 for e in events if e["executed"]),
        "blocked_attempts": sum(1 for e in events if not e["executed"]),
        "total_simulated_loss_brl": float(initial-equity),
        "reserve_breached": equity < reserve,
        "total_loss_trigger_exceeded": initial-equity > total_limit,
        "max_drawdown_fraction": drawdown["max_drawdown_fraction"],
        "events": events,
        "warnings": [
            "This is not a probability of ruin; loss multipliers are hand-selected scenarios.",
            "Gap losses can exceed nominal risk, reserve and loss triggers.",
            "Per-attempt risk never increases after losses; no martingale is applied.",
            "No fees, trading signals, probabilistic calibration or actual order fills are modeled.",
        ],
        "live_trading": "BLOCKED",
    }

"""Synthetic worst-case tests: no interpretation as probability of ruin."""
import pytest
from nazaret_quant.loss_stress import loss_streak_stress


def stress(events, **overrides):
    settings = dict(capital=250, reserve=100, fixed_risk_per_attempt=2,
                    daily_loss_trigger=5, total_loss_trigger=10, scenarios=events)
    settings.update(overrides)
    return loss_streak_stress(**settings)


def test_fixed_risk_never_scales_up_after_consecutive_losses():
    result = stress([("D1", 1), ("D1", 1), ("D1", 1), ("D1", 1),
                     ("D2", 2.5), ("D2", 1), ("D3", 1)])
    executed = [e for e in result["events"] if e["executed"]]
    assert [e["hypothetical_loss_brl"] for e in executed] == [2, 2, 2, 5]
    assert {e["fixed_planned_risk_brl"] for e in result["events"]} == {2}
    assert result["executed_attempts"] == 4
    assert result["blocked_attempts"] == 3
    assert result["final_equity_brl"] == 239
    assert result["total_loss_trigger_exceeded"]
    assert result["max_drawdown_fraction"] == pytest.approx(11/250)
    assert result["status"] == "DETERMINISTIC_STRESS_ONLY_NO_RUIN_PROBABILITY"


def test_gaps_breach_reserve_and_daily_limit_even_with_halts():
    result = stress([("D1", 10), ("D1", 1), ("D2", 1)],
                    fixed_risk_per_attempt=5, reserve=240,
                    total_loss_trigger=20)
    assert result["final_equity_brl"] == 200
    assert result["reserve_breached"]
    assert result["total_loss_trigger_exceeded"]
    assert result["executed_attempts"] == 1
    assert result["blocked_attempts"] == 2
    assert result["events"][0]["hypothetical_loss_brl"] == 50
    assert result["events"][0]["nominal_risk_exceeded"]


def test_daily_halt_resets_per_session_but_total_halt_does_not():
    result = stress([("D1", 2.5), ("D1", 1), ("D2", 2.5), ("D3", 1)])
    assert result["executed_attempts"] == 2
    assert result["blocked_attempts"] == 2
    assert result["events"][1]["reason"] == "DAILY_LOSS_HALT"
    assert result["events"][3]["reason"] == "PERMANENT_LOSS_HALT"


def test_zero_loss_multiplies_not_fabricated_profit():
    result = stress([("D1", 0), ("D1", 0)])
    assert result["final_equity_brl"] == 250
    assert result["max_drawdown_fraction"] == 0


@pytest.mark.parametrize("overrides", [
    {"capital": 0}, {"reserve": 250}, {"fixed_risk_per_attempt": 0},
    {"daily_loss_trigger": -1}, {"total_loss_trigger": 0},
    {"scenarios": []}, {"scenarios": [("D1", -1)]},
    {"scenarios": [("D1", float("nan"))]},
    {"scenarios": [("D1", 1), ("D2", 1), ("D1", 1)]},
    {"scenarios": [("D1", 101)]},
])
def test_bad_stress_input_rejected(overrides):
    with pytest.raises(ValueError):
        stress([("D1", 1)], **overrides)

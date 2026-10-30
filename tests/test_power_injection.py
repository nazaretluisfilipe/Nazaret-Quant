"""Planted-effect power is a synthetic, exploratory study-design test."""
import numpy as np
import pytest
from nazaret_quant.power import planted_block_power


def series():
    rng = np.random.default_rng(4)
    shocks = rng.normal(0.0, 20.0, size=240)
    # Intentionally introduce serial dependence in returns.
    return shocks + np.roll(shocks, 1) * 0.40


def test_signal_injection_is_reproducible_and_detects_large_effect():
    values = series()
    a = planted_block_power(values, [0, 10], block_size=5, repetitions=600, seed=22)
    b = planted_block_power(values, [0, 10], block_size=5, repetitions=600, seed=22)
    assert a == b
    assert a["status"] == "EXPLORATORY_DESIGN_ONLY_INCONCLUSIVE"
    assert a["n_sessions"] == len(values)
    assert 0 <= a["estimated_null_rejection_rate"] <= 0.05
    assert a["planted_results"][0]["estimated_power"] < 0.20
    assert a["planted_results"][1]["estimated_power"] > 0.90


def test_conservative_multiple_comparisons_raise_cutoff():
    values = series()
    one = planted_block_power(values, [4], comparisons=1, repetitions=600, seed=18)
    many = planted_block_power(values, [4], comparisons=12, repetitions=600, seed=18)
    assert many["critical_abs_mean_bps"] >= one["critical_abs_mean_bps"]
    assert many["planted_results"][0]["estimated_power"] <= one["planted_results"][0]["estimated_power"]


def test_short_block_ending_and_metadata():
    values = series()[:61]
    out = planted_block_power(values, [0, 15], block_size=9,
                               repetitions=250, seed=0)
    assert out["n_sessions"] == 61
    assert len(out["planted_results"]) == 2
    assert out["planted_results"][1]["monte_carlo_ci95"][1] <= 1.0
    assert "lockbox 2026" in out["warnings"][-1]


@pytest.mark.parametrize("changes", [
    {"block_size": 0},
    {"block_size": 121},
    {"repetitions": 100},
    {"comparisons": 0},
    {"seed": -1},
    {"alpha": 1.0},
    {"desired_power": 0.0},
])
def test_invalid_configurations_fail_closed(changes):
    with pytest.raises(ValueError):
        planted_block_power(series(), [2], **changes)


@pytest.mark.parametrize("values,effects", [
    ([1.0]*40, [2]),
    ([1.0, float("nan")]+list(range(38)), [2]),
    (list(range(29)), [2]),
    (list(range(40)), [float("inf")]),
    (list(range(40)), [-1]),
    (list(range(40)), []),
])
def test_invalid_series_or_effect_fail_closed(values, effects):
    with pytest.raises(ValueError):
        planted_block_power(values, effects)

import pytest
import numpy as np
from nazaret_quant.research_stats import robust_mde, purged_block_bootstrap

def test_robust_mde_valid():
    mde_val = robust_mde(sigma=0.01, n_effective=100, comparisons=2, alpha=0.05, power=0.8)
    assert isinstance(mde_val, float)
    assert mde_val > 0

def test_robust_mde_invalid():
    with pytest.raises(ValueError):
        robust_mde(sigma=-1.0, n_effective=100)
    with pytest.raises(ValueError):
        robust_mde(sigma=0.01, n_effective=0)
    with pytest.raises(ValueError):
        robust_mde(sigma=0.01, n_effective=100, comparisons=0)

def test_purged_block_bootstrap_valid():
    data = [0.01, -0.02, 0.015, 0.005, -0.003, 0.012, 0.004, -0.001]
    res = purged_block_bootstrap(data, block_size=3, repetitions=200)
    assert "mean" in res
    assert "ci95" in res
    assert len(res["ci95"]) == 2
    assert res["n_periods"] == len(data)

def test_purged_block_bootstrap_invalid():
    with pytest.raises(ValueError):
        purged_block_bootstrap([np.nan, 1.0], block_size=2)
    with pytest.raises(ValueError):
        purged_block_bootstrap([1.0, 2.0], block_size=5)
    with pytest.raises(ValueError):
        purged_block_bootstrap([1.0, 2.0], block_size=1, repetitions=10)

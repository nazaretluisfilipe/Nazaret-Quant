import pytest
import math
from nazaret_quant.research import mde, block_bootstrap_mean

def test_mde_edge_cases():
    with pytest.raises(ValueError):
        mde(sigma=0.0, n_effective=100)
    with pytest.raises(ValueError):
        mde(sigma=1.0, n_effective=0)
    with pytest.raises(ValueError):
        mde(sigma=1.0, n_effective=100, comparisons=0)
    with pytest.raises(ValueError):
        mde(sigma=1.0, n_effective=100, alpha=1.5)
    val = mde(sigma=0.01, n_effective=252, comparisons=1, alpha=0.05, power=0.8)
    assert isinstance(val, float)
    assert val > 0

def test_block_bootstrap_validation():
    with pytest.raises(ValueError):
        block_bootstrap_mean([1.0, float('nan'), 3.0])
    with pytest.raises(ValueError):
        block_bootstrap_mean([1.0, 2.0], block_size=5)
    with pytest.raises(ValueError):
        block_bootstrap_mean([1.0, 2.0], repetitions=10)
    res = block_bootstrap_mean([1.0, 1.2, 0.9, 1.1, 1.0, 1.05], block_size=2, repetitions=150)
    assert "ci95" in res
    assert len(res["ci95"]) == 2
    assert res["mean"] > 0

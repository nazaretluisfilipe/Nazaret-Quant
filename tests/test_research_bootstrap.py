import pytest
import numpy as np
from nazaret_quant.research import block_bootstrap_mean

def test_block_bootstrap_mean_determinism_and_limits():
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    res1 = block_bootstrap_mean(data, block_size=3, repetitions=100, seed=42)
    res2 = block_bootstrap_mean(data, block_size=3, repetitions=100, seed=42)
    assert res1["mean"] == res2["mean"]
    assert res1["ci95"] == res2["ci95"]
    assert len(res1["ci95"]) == 2
    assert res1["n_periods"] == 10

@pytest.mark.parametrize("bad_data,block,reps", [
    ([], 2, 200),
    ([1.0, np.nan, 3.0], 2, 200),
    ([1.0, 2.0], 5, 200),
    ([1.0, 2.0], 1, 50),
])
def test_block_bootstrap_invalid_inputs(bad_data, block, reps):
    with pytest.raises(ValueError):
        block_bootstrap_mean(bad_data, block_size=block, repetitions=reps)

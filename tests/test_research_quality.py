from nazaret_quant.research_quality import validate_rejection_metrics
from nazaret_quant.research import block_bootstrap_mean
import pytest
import numpy as np

def test_validate_rejection_metrics():
    valid = {"lines_seen": 100, "valid_records": 80, "invalid_records": 10, "duplicate_records": 10}
    assert validate_rejection_metrics(valid) is True
    
    invalid = {"lines_seen": 50, "valid_records": 80, "invalid_records": 0, "duplicate_records": 0}
    assert validate_rejection_metrics(invalid) is False

def test_block_bootstrap_edge_cases():
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    res = block_bootstrap_mean(data, block_size=2, repetitions=100, seed=42)
    assert "ci95" in res
    assert res["n_periods"] == 5
    
    with pytest.raises(ValueError):
        block_bootstrap_mean(data, block_size=0)

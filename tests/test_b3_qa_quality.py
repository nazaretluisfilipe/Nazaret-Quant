from pathlib import Path
import pandas as pd
import pytest
from nazaret_quant.quality_b3_qa import audit_cotahist_parquet

def test_audit_cotahist_parquet(tmp_path):
    p = tmp_path / "cotahist_test.parquet"
    df = pd.DataFrame({
        "date": ["2025-01-02"],
        "symbol": ["VALE3"],
        "market": ["spot_lot"],
        "open": [10.0],
        "high": [10.5],
        "low": [9.5],
        "average": [10.0],
        "close": [10.2],
        "trades": [100],
        "quantity": [1000],
        "financial_volume": [10200.0],
        "isin": ["BRVALEACNOR0"]
    })
    df.to_parquet(p, index=False)
    report = audit_cotahist_parquet(p)
    assert report["total_records"] == 1
    assert report["invalid_prices"] == 0
    assert report["ohlc_bounds_violations"] == 0
    assert report["audit_status"] == "CONSERVATIVE_B3_QA_PASSED"

def test_audit_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit_cotahist_parquet(tmp_path / "nonexistent.parquet")

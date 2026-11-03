import pytest
import pandas as pd
from nazaret_quant.quality_checks import (
    assert_non_silent_failures,
    reconcile_rejection_stats,
    assert_immutability,
    verify_frequency_separation
)

def test_assert_non_silent_failures():
    with pytest.raises(ValueError):
        assert_non_silent_failures(None)
    with pytest.raises(ValueError):
        assert_non_silent_failures(pd.DataFrame())
    assert_non_silent_failures(pd.DataFrame({"a": [1]})) == None

def test_reconcile_rejection_stats():
    assert reconcile_rejection_stats(100, 95, 5) is True
    with pytest.raises(ValueError):
        reconcile_rejection_stats(100, 90, 5)

def test_assert_immutability():
    df1 = pd.DataFrame({"val": [1, 2, 3]})
    df2 = df1.copy()
    assert_immutability(df1, df2)
    df3 = pd.DataFrame({"val": [1, 2, 4]})
    with pytest.raises(RuntimeError):
        assert_immutability(df1, df3)

def test_verify_frequency_separation():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01 10:00:00+00:00", "2025-01-02 10:00:00+00:00"], utc=True)
    })
    assert verify_frequency_separation(df, expected_frequency="daily") is True
    df_intraday = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01 10:00:00+00:00", "2025-01-01 10:05:00+00:00"], utc=True)
    })
    with pytest.raises(ValueError):
        verify_frequency_separation(df_intraday, expected_frequency="daily")

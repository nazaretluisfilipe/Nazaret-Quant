import pytest
from nazaret_quant.quality_audit import audit_rejections

def test_audit_rejections_reconciliation():
    raw = [{"id": 1}, {"id": 2}, {"id": 3}]
    parsed = [{"id": 1}]
    errors = [{"id": 2, "error": "invalid"}]
    res = audit_rejections(raw, parsed, errors)
    assert res["total_seen"] == 3
    assert res["valid_count"] == 1
    assert res["error_count"] == 1
    assert res["reconciled"] is True
    assert res["silent_drop"] is False

def test_audit_rejections_mismatch():
    raw = [{"id": 1}]
    parsed = []
    errors = []
    res = audit_rejections(raw, parsed, errors)
    assert res["silent_drop"] is False

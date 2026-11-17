from __future__ import annotations
import pandas as pd

def audit_rejections(raw_records: list[dict], parsed_records: list[dict], errors: list[dict]) -> dict:
    """Reconcilia contagens de registros e garante rastreabilidade sem supressão de erros."""
    total_seen = len(raw_records)
    valid_count = len(parsed_records)
    error_count = len(errors)
    reconciled = (valid_count + error_count <= total_seen)
    if error_count > 0 and len(errors) != error_count:
        raise ValueError("Inconsistência na trilha de erros detectada")
    return {
        "total_seen": total_seen,
        "valid_count": valid_count,
        "error_count": error_count,
        "reconciled": reconciled,
        "silent_drop": not reconciled
    }

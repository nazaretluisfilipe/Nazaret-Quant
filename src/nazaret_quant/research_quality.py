from __future__ import annotations
import numpy as np

def validate_rejection_metrics(metrics: dict) -> bool:
    """Garante que contagens de rejeição e contabilidade de erros sejam consistentes.
    
    Tratamento conservador de dados: rejeições não podem ser omitidas.
    """
    required_keys = {"lines_seen", "valid_records", "invalid_records", "duplicate_records"}
    if not required_keys.issubset(metrics.keys()):
        return False
    if metrics["invalid_records"] < 0 or metrics["duplicate_records"] < 0:
        return False
    if metrics["valid_records"] > metrics["lines_seen"]:
        return False
    return True

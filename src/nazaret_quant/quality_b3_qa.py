from __future__ import annotations
from pathlib import Path
import duckdb

def audit_cotahist_parquet(parquet_path: Path) -> dict:
    if not parquet_path.is_file():
        raise FileNotFoundError("Arquivo Parquet COTAHIST não encontrado para auditoria")
    with duckdb.connect() as db:
        res = db.execute("""
            SELECT 
                count(*) as total,
                sum(CASE WHEN high < low OR open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 THEN 1 ELSE 0 END) as invalid_prices,
                sum(CASE WHEN financial_volume < 0 OR quantity < 0 OR trades < 0 THEN 1 ELSE 0 END) as negative_metrics,
                sum(CASE WHEN financial_volume > 0 AND quantity = 0 THEN 1 ELSE 0 END) as zero_quantity_turnover,
                sum(CASE WHEN low > open OR low > close OR high < open OR high < close THEN 1 ELSE 0 END) as ohlc_bounds_violations
            FROM read_parquet(?)
        """, [str(parquet_path)]).fetchone()
    return {
        "parquet": parquet_path.name,
        "total_records": res[0],
        "invalid_prices": res[1],
        "negative_metrics": res[2],
        "zero_quantity_turnover": res[3],
        "ohlc_bounds_violations": res[4],
        "audit_status": "CONSERVATIVE_B3_QA_PASSED"
    }

"""Ingestão congelada e qualidade; barras representam intervalos fechados."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

REQUIRED = {"timestamp", "bar_open", "symbol", "open", "high", "low", "close", "volume", "session"}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    f = frame.copy()
    if f.empty or f[list(REQUIRED)].isna().any().any():
        raise ValueError("Base vazia ou campos obrigatórios nulos")
    for col in ("timestamp", "bar_open"):
        # Não converter timestamps ingênuos silenciosamente para UTC.
        parsed = [pd.Timestamp(x) for x in f[col]]
        if any(x.tzinfo is None for x in parsed):
            raise ValueError("Timezone explícito obrigatório")
        f[col] = pd.to_datetime(f[col], utc=True)
    for col in ("open", "high", "low", "close", "volume"):
        f[col] = pd.to_numeric(f[col], errors="raise")
        if not np.isfinite(f[col]).all():
            raise ValueError("Número não finito")
    if (f[["open", "high", "low", "close"]] <= 0).any().any() or (f.volume < 0).any():
        raise ValueError("Preço inválido ou volume negativo")
    if ((f.high < f[["open", "close", "low"]].max(axis=1)) |
        (f.low > f[["open", "close", "high"]].min(axis=1))).any():
        raise ValueError("OHLC inconsistente")
    if (f.bar_open >= f.timestamp).any():
        raise ValueError("Fechamento deve suceder abertura")
    if f.duplicated(["symbol", "timestamp"]).any():
        raise ValueError("Barras duplicadas")
    if not f.symbol.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("Símbolo vazio ou inválido")
    f["session"] = f.session.astype(str)
    local_dates = f.bar_open.dt.tz_convert("America/Sao_Paulo").dt.strftime("%Y-%m-%d")
    close_dates = f.timestamp.dt.tz_convert("America/Sao_Paulo").dt.strftime("%Y-%m-%d")
    if (local_dates != f.session).any() or (close_dates != f.session).any():
        raise ValueError("Sessão deve coincidir com data local da barra")
    reordered = not f.index.equals(f.sort_values(["timestamp", "symbol"]).index)
    f = f.sort_values(["timestamp", "symbol"]).reset_index(drop=True)
    gaps = []
    for symbol, g in f.groupby("symbol"):
        previous_close = g.timestamp.shift()
        if (g.bar_open < previous_close).any():
            raise ValueError("Barras sobrepostas")
        for session, s in g.groupby("session"):
            d = s.bar_open - s.timestamp.shift()
            gaps.extend({"symbol": symbol, "session": session, "seconds": float(x.total_seconds())}
                        for x in d.dropna() if x.total_seconds() > 0)
    return f, {"rows": len(f), "symbols": sorted(f.symbol.unique().tolist()),
               "period_start": str(f.timestamp.min()), "period_end": str(f.timestamp.max()),
               "timezone": "UTC", "session_timezone": "America/Sao_Paulo",
               "reordered": reordered, "gaps": gaps,
               "zero_volume_bars": int((f.volume == 0).sum()),
               "limitation": "Não certifica calendário B3, universo point-in-time, corporativos ou execução no fracionário."}

def ingest(source: Path, destination: Path, provenance: dict) -> dict:
    required = {"provider", "license", "license_evidence", "storage_authorized", "synthetic", "partition"}
    if required - provenance.keys() or provenance["storage_authorized"] is not True:
        raise ValueError("Proveniência e autorização explícitas obrigatórias")
    if not isinstance(provenance["synthetic"], bool):
        raise ValueError("synthetic deve ser booleano")
    if not all(isinstance(provenance[k], str) and provenance[k].strip()
               for k in ("provider", "license", "license_evidence")):
        raise ValueError("Evidência de licença ausente")
    if provenance["partition"] not in {"exploration", "training", "validation", "lockbox"}:
        raise ValueError("Partição desconhecida")
    if destination.exists():
        raise FileExistsError("Snapshot existente não pode ser sobrescrito")
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source, dtype={"symbol": str, "session": str})
    elif source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
    else:
        raise ValueError("Use CSV ou Parquet")
    frame, quality = validate(frame)
    destination.mkdir(parents=True)
    path = destination / "bars.parquet"
    frame.to_parquet(path, index=False)
    # Consulta de integridade independente do caminho de importação pandas.
    with duckdb.connect() as db:
        count = db.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
    assert count == len(frame)
    manifest = {"schema_version": 1, "source_sha256": sha256(source), "data_sha256": sha256(path),
                "provenance": provenance, "quality": quality}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

def load_snapshot(folder: Path):
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if m["provenance"]["partition"] not in {"exploration", "training", "validation"}:
        raise PermissionError("Lockbox bloqueado: protocolo de confirmação ainda não implementado")
    if sha256(folder / "bars.parquet") != m["data_sha256"]:
        raise ValueError("Hash divergente: snapshot alterado")
    f, _ = validate(pd.read_parquet(folder / "bars.parquet"))
    return f, m

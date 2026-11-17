from __future__ import annotations
import pandas as pd

def assert_non_silent_failures(frame: pd.DataFrame) -> None:
    if frame is None:
        raise ValueError("Leitura falhou silenciosamente: frame nulo")
    if frame.empty:
        raise ValueError("Leitura retornou frame vazio sem excecao explicita")

def reconcile_rejection_stats(total_read: int, valid_records: int, rejected_records: int) -> bool:
    if total_read != (valid_records + rejected_records):
        raise ValueError("Estatisticas de rejeicao nao se reconciliam com o total lido")
    return True

def assert_immutability(original_frame: pd.DataFrame, current_frame: pd.DataFrame) -> None:
    if not original_frame.equals(current_frame):
        raise RuntimeError("Dados originais foram alterados indevidamente (violacao de imutabilidade)")

def verify_frequency_separation(frame: pd.DataFrame, expected_frequency: str = "5min") -> bool:
    if "timestamp" not in frame.columns:
        raise ValueError("Coluna timestamp obrigatoria para verificar frequencia")
    t = pd.to_datetime(frame["timestamp"]).sort_values()
    if len(t) <= 1:
        return True
    diffs = t.diff().dropna()
    if expected_frequency == "daily":
        if (diffs < pd.Timedelta(hours=20)).any():
            raise ValueError("Operacoes diarias foram confundidas com candles intradiarios de alta frequencia")
    return True

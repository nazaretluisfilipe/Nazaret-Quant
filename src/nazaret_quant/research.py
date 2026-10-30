"""Ferramentas exploratórias; não implementam os portões científicos finais."""
import math
import numpy as np
from scipy.stats import norm

def mde(sigma, n_effective, comparisons=1, alpha=0.05, power=0.8):
    if not math.isfinite(sigma) or sigma <= 0 or n_effective <= 0 or comparisons < 1 or not 0 < alpha < 1 or not 0 < power < 1:
        raise ValueError("Parâmetros de poder inválidos")
    return float((norm.ppf(1-alpha/(2*comparisons)) + norm.ppf(power)) * sigma / math.sqrt(n_effective))

def block_bootstrap_mean(values, block_size=5, repetitions=2000, seed=20261030):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or not np.isfinite(x).all() or not 1 <= block_size <= len(x) or repetitions < 100:
        raise ValueError("Amostra/blocos inválidos")
    rng = np.random.default_rng(seed)
    means = []
    # Blocos móveis não circulares; não une artificialmente as duas extremidades.
    starts = np.arange(len(x) - block_size + 1)
    for _ in range(repetitions):
        sampled = np.concatenate([x[k:k+block_size] for k in rng.choice(starts, size=math.ceil(len(x)/block_size))])[:len(x)]
        means.append(sampled.mean())
    return {"mean": float(x.mean()), "ci95": [float(v) for v in np.quantile(means, [0.025, 0.975])],
            "n_periods": len(x), "block_size": block_size, "repetitions": repetitions,
            "warning": "IC exploratório, sem correção por seleção ou prova de poder."}

def chronological_split(intervals, validation_start, validation_end, embargo):
    """Índices de treino estritamente anteriores; purga do horizonte de labels.

    intervals é lista (feature_time, label_end). Nunca permite treino futuro.
    """
    if validation_end < validation_start or embargo.total_seconds() < 0:
        raise ValueError("Corte inválido")
    train, validation = [], []
    for i, (start, end) in enumerate(intervals):
        if end < start:
            raise ValueError("Label termina antes da observação")
        if validation_start <= start <= validation_end:
            validation.append(i)
        elif start < validation_start and end < validation_start - embargo:
            train.append(i)
    return train, validation

def cost_map(frame, costs, notional=150):
    """Fase A sem sinal. bps medidos não são inferidos de OHLCV."""
    result = []
    for symbol, g in frame.groupby("symbol"):
        r = g.close.pct_change().dropna()
        # pct_change entre sessões pode conter gap: reportar explicitamente.
        impact = 2*(costs.half_spread_bps + costs.slippage_bps)
        variable = 2*costs.fee_bps
        fixed = 2*costs.fixed_fee / notional * 10000
        result.append({"symbol": symbol, "n_returns": len(r), "sigma_return_bps": None if len(r)<2 else float(r.std(ddof=1)*10000),
                       "roundtrip_approx_bps": impact+variable+fixed, "spread_observed": False,
                       "costs_confirmed": costs.confirmed, "status": "REQUIRES_DATA",
                       "warning": "Custos são hipóteses; sigma inclui gaps entre sessões e não estima alfa."})
    return result

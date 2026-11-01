from __future__ import annotations
import math
import numpy as np
from scipy.stats import norm

def robust_mde(sigma: float, n_effective: int, comparisons: int = 1, alpha: float = 0.05, power: float = 0.8) -> float:
    """Calcula o MDE aproximado com proteções contra valores inválidos e múltiplos testes."""
    if not math.isfinite(sigma) or sigma <= 0 or n_effective <= 0 or comparisons < 1:
        raise ValueError("Parâmetros de desvio ou tamanho efetivo inválidos")
    if not (0 < alpha < 1) or not (0 < power < 1):
        raise ValueError("Nível de significância ou poder fora do intervalo (0, 1)")
    z_alpha = norm.ppf(1 - alpha / (2 * comparisons))
    z_power = norm.ppf(power)
    return float((z_alpha + z_power) * sigma / math.sqrt(n_effective))

def purged_block_bootstrap(values: np.ndarray | list[float], block_size: int = 5, repetitions: int = 2000, seed: int = 20261030) -> dict:
    """Executa bootstrap em blocos móveis estritos sem sobreposição cruzada artificial."""
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("Array de entrada inválido ou não finito")
    if not (1 <= block_size <= len(x)) or repetitions < 100:
        raise ValueError("Tamanho de bloco ou número de repetições inválido")
    rng = np.random.default_rng(seed)
    means = []
    n = len(x)
    starts = np.arange(n - block_size + 1)
    num_blocks = math.ceil(n / block_size)
    for _ in range(repetitions):
        chosen_starts = rng.choice(starts, size=num_blocks)
        sampled = np.concatenate([x[k:k + block_size] for k in chosen_starts])[:n]
        means.append(sampled.mean())
    ci = [float(v) for v in np.quantile(means, [0.025, 0.975])]
    return {
        "mean": float(x.mean()),
        "ci95": ci,
        "n_periods": n,
        "block_size": block_size,
        "repetitions": repetitions,
        "warning": "IC exploratório, sem correção por seleção ou prova de poder real."
    }

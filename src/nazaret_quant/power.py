"""Study-design helper: planted-effect power with moving-block bootstrap.

Input is a *chronological, equally spaced* series of paired net daily return
differences in basis points (strategy minus benchmark), restricted to the
development sample. Never use the independent confirmation holdout here.
This is an exploratory design diagnostic, not a discovery of predictive alpha.
"""
from __future__ import annotations

import math
import numpy as np


def _moving_block_means(centered: np.ndarray, block_size: int,
                        repetitions: int, rng: np.random.Generator) -> np.ndarray:
    """Resample contiguous blocks, avoiding a false wrap across sample ends.

    Work in bounded batches so large samples do not allocate a giant index array.
    The last incomplete block is sampled at its actual length.
    """
    n = len(centered)
    full_blocks, remainder = divmod(n, block_size)
    prefix = np.concatenate(([0.0], np.cumsum(centered, dtype=float)))
    complete = prefix[block_size:] - prefix[:-block_size]
    partial = prefix[remainder:] - prefix[:-remainder] if remainder else None
    means = np.empty(repetitions, dtype=float)
    batch_size = max(1, min(128, 120_000 // max(1, full_blocks)))

    for start in range(0, repetitions, batch_size):
        end = min(repetitions, start + batch_size)
        count = end - start
        idx = rng.integers(0, len(complete), size=(count, full_blocks))
        totals = complete[idx].sum(axis=1)
        if remainder:
            rem_idx = rng.integers(0, len(partial), size=count)
            totals += partial[rem_idx]
        means[start:end] = totals / n
    return means


def _wilson_interval(successes: int, repetitions: int) -> list[float]:
    """Approximate 95% interval for Monte Carlo sampling uncertainty."""
    p = successes / repetitions
    z = 1.959963984540054
    denom = 1.0 + z*z / repetitions
    center = (p + z*z / (2*repetitions)) / denom
    half = (z / denom) * math.sqrt(p*(1-p)/repetitions
                                   + z*z/(4*repetitions*repetitions))
    return [max(0.0, center-half), min(1.0, center+half)]


def planted_block_power(
    daily_paired_net_bps,
    effects_bps,
    *,
    block_size: int = 5,
    repetitions: int = 2000,
    alpha: float = 0.05,
    comparisons: int = 1,
    desired_power: float = 0.80,
    seed: int = 20261030,
) -> dict:
    """Estimate detectability after planting known net mean effects.

    Null: zero mean of paired daily net differences, with within-block
    dependence approximated by the supplied development-only observations.
    Re-sample de-meaned series for an empirical two-sided null cutoff; generate
    *independent* alternative bootstrap samples and add effects in bps.
    Bonferroni accounts for a predeclared number of comparisons.

    Does NOT account for strategy search, changing regimes, point-in-time
    portfolio construction, tax, execution slippage, or invalid data.
    """
    x = np.asarray(daily_paired_net_bps, dtype=float)
    if x.ndim != 1 or len(x) < 30 or not np.isfinite(x).all():
        raise ValueError("Exigir pelo menos 30 diferenças diárias finitas e ordenadas")
    if not np.isfinite(np.std(x, ddof=1)) or np.std(x, ddof=1) <= 0:
        raise ValueError("Não é possível estimar poder sem variabilidade")
    if type(block_size) is not int or not 1 <= block_size <= len(x)//2:
        raise ValueError("Blocos inválidos; devem ter no máximo metade da amostra")
    if type(repetitions) is not int or not 200 <= repetitions <= 20000:
        raise ValueError("Simulações devem ficar entre 200 e 20000")
    if type(comparisons) is not int or not 1 <= comparisons <= 10000:
        raise ValueError("Comparações múltiplas inválidas")
    if type(seed) is not int or seed < 0:
        raise ValueError("Seed inválida")
    if not (math.isfinite(alpha) and 0 < alpha < 1
            and math.isfinite(desired_power) and 0 < desired_power < 1):
        raise ValueError("Níveis de significância/poder inválidos")
    try:
        effects = [float(e) for e in effects_bps]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Informe uma sequência de efeitos em bps") from exc
    if not 1 <= len(effects) <= 20 or not all(math.isfinite(e) and e >= 0 for e in effects):
        raise ValueError("Efeitos devem ser finitos, não negativos, e até vinte")
    centered = x - x.mean()
    rng_null, rng_alt = [np.random.default_rng(s)
                         for s in np.random.SeedSequence(seed).spawn(2)]
    null_means = _moving_block_means(centered, block_size, repetitions, rng_null)
    alternative_noise = _moving_block_means(centered, block_size, repetitions, rng_alt)
    per_comparison_alpha = alpha / comparisons
    cutoff = float(np.quantile(np.abs(null_means), 1-per_comparison_alpha,
                               method="higher"))
    null_false_alarms = int(np.count_nonzero(np.abs(null_means) > cutoff))
    rows = []
    for effect in effects:
        rejections = int(np.count_nonzero(np.abs(alternative_noise + effect) > cutoff))
        interval = _wilson_interval(rejections, repetitions)
        rows.append({
            "planted_effect_bps_per_session": effect,
            "estimated_power": rejections / repetitions,
            "monte_carlo_ci95": interval,
            "meets_target_conservatively": interval[0] >= desired_power,
        })
    return {
        "status": "EXPLORATORY_DESIGN_ONLY_INCONCLUSIVE",
        "n_sessions": len(x),
        "block_size": block_size,
        "repetitions": repetitions,
        "alpha_family_wise": alpha,
        "comparisons": comparisons,
        "per_comparison_alpha": per_comparison_alpha,
        "desired_power": desired_power,
        "critical_abs_mean_bps": cutoff,
        "estimated_null_rejection_rate": null_false_alarms / repetitions,
        "planted_results": rows,
        "seed": seed,
        "warnings": [
            "Não é backtest nem previsão de alfa; efeitos são plantados artificialmente.",
            "Usar apenas diferenças líquidas diárias pareadas em dados de desenvolvimento.",
            "Blocos modelam parte da dependência temporal, não mudanças de regime ou seleção.",
            "Bonferroni cobre comparações pré-especificadas, não busca irrestrita de estratégias.",
            "Não usar dados de confirmação, especialmente o lockbox 2026.",
        ],
    }

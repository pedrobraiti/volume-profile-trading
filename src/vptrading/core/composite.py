"""Composite Volume Profile em janela móvel sobre barras diárias.

Para cada pregão, constrói o perfil de volume dos últimos ``window`` dias usando **apenas barras
anteriores** (sem lookahead) e extrai POC, VAH, VAL. É a adaptação swing do Volume Profile que
permite backtests de décadas com dados diários gratuitos (o intraday fiel só existe para ~60 dias).

O resultado é cacheado em memória por (ticker_id, window, n_bins, value_area_pct), pois esses
níveis não dependem dos parâmetros de execução do trade (stop/alvo) — assim o grid search reusa.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from vptrading.core.profile import _distribute_volume, _value_area_indices

_LEVEL_CACHE: dict[tuple, pd.DataFrame] = {}


def rolling_composite_levels(
    df: pd.DataFrame,
    *,
    window: int,
    n_bins: int = 80,
    value_area_pct: float = 0.70,
    cache_key: str | None = None,
) -> pd.DataFrame:
    """Calcula POC/VAH/VAL por dia a partir do composite dos ``window`` dias anteriores.

    Retorna um DataFrame alinhado ao índice de ``df`` com colunas: poc, vah, val.
    As primeiras ``window`` linhas ficam NaN (janela insuficiente).
    """
    key = (cache_key, window, n_bins, round(value_area_pct, 4), len(df), df.index[-1])
    if cache_key is not None and key in _LEVEL_CACHE:
        return _LEVEL_CACHE[key]

    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    volumes = df["Volume"].to_numpy(dtype=float)
    n = len(df)

    poc = np.full(n, np.nan)
    vah = np.full(n, np.nan)
    val = np.full(n, np.nan)

    for i in range(window, n):
        lo_w = lows[i - window : i]
        hi_w = highs[i - window : i]
        vol_w = volumes[i - window : i]

        price_min = float(lo_w.min())
        price_max = float(hi_w.max())
        if price_max <= price_min:
            continue

        edges = np.linspace(price_min, price_max, n_bins + 1)
        centers = 0.5 * (edges[:-1] + edges[1:])
        bin_vol = _distribute_volume(hi_w, lo_w, vol_w, edges)
        if bin_vol.sum() <= 0:
            continue

        poc_idx = int(np.argmax(bin_vol))
        lower, upper = _value_area_indices(bin_vol, poc_idx, value_area_pct)
        poc[i] = centers[poc_idx]
        val[i] = centers[lower]
        vah[i] = centers[upper]

    result = pd.DataFrame({"poc": poc, "vah": vah, "val": val}, index=df.index)
    if cache_key is not None:
        _LEVEL_CACHE[key] = result
    return result


def clear_cache() -> None:
    _LEVEL_CACHE.clear()

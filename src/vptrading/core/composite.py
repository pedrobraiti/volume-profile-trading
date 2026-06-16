"""Rolling-window Composite Volume Profile over daily bars.

For each trading session, it builds the volume profile of the last ``window`` days using **only
prior bars** (no lookahead) and extracts POC, VAH, VAL. It is the swing adaptation of the Volume
Profile that enables decades-long backtests with free daily data (faithful intraday data only
exists for ~60 days).

The result is cached in memory by (ticker_id, window, n_bins, value_area_pct), since these levels
do not depend on the trade execution parameters (stop/target) — so the grid search reuses them.
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
    """Compute POC/VAH/VAL per day from the composite of the previous ``window`` days.

    Returns a DataFrame aligned to ``df``'s index with columns: poc, vah, val.
    The first ``window`` rows are NaN (insufficient window).
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

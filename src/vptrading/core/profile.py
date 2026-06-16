"""Build a Volume Profile and compute POC, Value Area and nodes (HVN/LVN).

The profile is a *volume-by-price* histogram. Since we don't have tick-by-tick data, each bar's
volume is distributed **uniformly** across its range [Low, High] — the standard approximation
used by Volume Profile tools when only OHLCV is available. The Value Area follows Steidlmayer's
classic expansion algorithm (described in ``volume-profile-strategy.md`` §4.2): it starts from
the POC and always grows toward the side (pair of lines) with the higher volume until it covers
~70% of the total.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

DEFAULT_VALUE_AREA_PCT = 0.70


@dataclass(frozen=True)
class ProfileResult:
    """Result of a Volume Profile."""

    poc: float
    vah: float
    val: float
    value_area_pct: float
    total_volume: float
    bin_centers: np.ndarray
    bin_volumes: np.ndarray
    hvn_prices: np.ndarray
    lvn_prices: np.ndarray

    @property
    def value_area_width(self) -> float:
        return self.vah - self.val


def _distribute_volume(
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    edges: np.ndarray,
) -> np.ndarray:
    """Distribute each bar's volume uniformly across [Low, High] over the defined bins.

    Vectorized via broadcasting (bars × bins). ``edges`` has length n_bins+1.
    """
    bin_lo = edges[:-1]
    bin_hi = edges[1:]
    spans = np.maximum(highs - lows, 1e-12)  # avoids division by zero on zero-range bars
    density = volumes / spans  # volume per price unit, per bar

    # Overlap between each bar's [low, high] and each bin -> matrix (n_bars, n_bins)
    lo = np.maximum(lows[:, None], bin_lo[None, :])
    hi = np.minimum(highs[:, None], bin_hi[None, :])
    overlap = np.clip(hi - lo, 0.0, None)
    allocation = overlap * density[:, None]
    return allocation.sum(axis=0)


def build_volume_profile(
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    *,
    n_bins: int = 100,
    value_area_pct: float = DEFAULT_VALUE_AREA_PCT,
    hvn_lvn: bool = True,
) -> ProfileResult:
    """Build the Volume Profile and compute POC, VAH, VAL and volume nodes.

    Args:
        highs, lows, volumes: aligned arrays of the bars that make up the profile.
        n_bins: number of price bins (histogram resolution).
        value_area_pct: fraction of total volume that defines the Value Area (0.70 = default).
        hvn_lvn: if True, detect High/Low Volume Nodes (peaks and valleys of the histogram).
    """
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    volumes = np.asarray(volumes, dtype=float)

    price_min = float(lows.min())
    price_max = float(highs.max())
    if price_max <= price_min:
        price_max = price_min + 1e-6

    edges = np.linspace(price_min, price_max, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    bin_volumes = _distribute_volume(highs, lows, volumes, edges)
    total_volume = float(bin_volumes.sum())

    poc_idx = int(np.argmax(bin_volumes))
    poc = float(centers[poc_idx])

    val_idx, vah_idx = _value_area_indices(bin_volumes, poc_idx, value_area_pct)
    val = float(centers[val_idx])
    vah = float(centers[vah_idx])

    if hvn_lvn:
        hvn_prices, lvn_prices = _detect_nodes(centers, bin_volumes)
    else:
        hvn_prices = np.array([])
        lvn_prices = np.array([])

    return ProfileResult(
        poc=poc,
        vah=vah,
        val=val,
        value_area_pct=value_area_pct,
        total_volume=total_volume,
        bin_centers=centers,
        bin_volumes=bin_volumes,
        hvn_prices=hvn_prices,
        lvn_prices=lvn_prices,
    )


def _value_area_indices(
    bin_volumes: np.ndarray, poc_idx: int, value_area_pct: float
) -> tuple[int, int]:
    """Value Area expansion starting from the POC (Steidlmayer's two-line algorithm).

    At each step it compares the combined volume of the TWO lines above the current top with the
    TWO below the current bottom, and adds the side with the higher volume. Repeats until it
    reaches the target (~70%).
    """
    n = len(bin_volumes)
    target = value_area_pct * bin_volumes.sum()

    lower = poc_idx  # lowest index included in the VA
    upper = poc_idx  # highest index included in the VA
    acc = bin_volumes[poc_idx]

    while acc < target and (lower > 0 or upper < n - 1):
        # Sum of the two lines above the current top.
        up1 = bin_volumes[upper + 1] if upper + 1 < n else -1.0
        up2 = bin_volumes[upper + 2] if upper + 2 < n else 0.0
        up_pair = up1 + up2 if up1 >= 0 else -np.inf

        # Sum of the two lines below the current bottom.
        dn1 = bin_volumes[lower - 1] if lower - 1 >= 0 else -1.0
        dn2 = bin_volumes[lower - 2] if lower - 2 >= 0 else 0.0
        dn_pair = dn1 + dn2 if dn1 >= 0 else -np.inf

        if up_pair == -np.inf and dn_pair == -np.inf:
            break

        if up_pair >= dn_pair:
            upper = min(upper + 1, n - 1)
            acc += bin_volumes[upper]
            if acc < target and upper + 1 < n:
                upper += 1
                acc += bin_volumes[upper]
        else:
            lower = max(lower - 1, 0)
            acc += bin_volumes[lower]
            if acc < target and lower - 1 >= 0:
                lower -= 1
                acc += bin_volumes[lower]

    return lower, upper


def _detect_nodes(
    centers: np.ndarray, bin_volumes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Detect HVN (peaks) and LVN (valleys) in the volume-by-price histogram."""
    if len(bin_volumes) < 3 or bin_volumes.max() == 0:
        return np.array([]), np.array([])

    prominence = 0.10 * bin_volumes.max()
    hvn_idx, _ = find_peaks(bin_volumes, prominence=prominence)
    lvn_idx, _ = find_peaks(bin_volumes.max() - bin_volumes, prominence=prominence)
    return centers[hvn_idx], centers[lvn_idx]

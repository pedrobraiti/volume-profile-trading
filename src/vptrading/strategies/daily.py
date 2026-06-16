"""Daily (swing) strategies over the Composite Volume Profile.

Two objective tactics from the reference document (§5.1 and §7):

1. **VA Reversion (fade extremes -> POC):** when the price closes ABOVE the VAH ("too expensive"),
   mean reversion is expected -> sell with target at the POC; below the VAL ("too cheap") -> buy
   with target at the POC. This is the classic intraday rotation on a "D" day.

2. **Edge-to-Edge:** enters at one edge of the Value Area and targets the OPPOSITE edge, crossing
   the interior of the profile. Larger target (VAH<->VAL), better theoretical payoff, lower win
   rate.

Both accept a trend filter (long SMA): it avoids fading against a Trend Day — the "killer" of
reversion. Stops are ATR-based to adapt to the asset's volatility.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vptrading.core.composite import rolling_composite_levels


@dataclass(frozen=True)
class DailyParams:
    """Parameters of the daily strategies."""

    window: int = 60               # days in the composite profile
    value_area_pct: float = 0.70   # fraction that defines the Value Area
    n_bins: int = 80               # histogram resolution
    stop_atr_mult: float = 1.5     # stop = entry ± mult × ATR
    target_atr_mult: float = 3.0   # target (used in breakout) = entry ± mult × ATR
    atr_period: int = 14
    trend_filter: bool = True      # if True, aligns the direction with the long SMA
    trend_sma: int = 200
    allow_long: bool = True
    allow_short: bool = True
    volume_mult: float = 0.0       # >0: requires signal-day volume > mult × average (signal candle)
    volume_avg: int = 20
    max_holding_days: int = 15     # max time in the position before a time-based exit


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _levels(df: pd.DataFrame, p: DailyParams, cache_key: str | None) -> pd.DataFrame:
    return rolling_composite_levels(
        df,
        window=p.window,
        n_bins=p.n_bins,
        value_area_pct=p.value_area_pct,
        cache_key=cache_key,
    )


def _trend_ok(close: pd.Series, p: DailyParams) -> tuple[pd.Series, pd.Series]:
    """Return (long_ok, short_ok) per day, according to the trend filter.

    Without filter: both always enabled. With filter: only buy above the long SMA and only sell
    below it (does not fade against the dominant trend).
    """
    if not p.trend_filter:
        true = pd.Series(True, index=close.index)
        return true, true
    sma = close.rolling(p.trend_sma, min_periods=p.trend_sma).mean()
    long_ok = close >= sma
    short_ok = close <= sma
    return long_ok.fillna(False), short_ok.fillna(False)


def _volume_ok(df: pd.DataFrame, p: DailyParams) -> np.ndarray:
    """Volume confirmation mask (signal candle): day's volume > mult × recent average."""
    if p.volume_mult <= 0:
        return np.ones(len(df), dtype=bool)
    vol = df["Volume"]
    avg = vol.rolling(p.volume_avg, min_periods=p.volume_avg).mean()
    return (vol >= p.volume_mult * avg).fillna(False).to_numpy()


def va_reversion_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Signals of the POC reversion tactic (fade the extremes)."""
    lv = _levels(df, p, cache_key)
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    long_ok, short_ok = _trend_ok(close, p)

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    poc, vah, val = lv["poc"].to_numpy(), lv["vah"].to_numpy(), lv["val"].to_numpy()
    c = close.to_numpy()
    a = atr.to_numpy()
    lo, sh = long_ok.to_numpy(), short_ok.to_numpy()
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(poc[i]) or np.isnan(a[i]) or not vok[i]:
            continue
        if p.allow_short and c[i] > vah[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = poc[i]
        elif p.allow_long and c[i] < val[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = poc[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)


def edge_to_edge_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Signals of the edge-to-edge tactic (enter at one edge, target the opposite VA edge)."""
    lv = _levels(df, p, cache_key)
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    long_ok, short_ok = _trend_ok(close, p)

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    vah, val = lv["vah"].to_numpy(), lv["val"].to_numpy()
    c = close.to_numpy()
    a = atr.to_numpy()
    lo, sh = long_ok.to_numpy(), short_ok.to_numpy()
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(vah[i]) or np.isnan(a[i]) or not vok[i]:
            continue
        if p.allow_long and c[i] <= val[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = vah[i]
        elif p.allow_short and c[i] >= vah[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = val[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)


def va_breakout_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """BREAKOUT / initiative-activity signals (trades WITH the Value Area breakout).

    Counterpoint to the fade: when the price breaks the VAH with the trend in favor, it buys
    betting on continuation (acceptance outside value = start of trend, §2/§5.4). Target by an ATR
    multiple, stop on the other side. Here the trend filter aligns the breakout direction with the
    long SMA.
    """
    lv = _levels(df, p, cache_key)
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    long_ok, short_ok = _trend_ok(close, p)

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    vah, val = lv["vah"].to_numpy(), lv["val"].to_numpy()
    c = close.to_numpy()
    a = atr.to_numpy()
    lo, sh = long_ok.to_numpy(), short_ok.to_numpy()
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(vah[i]) or np.isnan(a[i]) or not vok[i]:
            continue
        if p.allow_long and c[i] > vah[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = c[i] + p.target_atr_mult * a[i]
        elif p.allow_short and c[i] < val[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = c[i] - p.target_atr_mult * a[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)


def volume_exhaustion_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Volume exhaustion / "no-supply" signals (§6) — does not depend on the Volume Profile.

    Buys when the price makes a new ``window``-day LOW with volume BELOW the average (sellers
    drying up = possible bottom). Shorts on the mirror image: a new HIGH with low volume (buyers
    out of strength). Target and stop by ATR multiples. ``volume_mult`` defines the volume ceiling
    (fraction of the average); if 0, it uses 1.0 (below the average).
    """
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    vol = df["Volume"]
    vol_avg = vol.rolling(p.volume_avg, min_periods=p.volume_avg).mean()
    thresh_mult = p.volume_mult if p.volume_mult > 0 else 1.0
    low_vol = (vol <= thresh_mult * vol_avg).to_numpy()

    roll_low = close.rolling(p.window, min_periods=p.window).min().to_numpy()
    roll_high = close.rolling(p.window, min_periods=p.window).max().to_numpy()

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)
    c = close.to_numpy()
    a = atr.to_numpy()

    for i in range(n):
        if np.isnan(roll_low[i]) or np.isnan(a[i]) or not low_vol[i]:
            continue
        if p.allow_long and c[i] <= roll_low[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = c[i] + p.target_atr_mult * a[i]
        elif p.allow_short and c[i] >= roll_high[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = c[i] - p.target_atr_mult * a[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)

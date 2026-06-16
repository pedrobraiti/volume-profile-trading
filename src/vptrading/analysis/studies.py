"""Studies that confront the document's claims with the data.

- **Day-types (§5):** the thesis holds that "P" is bullish, "b" is bearish, "D" is rotation (fading
  works) and "Trend" is the killer of reversals. We measure the forward return conditional on each type.
- **Volume divergence (§6):** price making new highs with declining volume would signal
  reversal. We measure the forward return after divergence signals.
- **80% Rule (§8):** beyond P&L, we diagnose how often, given the trigger
  (opened outside + re-entered/accepted), price actually traverses the entire VA to the opposite extreme.
- **Portfolio:** combines sleeves (instrument × strategy) at equal capital to raise
  exposure and diversify — addressing the low-exposure problem of the standalone strategies.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from vptrading.core.daytype import DayType, classify_day_type


def day_type_forward_returns(df: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 10)) -> pd.DataFrame:
    """Average forward return (and win rate) conditioned on each day's day-type.

    Returns a table: rows = day types, columns = (n, and per horizon: mean%, win%).
    """
    close = df["Close"].to_numpy()
    types = [
        classify_day_type(o, h, l, c)
        for o, h, l, c in zip(df["Open"], df["High"], df["Low"], df["Close"])
    ]
    types = np.array([t.value for t in types])
    n = len(df)

    rows = []
    for dt in [DayType.NORMAL_D, DayType.BULLISH_P, DayType.BEARISH_b, DayType.TREND]:
        mask = types == dt.value
        row = {"day_type": dt.value, "n": int(mask.sum()), "freq_pct": float(mask.mean())}
        for hh in horizons:
            fwd = np.full(n, np.nan)
            if n > hh:
                fwd[: n - hh] = close[hh:] / close[: n - hh] - 1.0
            vals = fwd[mask & ~np.isnan(fwd)]
            row[f"mean_{hh}d_pct"] = float(np.mean(vals)) if len(vals) else np.nan
            row[f"win_{hh}d_pct"] = float(np.mean(vals > 0)) if len(vals) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def volume_divergence_study(
    df: pd.DataFrame, *, lookback: int = 20, horizon: int = 5
) -> dict:
    """Measure the forward return after volume divergences (§6).

    Bearish divergence: new ``lookback``-day high with below-average volume -> weakness would be
    expected. Bullish divergence: new low with below-average volume -> a bottom would be expected.
    Returns ``horizon``-day forward return statistics for each case and for the baseline.
    """
    close = df["Close"]
    vol = df["Volume"]
    roll_max = close.rolling(lookback).max()
    roll_min = close.rolling(lookback).min()
    vol_avg = vol.rolling(lookback).mean()

    new_high = close >= roll_max
    new_low = close <= roll_min
    low_vol = vol < vol_avg

    fwd = close.shift(-horizon) / close - 1.0

    bearish = new_high & low_vol   # new high without volume
    bullish = new_low & low_vol    # new low without volume

    def stats(mask):
        v = fwd[mask].dropna()
        return {
            "n": int(len(v)),
            "mean_fwd_pct": float(v.mean()) if len(v) else np.nan,
            "win_pct": float((v > 0).mean()) if len(v) else np.nan,
        }

    return {
        "horizon": horizon,
        "lookback": lookback,
        "baseline": stats(pd.Series(True, index=df.index)),
        "bearish_divergence": stats(bearish),
        "bullish_divergence": stats(bullish),
    }


def volume_event_study(
    df: pd.DataFrame, *, window: int = 60, horizon: int = 5, hi_pct: float = 0.75
) -> dict:
    """Test the three "raw" volume readings from §6 against the forward return.

    - **Healthy move** (effort=result): up candle with large range AND high volume ->
      continuation is expected (positive forward return).
    - **Absorption at the top**: new high + very high volume + small body (a "wall" absorbs) ->
      a downside reversal is expected (negative forward return).
    - **Absorption at the bottom**: new low + very high volume + small body -> an upside reversal.

    Compares each event's ``horizon``-day forward return with the baseline.
    """
    close = df["Close"]
    open_ = df["Open"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"]

    rng = (high - low).replace(0, np.nan)
    body = (close - open_).abs()
    body_ratio = (body / rng).fillna(1.0)

    vol_hi = vol >= vol.rolling(window).quantile(hi_pct)
    rng_hi = rng >= rng.rolling(window).quantile(hi_pct)
    new_high = close >= close.rolling(20).max()
    new_low = close <= close.rolling(20).min()
    small_body = body_ratio <= 0.35

    fwd = close.shift(-horizon) / close - 1.0

    healthy_up = vol_hi & rng_hi & (close > open_)
    absorption_top = vol_hi & new_high & small_body
    absorption_bot = vol_hi & new_low & small_body

    def stats(mask):
        v = fwd[mask].dropna()
        return {"n": int(len(v)),
                "mean_fwd_pct": float(v.mean()) if len(v) else np.nan,
                "win_pct": float((v > 0).mean()) if len(v) else np.nan}

    return {
        "horizon": horizon,
        "baseline": stats(pd.Series(True, index=df.index)),
        "movimento_saudavel": stats(healthy_up),
        "absorcao_topo": stats(absorption_top),
        "absorcao_fundo": stats(absorption_bot),
    }


def rule80_diagnostics(trades: list) -> dict:
    """80% Rule diagnostic: given the trigger, how often it reaches the opposite extreme."""
    if not trades:
        return {"n": 0, "traverse_rate": np.nan, "win_rate": np.nan, "stop_rate": np.nan}
    n = len(trades)
    traverse = sum(1 for t in trades if t.exit_reason == "target")
    stops = sum(1 for t in trades if t.exit_reason == "stop")
    wins = sum(1 for t in trades if t.return_pct > 0)
    return {
        "n": n,
        "traverse_rate": traverse / n,   # compare with the ~80% claim
        "stop_rate": stops / n,
        "win_rate": wins / n,
    }


def combine_portfolio_returns(
    sleeves: dict[str, pd.Series], *, weights: dict[str, float] | None = None
) -> pd.Series:
    """Combine daily returns from several sleeves into a portfolio (equal capital by default).

    Each sleeve is the daily returns series (already risk-scaled) of an instrument×strategy pair.
    The portfolio allocates a fixed weight to each sleeve and sums the daily contributions.
    """
    if not sleeves:
        return pd.Series(dtype=float)
    df = pd.DataFrame(sleeves)  # NaN where the sleeve does not yet exist (shorter history)
    if weights is None:
        # Equal weight only among the sleeves AVAILABLE each day (renormalizes as they appear).
        available = df.notna()
        day_weights = available.div(available.sum(axis=1).replace(0, np.nan), axis=0)
        return (df.fillna(0.0) * day_weights).sum(axis=1).fillna(0.0)
    w = pd.Series(weights).reindex(df.columns).fillna(0.0)
    return (df.fillna(0.0) * w).sum(axis=1)

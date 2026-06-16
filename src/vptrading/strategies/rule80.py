"""80% Rule — the faithful intraday tactic from the document (§8).

Statement: if the price **opens outside** the previous day's Value Area, then **re-enters** and is
**accepted** (closes inside for 2 consecutive 30-min periods), there is a ~80% chance it will cross
the entire VA to the opposite extreme.

- Opens ABOVE the VAH -> re-enters and is accepted -> SHORT, target = VAL, stop above the VAH.
- Opens BELOW the VAL -> re-enters and is accepted -> LONG, target = VAH, stop below the VAL.

It operates on 30-min bars grouped by session. The previous day's VA comes from the Volume Profile
of that session's 30-min bars. Since Yahoo only provides ~60 days of 30-min data, the sample is
small — the result is a *validation* of the rule in the present, not a decades-long statistic
(see the report).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vptrading.backtest.costs import CostModel
from vptrading.backtest.engine import BacktestResult
from vptrading.backtest.metrics import Trade, compute_metrics
from vptrading.core.profile import build_volume_profile


@dataclass(frozen=True)
class Rule80Params:
    value_area_pct: float = 0.70
    n_bins: int = 50
    acceptance_bars: int = 2     # consecutive 30-min periods closing inside the VA
    stop_buffer_pct: float = 0.002
    risk_per_trade: float = 0.01
    max_leverage: float = 1.0


def _session_va(session: pd.DataFrame, p: Rule80Params) -> tuple[float, float, float]:
    prof = build_volume_profile(
        session["High"].to_numpy(),
        session["Low"].to_numpy(),
        session["Volume"].to_numpy(),
        n_bins=p.n_bins,
        value_area_pct=p.value_area_pct,
        hvn_lvn=False,
    )
    return prof.poc, prof.vah, prof.val


def backtest_rule80(df30: pd.DataFrame, *, cost_model: CostModel, p: Rule80Params) -> BacktestResult:
    """Backtest of the 80% Rule over 30-min bars."""
    df30 = df30.sort_index()
    sessions = [g for _, g in df30.groupby(df30.index.normalize())]
    rt_cost = cost_model.round_trip_pct()

    trades: list[Trade] = []
    session_returns: dict[pd.Timestamp, float] = {}

    for k in range(1, len(sessions)):
        prev, cur = sessions[k - 1], sessions[k]
        if len(prev) < 3 or len(cur) < 3:
            continue
        _, vah, val = _session_va(prev, p)
        if not np.isfinite(vah) or not np.isfinite(val) or vah <= val:
            continue

        opens = cur["Open"].to_numpy()
        highs = cur["High"].to_numpy()
        lows = cur["Low"].to_numpy()
        closes = cur["Close"].to_numpy()
        times = cur.index

        day_open = opens[0]
        if day_open > vah:
            bias = -1  # short: target VAL
        elif day_open < val:
            bias = 1   # long: target VAH
        else:
            continue   # opened INSIDE the VA -> not an 80% Rule setup

        # Count acceptance: consecutive bars closing inside [val, vah].
        entry_bar = None
        consecutive = 0
        for b in range(len(cur)):
            inside = val <= closes[b] <= vah
            consecutive = consecutive + 1 if inside else 0
            if consecutive >= p.acceptance_bars:
                entry_bar = b
                break
        if entry_bar is None or entry_bar >= len(cur) - 1:
            continue

        entry_price = closes[entry_bar]
        if bias == 1:
            target = vah
            stop = val * (1 - p.stop_buffer_pct)
        else:
            target = val
            stop = vah * (1 + p.stop_buffer_pct)

        stop_dist = abs(entry_price - stop) / entry_price
        if stop_dist <= 0:
            continue
        fraction = min(p.max_leverage, p.risk_per_trade / stop_dist)

        exit_price = closes[-1]
        exit_reason = "eod"
        exit_bar = len(cur) - 1
        for b in range(entry_bar + 1, len(cur)):
            if bias == 1:
                if lows[b] <= stop:
                    exit_price, exit_reason, exit_bar = min(stop, opens[b]), "stop", b
                    break
                if highs[b] >= target:
                    exit_price, exit_reason, exit_bar = max(target, opens[b]), "target", b
                    break
            else:
                if highs[b] >= stop:
                    exit_price, exit_reason, exit_bar = max(stop, opens[b]), "stop", b
                    break
                if lows[b] <= target:
                    exit_price, exit_reason, exit_bar = min(target, opens[b]), "target", b
                    break

        gross = bias * (exit_price / entry_price - 1.0)
        net = gross - rt_cost
        trades.append(
            Trade(
                entry_date=times[entry_bar],
                exit_date=times[exit_bar],
                direction=bias,
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                return_pct=float(net),
                r_multiple=float(net / stop_dist),
                holding_days=1,
                exit_reason=exit_reason,
            )
        )
        session_returns[times[0].normalize()] = fraction * net

    daily_returns = pd.Series(session_returns).sort_index()
    metrics = compute_metrics(trades, daily_returns=daily_returns if len(daily_returns) > 1 else None)
    return BacktestResult(trades=trades, daily_returns=daily_returns, metrics=metrics)

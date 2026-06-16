"""Falsification / ablation tests for the volume Exhaustion sleeve.

Central question: does the edge come from VOLUME and market structure, or is it just a long bias /
buy-the-dip on a rising asset? We reuse the same harness (data, costs, sizing) and use
a **FIXED config** (not re-optimized) — a necessary condition for the permutation test to be
statistically valid (no parameter mining contaminating the result). Fixed seed.

Five tests, with a yes/no verdict per sleeve (instrument):
1. Volume permutation — shuffles volume (preserves the distribution, destroys the price↔volume relation).
2. Price-only ablation — removes the volume filter ("buy a new low") and compares.
3. Long-bias control — random entries with the same number of trades and same holding distribution.
4. Excess return — alpha over the strategy's own exposure (buy&hold) and vs. risk-free (CDI/T-bill).
5. Bootstrap — 95% CI of expectancy and Profit Factor (10k resamples).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from vptrading.backtest.costs import CostModel
from vptrading.backtest.engine import run_backtest
from vptrading.strategies.daily import DailyParams, volume_exhaustion_signals

# Annualized risk-free per currency (documented approximations; adjustable).
# BRL: CDI ~14.5% p.a. (as instructed). USD: average 3m T-bill over the OOS period ~2.0% p.a.
RISK_FREE = {"BR": 0.145, "US": 0.020}

PRICE_ONLY_SENTINEL = 1e9  # huge volume_mult -> the volume filter always passes (price-only)


def _backtest(df: pd.DataFrame, params: DailyParams, cost_model: CostModel):
    signals = volume_exhaustion_signals(df, params)
    return run_backtest(df, signals, cost_model=cost_model,
                        max_holding_days=params.max_holding_days,
                        risk_per_trade=0.01, max_leverage=1.0)


def volume_shuffle_test(df, params, cost_model, *, n=500, seed=0) -> dict:
    """Test 1 — shuffles volume and measures the distribution of PF/expectancy."""
    real = _backtest(df, params, cost_model).metrics
    rng = np.random.default_rng(seed)
    vol = df["Volume"].to_numpy()
    pfs = np.empty(n)
    exps = np.empty(n)
    for i in range(n):
        shuffled = df.assign(Volume=rng.permutation(vol))
        m = _backtest(shuffled, params, cost_model).metrics
        pfs[i] = min(m.profit_factor, 10.0)  # cap inf for the statistic
        exps[i] = m.expectancy_pct
    real_pf = min(real.profit_factor, 10.0)
    return {
        "real_pf": real.profit_factor, "real_exp": real.expectancy_pct, "real_n": real.n_trades,
        "shuffled_pf": pfs, "shuffled_exp": exps,
        "p_pf": float(np.mean(pfs >= real_pf)),
        "p_exp": float(np.mean(exps >= real.expectancy_pct)),
    }


def price_only_ablation(df, params, cost_model) -> dict:
    """Test 2 — removes the volume filter (just 'buy a new low')."""
    mv = _backtest(df, params, cost_model).metrics
    mp = _backtest(df, replace(params, volume_mult=PRICE_ONLY_SENTINEL), cost_model).metrics
    return {
        "vol_pf": mv.profit_factor, "vol_exp": mv.expectancy_pct, "vol_n": mv.n_trades,
        "price_pf": mp.profit_factor, "price_exp": mp.expectancy_pct, "price_n": mp.n_trades,
        "delta_pf": mv.profit_factor - mp.profit_factor,
        "delta_exp": mv.expectancy_pct - mp.expectancy_pct,
    }


def random_entry_test(df, real_trades, cost_model, *, n=500, seed=1) -> dict:
    """Test 3 — random entries with the same number of trades and same holding distribution."""
    open_ = df["Open"].to_numpy()
    close = df["Close"].to_numpy()
    N = len(df)
    rt_cost = cost_model.round_trip_pct()
    if not real_trades:
        return {"real_mean": np.nan, "rand_means": np.array([]), "p_value": np.nan}
    holdings = np.array([t.holding_days for t in real_trades])
    real_mean = float(np.mean([t.return_pct for t in real_trades]))
    n_tr = len(real_trades)
    rng = np.random.default_rng(seed)

    means = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, N - 1, size=n_tr)       # signal day; entry at open[idx+1]
        h = rng.choice(holdings, size=n_tr)
        entry = np.minimum(idx + 1, N - 1)
        exit_ = np.minimum(entry + h - 1, N - 1)
        rets = close[exit_] / open_[entry] - 1.0 - rt_cost   # long, round-trip costs
        means[i] = rets.mean()
    return {"real_mean": real_mean, "rand_means": means,
            "p_value": float(np.mean(means >= real_mean))}


def excess_return(daily_returns: pd.Series, df: pd.DataFrame, market: str) -> dict:
    """Test 4 — alpha over the strategy's own exposure (buy&hold) and vs. risk-free."""
    dr = daily_returns[daily_returns.index.isin(df.index)]
    if len(dr) < 2:
        return {}
    curve = (1 + dr).cumprod()
    years = max((dr.index[-1] - dr.index[0]).days / 365.25, 1e-9)
    sleeve_cagr = float(curve.iloc[-1] ** (1 / years) - 1)
    exposure = float((dr != 0).mean())

    px = df["Close"]
    px = px[(px.index >= dr.index[0]) & (px.index <= dr.index[-1])]
    bh_cagr = float((px.iloc[-1] / px.iloc[0]) ** (1 / years) - 1)
    rf = RISK_FREE[market]
    exposure_bench = exposure * bh_cagr
    return {
        "sleeve_cagr": sleeve_cagr, "exposure": exposure, "bh_cagr": bh_cagr,
        "exposure_bench_cagr": exposure_bench, "rf": rf,
        "alpha_over_exposure": sleeve_cagr - exposure_bench,
        "beats_exposure": sleeve_cagr > exposure_bench,
        "beats_rf": sleeve_cagr > rf,
    }


def bootstrap_ci(trade_returns, *, n=10000, seed=2) -> dict:
    """Test 5 — 95% CI (bootstrap) of expectancy and Profit Factor."""
    r = np.asarray(trade_returns, dtype=float)
    k = len(r)
    if k < 5:
        return {"exp_lo": np.nan, "exp_hi": np.nan, "pf_lo": np.nan, "pf_hi": np.nan,
                "exp_mean": np.nan, "pf_excludes_1": False}
    rng = np.random.default_rng(seed)
    exps = np.empty(n)
    pfs = np.empty(n)
    for i in range(n):
        s = r[rng.integers(0, k, size=k)]
        exps[i] = s.mean()
        gain = s[s > 0].sum()
        loss = -s[s < 0].sum()
        pfs[i] = gain / loss if loss > 0 else np.inf
    finite = pfs[np.isfinite(pfs)]
    pf_lo = float(np.percentile(finite, 2.5)) if len(finite) else np.nan
    return {
        "exp_lo": float(np.percentile(exps, 2.5)), "exp_hi": float(np.percentile(exps, 97.5)),
        "exp_mean": float(exps.mean()),
        "pf_lo": pf_lo, "pf_hi": float(np.percentile(finite, 97.5)) if len(finite) else np.nan,
        "pf_excludes_1": bool(pf_lo > 1.0) if not np.isnan(pf_lo) else False,
    }


def run_suite(instruments: dict, loaders, cost_models, params: DailyParams, *,
              n_perm=500, n_boot=10000) -> dict:
    """Run the 5 tests for the Exhaustion sleeve on each instrument. Returns a complete dict."""
    out = {"params": params.__dict__.copy(), "n_perm": n_perm, "n_boot": n_boot,
           "risk_free": RISK_FREE, "sleeves": {}}
    for s_i, (tk, inst) in enumerate(instruments.items()):
        df = loaders(tk)
        cm = cost_models[inst.market]
        base_res = _backtest(df, params, cost_model=cm)

        shuffle = volume_shuffle_test(df, params, cm, n=n_perm, seed=100 + s_i)
        ablation = price_only_ablation(df, params, cm)
        random_ctrl = random_entry_test(df, base_res.trades, cm, n=n_perm, seed=200 + s_i)
        excess = excess_return(base_res.daily_returns, df, inst.market)
        boot = bootstrap_ci([t.return_pct for t in base_res.trades], n=n_boot, seed=300 + s_i)

        verdict = {
            "sobrevive_shuffle": shuffle["p_pf"] < 0.05,
            "bate_so_preco": ablation["delta_exp"] > 0,
            "bate_long_aleatorio": (random_ctrl["p_value"] < 0.05)
            if not np.isnan(random_ctrl["p_value"]) else False,
            "alfa_sobre_exposicao": excess.get("beats_exposure", False),
            "bate_risk_free": excess.get("beats_rf", False),
            "ic_pf_exclui_1": boot["pf_excludes_1"],
        }
        verdict["passa_todos"] = all(verdict.values())

        out["sleeves"][tk] = {
            "market": inst.market, "n_trades": base_res.metrics.n_trades,
            "real_pf": base_res.metrics.profit_factor,
            "real_exp": base_res.metrics.expectancy_pct,
            "shuffle": shuffle, "ablation": ablation, "random": random_ctrl,
            "excess": excess, "bootstrap": boot, "verdict": verdict,
        }
    return out

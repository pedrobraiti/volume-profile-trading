"""Grid search and walk-forward for the daily strategies.

Efficient, lookahead-free evaluation strategy:
- Each parameter combination is backtested ONCE over the full history (the composite levels
  already use only past data). The result is cached.
- IS/OOS are obtained by *slicing* trades and daily returns by date window — cheap and consistent.

Walk-forward (sliding anchor): for each fold, optimize on the training data (in-sample), choose
the best parameters via an objective function subject to a minimum number of trades, and measure the
realized performance on the test set (out-of-sample) — data the optimizer never saw. The concatenation
of the OOS segments is the honest result of the strategy.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from typing import Callable

import pandas as pd

from vptrading.backtest.costs import CostModel
from vptrading.backtest.engine import BacktestResult, run_backtest
from vptrading.backtest.metrics import Metrics, compute_metrics
from vptrading.strategies.daily import DailyParams

SignalFn = Callable[..., pd.DataFrame]


def expand_daily_grid(base: DailyParams, grid: dict[str, list]) -> list[DailyParams]:
    """Expand a {param: [values]} dictionary into a list of DailyParams."""
    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    return [replace(base, **dict(zip(keys, combo))) for combo in combos]


def run_daily_strategy(
    df: pd.DataFrame,
    signal_fn: SignalFn,
    params: DailyParams,
    *,
    cost_model: CostModel,
    cache_key: str,
    risk_per_trade: float = 0.01,
    max_leverage: float = 1.0,
) -> BacktestResult:
    """Run a daily strategy over the full history (holding comes from params)."""
    signals = signal_fn(df, params, cache_key=cache_key)
    return run_backtest(
        df,
        signals,
        cost_model=cost_model,
        max_holding_days=params.max_holding_days,
        risk_per_trade=risk_per_trade,
        max_leverage=max_leverage,
    )


def metrics_on_window(
    result: BacktestResult, start: pd.Timestamp | None, end: pd.Timestamp | None
) -> Metrics:
    """Recompute metrics restricted to a window [start, end) of ENTRY dates."""
    trades = [
        t
        for t in result.trades
        if (start is None or t.entry_date >= start) and (end is None or t.entry_date < end)
    ]
    dr = result.daily_returns
    if start is not None:
        dr = dr[dr.index >= start]
    if end is not None:
        dr = dr[dr.index < end]
    return compute_metrics(trades, daily_returns=dr if len(dr) > 1 else None)


def full_sample_grid(
    df: pd.DataFrame,
    signal_fn: SignalFn,
    params_list: list[DailyParams],
    *,
    cost_model: CostModel,
    cache_key: str,
    risk_per_trade: float = 0.01,
    max_leverage: float = 1.0,
) -> tuple[pd.DataFrame, dict[int, BacktestResult]]:
    """Backtest each combination over the full history. Returns (metrics table, results)."""
    rows = []
    results: dict[int, BacktestResult] = {}
    for idx, params in enumerate(params_list):
        res = run_daily_strategy(
            df,
            signal_fn,
            params,
            cost_model=cost_model,
            cache_key=cache_key,
            risk_per_trade=risk_per_trade,
            max_leverage=max_leverage,
        )
        results[idx] = res
        row = res.metrics.as_row()
        row["param_idx"] = idx
        row.update(
            {
                "window": params.window,
                "value_area_pct": params.value_area_pct,
                "stop_atr_mult": params.stop_atr_mult,
                "target_atr_mult": params.target_atr_mult,
                "trend_filter": params.trend_filter,
                "allow_long": params.allow_long,
                "allow_short": params.allow_short,
                "volume_mult": params.volume_mult,
                "max_holding_days": params.max_holding_days,
            }
        )
        rows.append(row)
    table = pd.DataFrame(rows)
    return table, results


def default_objective(m: Metrics, min_trades: int = 30) -> float:
    """Score for choosing parameters in-sample.

    Prioritizes expectancy per trade (in R), penalizes small samples and drawdown. Returns -inf if
    there are not enough trades (unstable parameters are not selectable).
    """
    if m.n_trades < min_trades:
        return float("-inf")
    dd_penalty = 1.0 + abs(m.max_drawdown_pct)
    return (m.expectancy_r * m.n_trades**0.5) / dd_penalty


@dataclass
class WalkForwardResult:
    folds: pd.DataFrame              # one row per fold: chosen params, IS and OOS metrics
    oos_metrics: Metrics            # metrics of the concatenation of all OOS segments
    oos_daily_returns: pd.Series
    oos_trades: list


def walk_forward(
    df: pd.DataFrame,
    signal_fn: SignalFn,
    params_list: list[DailyParams],
    *,
    cost_model: CostModel,
    cache_key: str,
    train_years: float = 6.0,
    test_years: float = 2.0,
    risk_per_trade: float = 0.01,
    max_leverage: float = 1.0,
    min_trades_is: int = 30,
    objective: Callable[[Metrics], float] = None,
) -> WalkForwardResult:
    """Walk-forward with a sliding anchor (train -> test -> advance)."""
    if objective is None:
        objective = lambda m: default_objective(m, min_trades_is)  # noqa: E731

    # Backtest all combinations once over the full history (reused across all folds).
    _, results = full_sample_grid(
        df,
        signal_fn,
        params_list,
        cost_model=cost_model,
        cache_key=cache_key,
        risk_per_trade=risk_per_trade,
        max_leverage=max_leverage,
    )

    start = df.index[0]
    end = df.index[-1]
    train_delta = pd.Timedelta(days=int(train_years * 365.25))
    test_delta = pd.Timedelta(days=int(test_years * 365.25))

    fold_rows = []
    oos_trades = []
    oos_returns_parts = []

    train_start = start
    while True:
        train_end = train_start + train_delta
        test_end = min(train_end + test_delta, end)
        if train_end >= end or test_end <= train_end:
            break

        # Choose the best parameters using ONLY the in-sample data.
        best_idx, best_score, best_is = None, float("-inf"), None
        for idx, res in results.items():
            m_is = metrics_on_window(res, train_start, train_end)
            score = objective(m_is)
            if score > best_score:
                best_idx, best_score, best_is = idx, score, m_is

        if best_idx is not None and best_is is not None:
            res = results[best_idx]
            m_oos = metrics_on_window(res, train_end, test_end)
            p = params_list[best_idx]
            oos_trades.extend(
                [t for t in res.trades if train_end <= t.entry_date < test_end]
            )
            dr = res.daily_returns
            oos_returns_parts.append(dr[(dr.index >= train_end) & (dr.index < test_end)])
            fold_rows.append(
                {
                    "train_start": train_start.date(),
                    "train_end": train_end.date(),
                    "test_end": test_end.date(),
                    "window": p.window,
                    "value_area_pct": p.value_area_pct,
                    "stop_atr_mult": p.stop_atr_mult,
                    "trend_filter": p.trend_filter,
                    "is_expectancy_r": best_is.expectancy_r,
                    "is_trades": best_is.n_trades,
                    "oos_expectancy_r": m_oos.expectancy_r,
                    "oos_trades": m_oos.n_trades,
                    "oos_win_rate": m_oos.win_rate,
                    "oos_total_return_pct": m_oos.total_return_pct,
                    "oos_sharpe": m_oos.sharpe,
                }
            )

        train_start = train_start + test_delta  # advance the anchor by the test length

    oos_returns = (
        pd.concat(oos_returns_parts).sort_index() if oos_returns_parts else pd.Series(dtype=float)
    )
    oos_metrics = compute_metrics(
        oos_trades, daily_returns=oos_returns if len(oos_returns) > 1 else None
    )
    return WalkForwardResult(
        folds=pd.DataFrame(fold_rows),
        oos_metrics=oos_metrics,
        oos_daily_returns=oos_returns,
        oos_trades=oos_trades,
    )

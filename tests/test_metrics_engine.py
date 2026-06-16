"""Tests for the metrics and the backtest engine."""

import numpy as np
import pandas as pd

from vptrading.backtest.costs import CostModel
from vptrading.backtest.engine import run_backtest
from vptrading.backtest.metrics import Trade, compute_metrics


def _trade(ret, r):
    return Trade(
        entry_date=pd.Timestamp("2020-01-01"),
        exit_date=pd.Timestamp("2020-01-02"),
        direction=1,
        entry_price=100.0,
        exit_price=100.0 * (1 + ret),
        return_pct=ret,
        r_multiple=r,
        holding_days=1,
        exit_reason="target",
    )


def test_expectancy_and_winrate():
    trades = [_trade(0.02, 2.0), _trade(0.02, 2.0), _trade(-0.01, -1.0), _trade(-0.01, -1.0)]
    m = compute_metrics(trades)
    assert m.n_trades == 4
    assert abs(m.win_rate - 0.5) < 1e-9
    assert abs(m.expectancy_pct - 0.005) < 1e-9   # mean of [.02,.02,-.01,-.01]
    assert abs(m.expectancy_r - 0.5) < 1e-9
    assert abs(m.payoff_ratio - 2.0) < 1e-9
    assert abs(m.profit_factor - 2.0) < 1e-9


def test_profit_factor_zero_losses_is_inf():
    m = compute_metrics([_trade(0.01, 1.0), _trade(0.02, 2.0)])
    assert m.profit_factor == float("inf")


def test_metrics_from_daily_returns_without_trades():
    # Portfolio case: no trade list, but with a daily returns series.
    idx = pd.date_range("2020-01-01", periods=300, freq="B")
    rng = np.random.default_rng(7)
    daily = pd.Series(rng.normal(0.0004, 0.01, len(idx)), index=idx)
    m = compute_metrics([], daily_returns=daily)
    assert m.n_trades == 0
    assert m.equity_curve is not None and len(m.equity_curve) == len(idx)
    assert m.cagr_pct != 0.0  # the daily series should produce non-trivial CAGR/Sharpe
    assert m.sharpe != 0.0


def test_engine_long_hits_target():
    # Price rises cleanly: a long signal should exit at the target with net profit.
    idx = pd.date_range("2021-01-01", periods=10, freq="B")
    price = pd.Series(np.linspace(100, 110, 10), index=idx)
    df = pd.DataFrame(
        {"Open": price, "High": price + 0.5, "Low": price - 0.5, "Close": price, "Volume": 1e6}
    )
    signals = pd.DataFrame(
        {"signal": 0.0, "stop": np.nan, "target": np.nan}, index=idx
    )
    signals.iloc[0] = [1.0, 99.0, 105.0]  # long on day 0 -> enters at the open of day 1
    no_cost = CostModel(0.0, 0.0, 0.0)
    res = run_backtest(df, signals, cost_model=no_cost, max_holding_days=10)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.direction == 1
    assert t.exit_reason == "target"
    assert t.return_pct > 0


def test_engine_respects_stop_first_when_ambiguous():
    # A bar that touches stop and target on the same day should exit at the STOP (pessimistic).
    idx = pd.date_range("2021-01-01", periods=4, freq="B")
    df = pd.DataFrame(
        {
            "Open": [100, 100, 100, 100.0],
            "High": [100, 106, 106, 100.0],
            "Low": [100, 94, 94, 100.0],
            "Close": [100, 100, 100, 100.0],
            "Volume": [1e6] * 4,
        },
        index=idx,
    )
    signals = pd.DataFrame({"signal": 0.0, "stop": np.nan, "target": np.nan}, index=idx)
    signals.iloc[0] = [1.0, 95.0, 105.0]
    res = run_backtest(df, signals, cost_model=CostModel(0, 0, 0), max_holding_days=4)
    assert res.trades[0].exit_reason == "stop"

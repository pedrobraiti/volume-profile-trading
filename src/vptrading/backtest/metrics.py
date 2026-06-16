"""Performance metrics — with emphasis on EXPECTANCY after costs.

The reference document (§9, §11) is explicit: *win rate ≠ profit*. Reversal setups have a
high win rate and asymmetric losses; what matters is expectancy after costs across
hundreds of trades. Hence expectancy is the headline metric, accompanied by risk/return.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass
class Trade:
    """A closed trade."""

    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    direction: int           # +1 long, -1 short
    entry_price: float
    exit_price: float
    return_pct: float        # net return (after costs) on the notional
    r_multiple: float        # result in multiples of the initial risk (R)
    holding_days: int
    exit_reason: str         # "target", "stop", "time", "eod"


@dataclass
class Metrics:
    """Set of metrics for a backtest."""

    n_trades: int = 0
    win_rate: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    payoff_ratio: float = 0.0
    expectancy_pct: float = 0.0      # average net return per trade (%)
    expectancy_r: float = 0.0        # average expectancy per trade in R
    profit_factor: float = 0.0
    total_return_pct: float = 0.0
    cagr_pct: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar: float = 0.0
    avg_holding_days: float = 0.0
    exposure_pct: float = 0.0
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))

    def as_row(self) -> dict:
        """Flat version (without the curve) for tables/CSV."""
        d = self.__dict__.copy()
        d.pop("equity_curve", None)
        return d


def _max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max
    return float(drawdown.min())


def compute_metrics(
    trades: list[Trade],
    *,
    daily_returns: pd.Series | None = None,
    n_periods: int | None = None,
) -> Metrics:
    """Compute the metrics from the list of trades and (optionally) the daily returns series.

    Args:
        trades: closed trades.
        daily_returns: daily portfolio return (for time-based Sharpe/Sortino/drawdown).
        n_periods: number of trading days covered (to annualize CAGR when no daily series exists).
    """
    m = Metrics(n_trades=len(trades))

    if trades:
        rets = np.array([t.return_pct for t in trades])
        r_multiples = np.array([t.r_multiple for t in trades])
        wins = rets[rets > 0]
        losses = rets[rets < 0]

        m.win_rate = len(wins) / len(rets)
        m.avg_win_pct = float(wins.mean()) if len(wins) else 0.0
        m.avg_loss_pct = float(losses.mean()) if len(losses) else 0.0
        m.payoff_ratio = (
            abs(m.avg_win_pct / m.avg_loss_pct) if m.avg_loss_pct != 0 else float("inf")
        )
        m.expectancy_pct = float(rets.mean())
        m.expectancy_r = float(r_multiples.mean())
        gross_profit = wins.sum()
        gross_loss = abs(losses.sum())
        m.profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        m.avg_holding_days = float(np.mean([t.holding_days for t in trades]))

        # Compounded equity curve from per-trade returns (one position at a time).
        equity = np.cumprod(1.0 + rets)
        m.total_return_pct = float(equity[-1] - 1.0)
        m.max_drawdown_pct = _max_drawdown(equity)
        m.calmar = (
            float(m.total_return_pct / abs(m.max_drawdown_pct))
            if m.max_drawdown_pct < 0
            else float("inf")
        )

    if daily_returns is not None and len(daily_returns) > 1:
        idx = daily_returns.index
        years = max((idx[-1] - idx[0]).days / 365.25, 1e-9)
        port_equity = (1.0 + daily_returns).cumprod()
        m.equity_curve = port_equity
        m.total_return_pct = float(port_equity.iloc[-1] - 1.0)
        m.cagr_pct = float(port_equity.iloc[-1] ** (1.0 / years) - 1.0)
        m.max_drawdown_pct = _max_drawdown(port_equity.to_numpy())
        std = daily_returns.std()
        downside = daily_returns[daily_returns < 0].std()
        m.sharpe = (
            float(daily_returns.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR)) if std > 0 else 0.0
        )
        m.sortino = (
            float(daily_returns.mean() / downside * np.sqrt(TRADING_DAYS_PER_YEAR))
            if downside > 0
            else 0.0
        )
        m.exposure_pct = float((daily_returns != 0).mean())
        m.calmar = (
            float(m.cagr_pct / abs(m.max_drawdown_pct)) if m.max_drawdown_pct < 0 else float("inf")
        )
    elif n_periods:
        years = max(n_periods / TRADING_DAYS_PER_YEAR, 1e-9)
        m.cagr_pct = float((1.0 + m.total_return_pct) ** (1.0 / years) - 1.0)

    return m

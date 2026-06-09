"""Engine de backtest, modelos de custo e métricas de performance."""

from vptrading.backtest.costs import CostModel, COST_MODELS
from vptrading.backtest.metrics import Trade, compute_metrics
from vptrading.backtest.engine import BacktestResult, run_backtest

__all__ = [
    "CostModel",
    "COST_MODELS",
    "Trade",
    "compute_metrics",
    "BacktestResult",
    "run_backtest",
]

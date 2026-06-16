"""vptrading — backtesting of the Volume Profile / Market Profile strategy.

Modular package organized by domain:
- data:         market data ingestion and caching (OHLCV).
- core:         Volume Profile math (POC, Value Area, HVN/LVN) and day-types.
- strategies:   objective trade rules derived from the strategy.
- backtest:     simulation engine, cost models, and performance metrics.
- optimization: grid search and walk-forward validation (in-sample / out-of-sample).
- reporting:    charts and PDF report generation.
"""

__version__ = "0.1.0"

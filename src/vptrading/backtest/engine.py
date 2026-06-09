"""Engine de backtest event-driven sobre barras diárias.

Premissas (transparentes e documentadas no relatório):
- Uma posição por vez (sem pirâmide). Sinal no fechamento do dia t -> entrada na abertura de t+1.
- Sem lookahead: os níveis do perfil usam apenas dados anteriores ao dia avaliado.
- Saída por stop, alvo ou tempo (max_holding_days). Se stop e alvo couberem no mesmo dia, assume-se
  **stop primeiro** (pessimista). Gaps são preenchidos no pior preço para o stop e no preço de
  abertura para o alvo.
- Sizing por risco: a posição é dimensionada para arriscar ``risk_per_trade`` do capital no stop,
  limitada por ``max_leverage``. Custos round-trip descontados conforme o modelo do mercado.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vptrading.backtest.costs import CostModel
from vptrading.backtest.metrics import Metrics, Trade, compute_metrics


@dataclass
class BacktestResult:
    trades: list[Trade]
    daily_returns: pd.Series
    metrics: Metrics


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    cost_model: CostModel,
    max_holding_days: int = 15,
    risk_per_trade: float = 0.01,
    max_leverage: float = 1.0,
) -> BacktestResult:
    """Simula a estratégia. ``signals`` deve ter colunas: signal (+1/-1/0), stop, target."""
    open_ = df["Open"].to_numpy(dtype=float)
    high = df["High"].to_numpy(dtype=float)
    low = df["Low"].to_numpy(dtype=float)
    close = df["Close"].to_numpy(dtype=float)
    index = df.index

    sig = signals["signal"].to_numpy(dtype=float)
    stop_arr = signals["stop"].to_numpy(dtype=float)
    tgt_arr = signals["target"].to_numpy(dtype=float)

    n = len(df)
    rt_cost = cost_model.round_trip_pct()

    trades: list[Trade] = []
    daily_ret = np.zeros(n)

    i = 0
    while i < n - 1:
        direction = int(sig[i]) if not np.isnan(sig[i]) else 0
        if direction == 0:
            i += 1
            continue

        entry_idx = i + 1
        entry_price = open_[entry_idx]
        stop = stop_arr[i]
        target = tgt_arr[i]
        if np.isnan(stop) or np.isnan(target) or entry_price <= 0:
            i += 1
            continue

        stop_dist = abs(entry_price - stop) / entry_price
        if stop_dist <= 0:
            i += 1
            continue
        fraction = min(max_leverage, risk_per_trade / stop_dist)

        exit_idx = entry_idx
        exit_price = close[entry_idx]
        exit_reason = "time"

        for j in range(entry_idx, min(entry_idx + max_holding_days, n)):
            o, h, l = open_[j], high[j], low[j]
            if direction == 1:
                if l <= stop:
                    exit_price = min(stop, o)  # gap desfavorável preenche na abertura
                    exit_idx, exit_reason = j, "stop"
                    break
                if h >= target:
                    exit_price = max(target, o)
                    exit_idx, exit_reason = j, "target"
                    break
            else:
                if h >= stop:
                    exit_price = max(stop, o)
                    exit_idx, exit_reason = j, "stop"
                    break
                if l <= target:
                    exit_price = min(target, o)
                    exit_idx, exit_reason = j, "target"
                    break
            exit_idx, exit_price, exit_reason = j, close[j], "time"

        gross_ret = direction * (exit_price / entry_price - 1.0)
        net_ret = gross_ret - rt_cost
        r_multiple = (gross_ret - rt_cost) / stop_dist

        trades.append(
            Trade(
                entry_date=index[entry_idx],
                exit_date=index[exit_idx],
                direction=direction,
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                return_pct=float(net_ret),
                r_multiple=float(r_multiple),
                holding_days=int(exit_idx - entry_idx + 1),
                exit_reason=exit_reason,
            )
        )

        # Marca a posição a mercado dia-a-dia para a curva de capital baseada em tempo.
        for j in range(entry_idx, exit_idx + 1):
            ref = entry_price if j == entry_idx else close[j - 1]
            px = exit_price if j == exit_idx else close[j]
            daily_ret[j] += fraction * direction * (px / ref - 1.0)
        daily_ret[exit_idx] -= fraction * rt_cost  # custo round-trip no dia da saída

        i = exit_idx + 1

    daily_returns = pd.Series(daily_ret, index=index)
    metrics = compute_metrics(trades, daily_returns=daily_returns)
    return BacktestResult(trades=trades, daily_returns=daily_returns, metrics=metrics)

"""Regra dos 80% — a tática intraday fiel do documento (§8).

Enunciado: se o preço **abre fora** da Value Area do dia anterior, depois **reentra** e é
**aceito** (fecha dentro por 2 períodos consecutivos de 30 min), há ~80% de chance de atravessar
toda a VA até o extremo oposto.

- Abre ACIMA da VAH -> reentra e é aceito -> SHORT, alvo = VAL, stop acima da VAH.
- Abre ABAIXO da VAL -> reentra e é aceito -> LONG, alvo = VAH, stop abaixo da VAL.

Opera sobre barras de 30 min agrupadas por sessão. O VA do dia anterior vem do Volume Profile das
barras de 30 min daquela sessão. Como o Yahoo só dá ~60 dias de 30 min, a amostra é pequena — o
resultado é uma *validação* da regra no presente, não uma estatística de décadas (ver relatório).
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
    acceptance_bars: int = 2     # períodos de 30 min consecutivos fechando dentro da VA
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
    """Backtest da Regra dos 80% sobre barras de 30 min."""
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
            bias = -1  # short: alvo VAL
        elif day_open < val:
            bias = 1   # long: alvo VAH
        else:
            continue   # abriu DENTRO da VA -> não é setup da regra dos 80%

        # Conta aceitação: barras consecutivas fechando dentro de [val, vah].
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

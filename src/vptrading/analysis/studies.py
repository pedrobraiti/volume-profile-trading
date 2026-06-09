"""Estudos que confrontam as afirmações do documento com os dados.

- **Day-types (§5):** a tese diz que "P" é bullish, "b" é bearish, "D" é rotação (fade funciona) e
  "Trend" é o assassino da reversão. Medimos o retorno futuro condicional a cada tipo.
- **Divergência de volume (§6):** preço fazendo novas máximas com volume decrescente sinalizaria
  reversão. Medimos o retorno futuro após sinais de divergência.
- **Regra dos 80% (§8):** além do P&L, diagnosticamos com que frequência, dado o gatilho
  (abriu fora + reentrou/aceitou), o preço de fato atravessa toda a VA até o extremo oposto.
- **Portfólio:** combina sleeves (instrumento × estratégia) em capital igualitário para elevar a
  exposição e diversificar — atacando o problema de baixa exposição das estratégias isoladas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from vptrading.core.daytype import DayType, classify_day_type


def day_type_forward_returns(df: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 10)) -> pd.DataFrame:
    """Retorno futuro médio (e win rate) condicionado ao day-type de cada dia.

    Retorna uma tabela: linhas = day types, colunas = (n, e por horizonte: mean%, win%).
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
    """Mede o retorno futuro após divergências de volume (§6).

    Divergência baixista: novo topo de ``lookback`` dias com volume abaixo da média -> esperaria-se
    fraqueza. Divergência altista: novo fundo com volume abaixo da média -> esperaria-se fundo.
    Retorna estatísticas de retorno futuro de ``horizon`` dias para cada caso e para o baseline.
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

    bearish = new_high & low_vol   # novo topo sem volume
    bullish = new_low & low_vol    # novo fundo sem volume

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


def rule80_diagnostics(trades: list) -> dict:
    """Diagnóstico da Regra dos 80%: dado o gatilho, com que frequência atinge o extremo oposto."""
    if not trades:
        return {"n": 0, "traverse_rate": np.nan, "win_rate": np.nan, "stop_rate": np.nan}
    n = len(trades)
    traverse = sum(1 for t in trades if t.exit_reason == "target")
    stops = sum(1 for t in trades if t.exit_reason == "stop")
    wins = sum(1 for t in trades if t.return_pct > 0)
    return {
        "n": n,
        "traverse_rate": traverse / n,   # comparar com a alegação de ~80%
        "stop_rate": stops / n,
        "win_rate": wins / n,
    }


def combine_portfolio_returns(
    sleeves: dict[str, pd.Series], *, weights: dict[str, float] | None = None
) -> pd.Series:
    """Combina retornos diários de vários sleeves em um portfólio (capital igualitário por padrão).

    Cada sleeve é a série de retornos diários (já escalada por risco) de um par instrumento×estratégia.
    O portfólio aloca peso fixo a cada sleeve e soma as contribuições diárias.
    """
    if not sleeves:
        return pd.Series(dtype=float)
    df = pd.DataFrame(sleeves).fillna(0.0)
    if weights is None:
        w = pd.Series(1.0 / df.shape[1], index=df.columns)
    else:
        w = pd.Series(weights).reindex(df.columns).fillna(0.0)
    return (df * w).sum(axis=1)

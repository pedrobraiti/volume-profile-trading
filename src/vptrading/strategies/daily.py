"""Estratégias diárias (swing) sobre o Composite Volume Profile.

Duas táticas objetivas do documento de referência (§5.1 e §7):

1. **VA Reversion (fade de extremos -> POC):** quando o preço fecha ACIMA da VAH ("caro demais")
   espera-se reversão à média -> vende com alvo no POC; abaixo da VAL ("barato demais") -> compra
   com alvo no POC. É a rotação clássica do dia em "D".

2. **Edge-to-Edge:** entra numa borda da Value Area e mira a borda OPOSTA, atravessando o interior
   do perfil. Alvo maior (VAH<->VAL), payoff teórico melhor, win rate menor.

Ambas aceitam um filtro de tendência (SMA longa): evita *fadear* contra um Trend Day — o "assassino"
da reversão. Stops são baseados em ATR para se adaptar à volatilidade do ativo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from vptrading.core.composite import rolling_composite_levels


@dataclass(frozen=True)
class DailyParams:
    """Parâmetros das estratégias diárias."""

    window: int = 60               # dias no composite profile
    value_area_pct: float = 0.70   # fração que define a Value Area
    n_bins: int = 80               # resolução do histograma
    stop_atr_mult: float = 1.5     # stop = entrada ± mult × ATR
    atr_period: int = 14
    trend_filter: bool = True      # se True, não fadeia contra a SMA longa
    trend_sma: int = 200
    allow_long: bool = True
    allow_short: bool = True


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _levels(df: pd.DataFrame, p: DailyParams, cache_key: str | None) -> pd.DataFrame:
    return rolling_composite_levels(
        df,
        window=p.window,
        n_bins=p.n_bins,
        value_area_pct=p.value_area_pct,
        cache_key=cache_key,
    )


def _trend_ok(close: pd.Series, p: DailyParams) -> tuple[pd.Series, pd.Series]:
    """Retorna (long_ok, short_ok) por dia, segundo o filtro de tendência.

    Sem filtro: ambos sempre liberados. Com filtro: só compra acima da SMA longa e só vende abaixo
    (não fadeia contra a tendência dominante).
    """
    if not p.trend_filter:
        true = pd.Series(True, index=close.index)
        return true, true
    sma = close.rolling(p.trend_sma, min_periods=p.trend_sma).mean()
    long_ok = close >= sma
    short_ok = close <= sma
    return long_ok.fillna(False), short_ok.fillna(False)


def va_reversion_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Sinais da tática de reversão ao POC (fade de extremos)."""
    lv = _levels(df, p, cache_key)
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    long_ok, short_ok = _trend_ok(close, p)

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    poc, vah, val = lv["poc"].to_numpy(), lv["vah"].to_numpy(), lv["val"].to_numpy()
    c = close.to_numpy()
    a = atr.to_numpy()
    lo, sh = long_ok.to_numpy(), short_ok.to_numpy()

    for i in range(n):
        if np.isnan(poc[i]) or np.isnan(a[i]):
            continue
        if p.allow_short and c[i] > vah[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = poc[i]
        elif p.allow_long and c[i] < val[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = poc[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)


def edge_to_edge_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Sinais da tática edge-to-edge (entra numa borda, mira a borda oposta da VA)."""
    lv = _levels(df, p, cache_key)
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    long_ok, short_ok = _trend_ok(close, p)

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)

    vah, val = lv["vah"].to_numpy(), lv["val"].to_numpy()
    c = close.to_numpy()
    a = atr.to_numpy()
    lo, sh = long_ok.to_numpy(), short_ok.to_numpy()

    for i in range(n):
        if np.isnan(vah[i]) or np.isnan(a[i]):
            continue
        if p.allow_long and c[i] <= val[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = vah[i]
        elif p.allow_short and c[i] >= vah[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = val[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)

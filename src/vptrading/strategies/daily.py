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
    target_atr_mult: float = 3.0   # alvo (usado no breakout) = entrada ± mult × ATR
    atr_period: int = 14
    trend_filter: bool = True      # se True, alinha a direção à SMA longa
    trend_sma: int = 200
    allow_long: bool = True
    allow_short: bool = True
    volume_mult: float = 0.0       # >0: exige volume do dia-sinal > mult × média (signal candle)
    volume_avg: int = 20
    max_holding_days: int = 15     # tempo máximo na posição antes de sair "por tempo"


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


def _volume_ok(df: pd.DataFrame, p: DailyParams) -> np.ndarray:
    """Máscara de confirmação por volume (signal candle): volume do dia > mult × média recente."""
    if p.volume_mult <= 0:
        return np.ones(len(df), dtype=bool)
    vol = df["Volume"]
    avg = vol.rolling(p.volume_avg, min_periods=p.volume_avg).mean()
    return (vol >= p.volume_mult * avg).fillna(False).to_numpy()


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
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(poc[i]) or np.isnan(a[i]) or not vok[i]:
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
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(vah[i]) or np.isnan(a[i]) or not vok[i]:
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


def va_breakout_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Sinais de BREAKOUT / atividade iniciante (opera A FAVOR do rompimento da Value Area).

    Contraponto ao fade: quando o preço rompe a VAH com a tendência a favor, compra apostando na
    continuação (aceitação fora do valor = início de tendência, §2/§5.4). Alvo por múltiplo de ATR,
    stop no outro lado. Aqui o filtro de tendência alinha a direção do rompimento à SMA longa.
    """
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
    vok = _volume_ok(df, p)

    for i in range(n):
        if np.isnan(vah[i]) or np.isnan(a[i]) or not vok[i]:
            continue
        if p.allow_long and c[i] > vah[i] and lo[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = c[i] + p.target_atr_mult * a[i]
        elif p.allow_short and c[i] < val[i] and sh[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = c[i] - p.target_atr_mult * a[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)


def volume_exhaustion_signals(
    df: pd.DataFrame, p: DailyParams, *, cache_key: str | None = None
) -> pd.DataFrame:
    """Sinais de exaustão de volume / "sem oferta" (§6) — não depende do Volume Profile.

    Compra quando o preço faz uma nova MÍNIMA de ``window`` dias com volume ABAIXO da média
    (vendedores se esgotando = possível fundo). Vende a descoberto no espelho: nova MÁXIMA com
    volume baixo (compradores sem força). Alvo e stop por múltiplos de ATR. ``volume_mult`` define
    o teto de volume (fração da média); se 0, usa 1.0 (abaixo da média).
    """
    atr = _atr(df, p.atr_period)
    close = df["Close"]
    vol = df["Volume"]
    vol_avg = vol.rolling(p.volume_avg, min_periods=p.volume_avg).mean()
    thresh_mult = p.volume_mult if p.volume_mult > 0 else 1.0
    low_vol = (vol <= thresh_mult * vol_avg).to_numpy()

    roll_low = close.rolling(p.window, min_periods=p.window).min().to_numpy()
    roll_high = close.rolling(p.window, min_periods=p.window).max().to_numpy()

    n = len(df)
    signal = np.zeros(n)
    stop = np.full(n, np.nan)
    target = np.full(n, np.nan)
    c = close.to_numpy()
    a = atr.to_numpy()

    for i in range(n):
        if np.isnan(roll_low[i]) or np.isnan(a[i]) or not low_vol[i]:
            continue
        if p.allow_long and c[i] <= roll_low[i]:
            signal[i] = 1
            stop[i] = c[i] - p.stop_atr_mult * a[i]
            target[i] = c[i] + p.target_atr_mult * a[i]
        elif p.allow_short and c[i] >= roll_high[i]:
            signal[i] = -1
            stop[i] = c[i] + p.stop_atr_mult * a[i]
            target[i] = c[i] - p.target_atr_mult * a[i]

    return pd.DataFrame({"signal": signal, "stop": stop, "target": target}, index=df.index)

"""Classificação de day-types do Market Profile (D / P / b / Trend).

Baseado em ``volume-profile-estrategia.md`` §5. Aproximamos os tipos a partir de OHLCV diário:
onde o volume/centro de massa do dia se concentra e quão "esticado" é o range vs. o corpo.
Serve de filtro de regime: as táticas de *fade* (D, P, b) só valem em mercado balanceado; o Trend
Day é o "assassino" da reversão e deve ser evitado.
"""

from __future__ import annotations

from enum import Enum


class DayType(str, Enum):
    NORMAL_D = "D"      # balanceado, POC no centro -> fade nos extremos
    BULLISH_P = "P"     # valor no topo, cauda fina embaixo -> viés de alta
    BEARISH_b = "b"     # valor no fundo, cauda fina em cima -> viés de baixa
    TREND = "Trend"     # range largo, fecha no extremo -> não brigar contra


def classify_day_type(
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    trend_close_pct: float = 0.85,
    balanced_body_pct: float = 0.35,
) -> DayType:
    """Classifica o desenho do dia a partir do OHLC.

    - Trend: fecha muito perto de um extremo do range (>= trend_close_pct ou <= 1-trend_close_pct).
    - P (bullish): corpo concentrado na metade superior do range.
    - b (bearish): corpo concentrado na metade inferior do range.
    - D (normal): corpo pequeno e centrado.
    """
    rng = high - low
    if rng <= 0:
        return DayType.NORMAL_D

    close_pos = (close - low) / rng  # 0 = fechou no fundo, 1 = fechou no topo
    body_mid = ((open_ + close) / 2 - low) / rng
    body_size = abs(close - open_) / rng

    if close_pos >= trend_close_pct:
        return DayType.TREND if close_pos >= 0.92 else DayType.BULLISH_P
    if close_pos <= (1 - trend_close_pct):
        return DayType.TREND if close_pos <= 0.08 else DayType.BEARISH_b
    if body_size <= balanced_body_pct and 0.35 <= body_mid <= 0.65:
        return DayType.NORMAL_D
    if body_mid > 0.6:
        return DayType.BULLISH_P
    if body_mid < 0.4:
        return DayType.BEARISH_b
    return DayType.NORMAL_D

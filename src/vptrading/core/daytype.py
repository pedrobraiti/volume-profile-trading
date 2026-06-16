"""Market Profile day-type classification (D / P / b / Trend).

Based on ``volume-profile-strategy.md`` §5. We approximate the types from daily OHLCV: where the
day's volume/center of mass concentrates and how "stretched" the range is versus the body.
It serves as a regime filter: the *fade* tactics (D, P, b) only hold in a balanced market; the
Trend Day is the "killer" of reversion and should be avoided.
"""

from __future__ import annotations

from enum import Enum


class DayType(str, Enum):
    NORMAL_D = "D"      # balanced, POC at center -> fade the extremes
    BULLISH_P = "P"     # value at the top, thin tail below -> bullish bias
    BEARISH_b = "b"     # value at the bottom, thin tail above -> bearish bias
    TREND = "Trend"     # wide range, closes at an extreme -> don't fight it


def classify_day_type(
    open_: float,
    high: float,
    low: float,
    close: float,
    *,
    trend_close_pct: float = 0.85,
    balanced_body_pct: float = 0.35,
) -> DayType:
    """Classify the day's shape from the OHLC.

    - Trend: closes very near an extreme of the range (>= trend_close_pct or <= 1-trend_close_pct).
    - P (bullish): body concentrated in the upper half of the range.
    - b (bearish): body concentrated in the lower half of the range.
    - D (normal): small, centered body.
    """
    rng = high - low
    if rng <= 0:
        return DayType.NORMAL_D

    close_pos = (close - low) / rng  # 0 = closed at the bottom, 1 = closed at the top
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

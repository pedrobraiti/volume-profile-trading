"""Download and local cache of OHLCV data via Yahoo Finance.

Yahoo provides long daily history (decades) but short intraday (~60 days for 30 min).
This layer downloads once, saves to Parquet under ``data/cache/`` and reuses it on future
runs so as not to depend on the network or Yahoo's rate limit on every run.
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass(frozen=True)
class Instrument:
    """Metadata for a tradable instrument."""

    ticker: str
    name: str
    market: str  # "US" or "BR"
    currency: str


INSTRUMENTS: dict[str, Instrument] = {
    "SPY": Instrument("SPY", "SPDR S&P 500 ETF", "US", "USD"),
    "QQQ": Instrument("QQQ", "Invesco Nasdaq-100 ETF", "US", "USD"),
    "PETR4.SA": Instrument("PETR4.SA", "Petrobras PN", "BR", "BRL"),
    "VALE3.SA": Instrument("VALE3.SA", "Vale ON", "BR", "BRL"),
    "BOVA11.SA": Instrument("BOVA11.SA", "iShares Ibovespa ETF", "BR", "BRL"),
}


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns MultiIndex columns (Price, Ticker) when downloading 1 ticker. Flatten them."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure OHLCV columns, sort by date and drop invalid rows."""
    df = _flatten_columns(df)
    keep = [c for c in OHLCV_COLUMNS if c in df.columns]
    df = df[keep].copy()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df = df[df["Volume"] > 0]  # discard sessions with no trading (holidays/halts)
    return df


def _download(ticker: str, *, period: str, interval: str, retries: int = 3) -> pd.DataFrame:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is not None and len(df) > 0:
                return _normalize(df)
        except Exception as exc:  # noqa: BLE001 — unstable network; we retry
            last_err = exc
        time.sleep(1.5 * (attempt + 1))
    if last_err is not None:
        raise RuntimeError(f"Failed to download {ticker} ({interval}): {last_err}")
    raise RuntimeError(f"Empty download for {ticker} ({interval}).")


def load_daily(ticker: str, *, refresh: bool = False) -> pd.DataFrame:
    """Load the ticker's maximum daily history, with Parquet caching."""
    cache = CACHE_DIR / f"{ticker.replace('.', '_')}_1d.parquet"
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)
    df = _download(ticker, period="max", interval="1d")
    df.to_parquet(cache)
    return df


def load_intraday(ticker: str, *, interval: str = "30m", refresh: bool = False) -> pd.DataFrame:
    """Load the ticker's available (short) intraday history, with caching.

    Yahoo limits: ~60 days for 30m; ~730 days for 1h.
    """
    period = "60d" if interval in {"30m", "15m", "5m"} else "730d"
    cache = CACHE_DIR / f"{ticker.replace('.', '_')}_{interval}.parquet"
    if cache.exists() and not refresh:
        return pd.read_parquet(cache)
    df = _download(ticker, period=period, interval=interval)
    df.to_parquet(cache)
    return df

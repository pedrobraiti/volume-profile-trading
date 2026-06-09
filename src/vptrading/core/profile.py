"""Construção de um Volume Profile e cálculo de POC, Value Area e nós (HVN/LVN).

O perfil é um histograma de *volume por preço*. Como não temos dados tick-a-tick, o volume de
cada barra é distribuído **uniformemente** ao longo do seu range [Low, High] — aproximação padrão
usada por ferramentas de Volume Profile quando só há OHLCV. A Value Area segue o algoritmo de
expansão clássico de Steidlmayer (descrito em ``volume-profile-estrategia.md`` §4.2): parte do POC
e cresce sempre para o lado (par de linhas) de maior volume até cobrir ~70% do total.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

DEFAULT_VALUE_AREA_PCT = 0.70


@dataclass(frozen=True)
class ProfileResult:
    """Resultado de um Volume Profile."""

    poc: float
    vah: float
    val: float
    value_area_pct: float
    total_volume: float
    bin_centers: np.ndarray
    bin_volumes: np.ndarray
    hvn_prices: np.ndarray
    lvn_prices: np.ndarray

    @property
    def value_area_width(self) -> float:
        return self.vah - self.val


def _distribute_volume(
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    edges: np.ndarray,
) -> np.ndarray:
    """Distribui o volume de cada barra uniformemente sobre [Low, High] nos bins definidos.

    Vetorizado por broadcasting (barras × bins). ``edges`` tem comprimento n_bins+1.
    """
    bin_lo = edges[:-1]
    bin_hi = edges[1:]
    spans = np.maximum(highs - lows, 1e-12)  # evita divisão por zero em barras de range nulo
    density = volumes / spans  # volume por unidade de preço, por barra

    # Sobreposição entre [low, high] de cada barra e cada bin -> matriz (n_bars, n_bins)
    lo = np.maximum(lows[:, None], bin_lo[None, :])
    hi = np.minimum(highs[:, None], bin_hi[None, :])
    overlap = np.clip(hi - lo, 0.0, None)
    allocation = overlap * density[:, None]
    return allocation.sum(axis=0)


def build_volume_profile(
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
    *,
    n_bins: int = 100,
    value_area_pct: float = DEFAULT_VALUE_AREA_PCT,
    hvn_lvn: bool = True,
) -> ProfileResult:
    """Constrói o Volume Profile e calcula POC, VAH, VAL e nós de volume.

    Args:
        highs, lows, volumes: arrays alinhados das barras que compõem o perfil.
        n_bins: número de faixas de preço (resolução do histograma).
        value_area_pct: fração do volume total que define a Value Area (0.70 = padrão).
        hvn_lvn: se True, detecta High/Low Volume Nodes (picos e vales do histograma).
    """
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    volumes = np.asarray(volumes, dtype=float)

    price_min = float(lows.min())
    price_max = float(highs.max())
    if price_max <= price_min:
        price_max = price_min + 1e-6

    edges = np.linspace(price_min, price_max, n_bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    bin_volumes = _distribute_volume(highs, lows, volumes, edges)
    total_volume = float(bin_volumes.sum())

    poc_idx = int(np.argmax(bin_volumes))
    poc = float(centers[poc_idx])

    val_idx, vah_idx = _value_area_indices(bin_volumes, poc_idx, value_area_pct)
    val = float(centers[val_idx])
    vah = float(centers[vah_idx])

    if hvn_lvn:
        hvn_prices, lvn_prices = _detect_nodes(centers, bin_volumes)
    else:
        hvn_prices = np.array([])
        lvn_prices = np.array([])

    return ProfileResult(
        poc=poc,
        vah=vah,
        val=val,
        value_area_pct=value_area_pct,
        total_volume=total_volume,
        bin_centers=centers,
        bin_volumes=bin_volumes,
        hvn_prices=hvn_prices,
        lvn_prices=lvn_prices,
    )


def _value_area_indices(
    bin_volumes: np.ndarray, poc_idx: int, value_area_pct: float
) -> tuple[int, int]:
    """Expansão da Value Area a partir do POC (algoritmo de duas linhas de Steidlmayer).

    A cada passo compara o volume combinado das DUAS linhas acima do topo atual com o das DUAS
    abaixo do fundo atual, e adiciona o lado de maior volume. Repete até atingir o alvo (~70%).
    """
    n = len(bin_volumes)
    target = value_area_pct * bin_volumes.sum()

    lower = poc_idx  # índice mais baixo incluído na VA
    upper = poc_idx  # índice mais alto incluído na VA
    acc = bin_volumes[poc_idx]

    while acc < target and (lower > 0 or upper < n - 1):
        # Soma das duas linhas acima do topo atual.
        up1 = bin_volumes[upper + 1] if upper + 1 < n else -1.0
        up2 = bin_volumes[upper + 2] if upper + 2 < n else 0.0
        up_pair = up1 + up2 if up1 >= 0 else -np.inf

        # Soma das duas linhas abaixo do fundo atual.
        dn1 = bin_volumes[lower - 1] if lower - 1 >= 0 else -1.0
        dn2 = bin_volumes[lower - 2] if lower - 2 >= 0 else 0.0
        dn_pair = dn1 + dn2 if dn1 >= 0 else -np.inf

        if up_pair == -np.inf and dn_pair == -np.inf:
            break

        if up_pair >= dn_pair:
            upper = min(upper + 1, n - 1)
            acc += bin_volumes[upper]
            if acc < target and upper + 1 < n:
                upper += 1
                acc += bin_volumes[upper]
        else:
            lower = max(lower - 1, 0)
            acc += bin_volumes[lower]
            if acc < target and lower - 1 >= 0:
                lower -= 1
                acc += bin_volumes[lower]

    return lower, upper


def _detect_nodes(
    centers: np.ndarray, bin_volumes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Detecta HVN (picos) e LVN (vales) no histograma de volume por preço."""
    if len(bin_volumes) < 3 or bin_volumes.max() == 0:
        return np.array([]), np.array([])

    prominence = 0.10 * bin_volumes.max()
    hvn_idx, _ = find_peaks(bin_volumes, prominence=prominence)
    lvn_idx, _ = find_peaks(bin_volumes.max() - bin_volumes, prominence=prominence)
    return centers[hvn_idx], centers[lvn_idx]

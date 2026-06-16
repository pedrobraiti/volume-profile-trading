"""Tests for the Volume Profile core: volume distribution, POC and Value Area (70%)."""

import numpy as np

from vptrading.core.profile import build_volume_profile, _value_area_indices


def test_poc_at_highest_volume_price():
    # Three bars concentrating volume around 100.
    highs = np.array([101.0, 100.5, 100.2])
    lows = np.array([99.0, 99.5, 99.8])
    volumes = np.array([100.0, 500.0, 100.0])
    prof = build_volume_profile(highs, lows, volumes, n_bins=50)
    # The POC should fall near 100 (where the highest-volume bar concentrates).
    assert 99.5 <= prof.poc <= 100.5


def test_value_area_contains_poc_and_is_ordered():
    rng = np.random.default_rng(42)
    base = rng.normal(100, 1.0, 2000)
    highs = base + 0.25
    lows = base - 0.25
    volumes = np.ones_like(base)
    prof = build_volume_profile(highs, lows, volumes, n_bins=100, value_area_pct=0.70)
    assert prof.val <= prof.poc <= prof.vah


def test_value_area_captures_roughly_target_volume():
    # Gaussian histogram: the 70% VA should capture ~70% of the volume (with binning tolerance).
    bins = np.exp(-0.5 * ((np.arange(101) - 50) / 12.0) ** 2)
    lower, upper = _value_area_indices(bins, poc_idx=50, value_area_pct=0.70)
    captured = bins[lower : upper + 1].sum() / bins.sum()
    assert 0.66 <= captured <= 0.80
    assert lower <= 50 <= upper


def test_wider_value_area_pct_widens_area():
    bins = np.exp(-0.5 * ((np.arange(101) - 50) / 12.0) ** 2)
    l70, u70 = _value_area_indices(bins, 50, 0.70)
    l90, u90 = _value_area_indices(bins, 50, 0.90)
    assert (u90 - l90) >= (u70 - l70)

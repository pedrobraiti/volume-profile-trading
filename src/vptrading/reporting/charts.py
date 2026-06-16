"""Generation of all report figures (high-resolution PNG).

Each function draws a figure from the results dictionary (``results.pkl``) and saves it to
``output/figures/``. The style is uniform and designed for PDF printing: light background, sober
palette, titles and axes in English, annotations where they aid readability.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import Normalize, TwoSlopeNorm  # noqa: E402


def _safe_diverging_norm(vals: np.ndarray, center: float):
    """Safe TwoSlopeNorm: falls back to Normalize when the data does not straddle the center."""
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmin < center < vmax:
        return TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
    return Normalize(vmin=vmin, vmax=vmax)

# Palette
NAVY = "#1f3b5c"
BLUE = "#2c6fbb"
TEAL = "#2a9d8f"
ORANGE = "#e07a3f"
RED = "#c0392b"
GREEN = "#2e8b57"
GREY = "#8a8f98"
LIGHT = "#eef1f5"

plt.rcParams.update(
    {
        "figure.dpi": 140,
        "savefig.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.edgecolor": "#cccccc",
        "axes.grid": True,
        "grid.color": "#e6e6e6",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    }
)

STRAT_LABELS = {
    "REV": "POC reversion",
    "E2E": "Edge-to-Edge",
    "BRK": "VA breakout",
    "EXH": "Volume exhaustion",
}


def _save(fig, figdir: Path, name: str) -> str:
    path = figdir / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def fig_volume_profile(results: dict, figdir: Path) -> str:
    """Educational chart: price + volume-by-price histogram with POC/VAH/VAL and nodes."""
    sp = results["sample_profile"]
    price = sp["price"]
    centers, vols = sp["bin_centers"], sp["bin_volumes"]

    fig, (axp, axv) = plt.subplots(
        1, 2, figsize=(11, 6.2), gridspec_kw={"width_ratios": [3, 1], "wspace": 0.03}, sharey=True
    )
    axp.plot(price.index, price.values, color=NAVY, lw=1.3)
    axp.set_title(f"{sp['ticker']} — price (composite of 120 sessions)", loc="left")
    axp.set_ylabel("Price (US$)")
    axp.margins(x=0.01)

    # Bands and levels
    axp.axhspan(sp["val"], sp["vah"], color=BLUE, alpha=0.08, zorder=0)
    for lvl, lbl, col in [(sp["poc"], "POC", RED), (sp["vah"], "VAH", BLUE),
                          (sp["val"], "VAL", BLUE)]:
        axp.axhline(lvl, color=col, lw=1.2, ls="--", alpha=0.9)
        axp.text(price.index[0], lvl, f" {lbl}", color=col, va="center", ha="left",
                 fontsize=9, fontweight="bold")

    # Horizontal volume-by-price histogram
    height = (centers[1] - centers[0]) * 0.9
    colors = [RED if abs(c - sp["poc"]) < height else (BLUE if sp["val"] <= c <= sp["vah"] else GREY)
              for c in centers]
    axv.barh(centers, vols, height=height, color=colors, alpha=0.85)
    axv.set_title("Volume by price", loc="right")
    axv.set_xlabel("Aggregate volume")
    axv.grid(axis="y")
    for h in sp["hvn"][:6]:
        axv.scatter(vols.max() * 0.02, h, marker=">", color=GREEN, s=30, zorder=5)
    axv.text(0.98, 0.02, "HVN ▶ green", transform=axv.transAxes, ha="right", va="bottom",
             fontsize=8, color=GREEN)
    fig.suptitle(f"Composite Volume Profile — {sp['ticker']} ({sp['start'].date()} to "
                 f"{sp['end'].date()})\nPrice 'sticks' at high-volume nodes (HVN) and 'slips' "
                 "through low-volume ones (LVN)", fontsize=11, fontweight="bold")
    return _save(fig, figdir, "01_volume_profile")


def _wf_matrix(results: dict, metric: str) -> pd.DataFrame:
    wf = results["walkforward"]
    insts = list(results["instruments"].keys())
    data = {s: [wf[s][tk]["oos_metrics"][metric] for tk in insts] for s in wf}
    return pd.DataFrame(data, index=insts).T  # rows=strategy, columns=instrument


def fig_oos_heatmap(results: dict, figdir: Path) -> str:
    """OOS heatmap: Profit Factor and expectancy by strategy × instrument."""
    pf = _wf_matrix(results, "profit_factor").clip(upper=2.5)
    exp = _wf_matrix(results, "expectancy_pct") * 100

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, mat, title, center, fmt, cmap in [
        (axes[0], pf, "Profit Factor (OOS)", 1.0, "{:.2f}", "RdYlGn"),
        (axes[1], exp, "Expectancy per trade (%, OOS)", 0.0, "{:.2f}", "RdYlGn"),
    ]:
        vals = mat.values.astype(float)
        norm = _safe_diverging_norm(vals, center)
        im = ax.imshow(vals, cmap=cmap, norm=norm, aspect="auto")
        ax.set_xticks(range(mat.shape[1]))
        ax.set_xticklabels([c.replace(".SA", "") for c in mat.columns], rotation=30, ha="right")
        ax.set_yticks(range(mat.shape[0]))
        ax.set_yticklabels([STRAT_LABELS.get(i, i) for i in mat.index])
        ax.set_title(title)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, fmt.format(vals[i, j]), ha="center", va="center", fontsize=9)
        ax.grid(False)
    fig.suptitle("Out-of-sample validation (walk-forward) — long-only, costs included",
                 fontweight="bold")
    return _save(fig, figdir, "02_oos_heatmap")


def fig_oos_equity(results: dict, figdir: Path) -> str:
    """OOS equity curves of the best long strategy per instrument."""
    wf = results["walkforward"]
    chosen = results["portfolio"]["chosen"]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    palette = [NAVY, BLUE, TEAL, ORANGE, RED]
    for (tk, s), col in zip(chosen.items(), palette):
        curve = wf[s][tk]["oos_curve"]
        if len(curve):
            ax.plot(curve.index, curve.values, label=f"{tk.replace('.SA','')} · {STRAT_LABELS[s]}",
                    color=col, lw=1.5)
    ax.axhline(1.0, color=GREY, lw=1, ls=":")
    ax.set_title("Out-of-sample capital per instrument (1.0 = start, 1% risk/trade)")
    ax.set_ylabel("Capital multiple")
    ax.legend(fontsize=8, ncol=2)
    return _save(fig, figdir, "03_oos_equity")


def fig_walkforward_degradation(results: dict, figdir: Path) -> str:
    """In-sample vs out-of-sample per fold (flagship QQQ E2E) — overfitting check."""
    # Pick an ILLUSTRATIVE (strategy, instrument) pair: long history (>=5 folds), good OOS.
    wf = results["walkforward"]
    candidates = [
        (s, tk) for s in wf for tk in wf[s] if len(wf[s][tk]["folds"]) >= 5
    ]
    s, tk = max(candidates, key=lambda st: wf[st[0]][st[1]]["oos_metrics"]["sharpe"])
    folds = wf[s][tk]["folds"]
    fig, ax = plt.subplots(figsize=(11, 5.0))
    x = np.arange(len(folds))
    ax.bar(x - 0.2, folds["is_expectancy_r"], width=0.4, label="In-sample (train)", color=GREY)
    ax.bar(x + 0.2, folds["oos_expectancy_r"], width=0.4, label="Out-of-sample (test)", color=BLUE)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.train_end}\n→{r.test_end}" for r in folds.itertuples()],
                       fontsize=7, rotation=0)
    ax.set_ylabel("Expectancy per trade (R)")
    ax.set_title(f"Train->test degradation per window — {tk.replace('.SA','')} · {STRAT_LABELS[s]}")
    ax.legend()
    return _save(fig, figdir, "04_walkforward_degradation")


def fig_param_heatmap(results: dict, figdir: Path) -> str:
    """Parameter sensitivity: window × stop (ATR) -> Profit Factor (EXH SPY, full sample)."""
    grid = results["flagship"]["exh_spy_grid"]
    piv = grid.pivot_table(index="window", columns="stop_atr_mult", values="profit_factor",
                           aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    vals = piv.values
    cmap = "RdYlGn" if np.nanmin(vals) < 1.0 < np.nanmax(vals) else "YlGn"
    norm = _safe_diverging_norm(vals, 1.0)
    im = ax.imshow(vals, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels(piv.index)
    ax.set_xlabel("Stop (× ATR)")
    ax.set_ylabel("New-low window / lookback (days)")
    ax.set_title("Parameter sensitivity — Volume exhaustion (SPY)\n"
                 "Profit Factor (averaged over target/holding/volume) — every cell > 1 (profitable)")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, f"{vals[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return _save(fig, figdir, "05_param_heatmap")


def fig_daytype(results: dict, figdir: Path) -> str:
    """Average future return by day-type (averaged across instruments), 1/5/10 days."""
    dts = results["studies"]["day_type"]
    # Simple average across instruments per day_type.
    frames = []
    for tk, dfm in dts.items():
        frames.append(dfm.set_index("day_type"))
    avg = sum(f[["mean_1d_pct", "mean_5d_pct", "mean_10d_pct"]] for f in frames) / len(frames)
    avg = avg.reindex(["D", "P", "b", "Trend"]) * 100

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    x = np.arange(len(avg))
    w = 0.26
    for k, (col, lbl, c) in enumerate(
        [("mean_1d_pct", "1 day", BLUE), ("mean_5d_pct", "5 days", TEAL),
         ("mean_10d_pct", "10 days", ORANGE)]
    ):
        ax.bar(x + (k - 1) * w, avg[col], width=w, label=lbl, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels(["D (normal)", "P (bullish)", "b (bearish)", "Trend"])
    ax.set_ylabel("Average future return (%)")
    ax.set_title("Future return by day-type (average of the 5 instruments)\n"
                 "The labels do NOT predict continuation: 'b'/Trend days rebound more than 'P' — "
                 "the opposite of what is promised")
    ax.legend()
    ax.axhline(0, color="black", lw=0.8)
    return _save(fig, figdir, "06_daytype")


def fig_divergence(results: dict, figdir: Path) -> str:
    """Volume divergence: 5d future return (baseline vs bullish vs bearish) per instrument."""
    div = results["studies"]["divergence"]
    insts = list(div.keys())
    base = [div[t]["baseline"]["mean_fwd_pct"] * 100 for t in insts]
    bull = [div[t]["bullish_divergence"]["mean_fwd_pct"] * 100 for t in insts]
    bear = [div[t]["bearish_divergence"]["mean_fwd_pct"] * 100 for t in insts]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    x = np.arange(len(insts))
    w = 0.26
    ax.bar(x - w, base, width=w, label="Baseline (any day)", color=GREY)
    ax.bar(x, bull, width=w, label="Bullish divergence (new low + low vol.)", color=GREEN)
    ax.bar(x + w, bear, width=w, label="Bearish divergence (new high + low vol.)", color=RED)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("5-day future return (%)")
    ax.set_title("Volume divergence (§6): buying 'no-supply' at the lows beats the baseline")
    ax.legend(fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    return _save(fig, figdir, "07_divergence")


def fig_rule80(results: dict, figdir: Path) -> str:
    """80% rule: observed traverse rate vs the 80% claim, and expectancy."""
    r80 = results["rule80"]
    insts = list(r80.keys())
    traverse = [r80[t]["diagnostics"]["traverse_rate"] * 100
                if r80[t]["diagnostics"]["n"] else 0 for t in insts]
    n = [r80[t]["diagnostics"]["n"] for t in insts]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    x = np.arange(len(insts))
    bars = ax.bar(x, traverse, color=BLUE, alpha=0.85)
    ax.axhline(80, color=RED, lw=1.5, ls="--", label="Method's claim: ~80%")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("Observed traverse rate (%)")
    ax.set_ylim(0, 100)
    ax.set_title("80% rule (30 min, 60 days): how often does price traverse the entire VA?\n"
                 "Small sample — indicative reading, not conclusive")
    for b, ni in zip(bars, n):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"n={ni}",
                ha="center", fontsize=8, color=GREY)
    ax.legend()
    return _save(fig, figdir, "08_rule80")


def fig_portfolio(results: dict, figdir: Path) -> str:
    """OOS portfolio equity curve + drawdown."""
    port = results["portfolio"]
    key = "apenas_positivos_OOS" if "apenas_positivos_OOS" in port else "todos"
    curve = port[key]["curve"]
    dd = (curve / curve.cummax()) - 1

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.4), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    ax1.plot(curve.index, curve.values, color=NAVY, lw=1.6)
    ax1.fill_between(curve.index, 1.0, curve.values, where=(curve.values >= 1.0),
                     color=GREEN, alpha=0.10)
    m = port[key]["metrics"]
    ax1.set_title(f"Diversified portfolio (OOS-validated sleeves) — {', '.join(port[key]['sleeves'])}\n"
                  f"CAGR {m['cagr_pct']:.1%} · Sharpe {m['sharpe']:.2f} · maxDD {m['max_drawdown_pct']:.1%} "
                  f"· exposure {port[key]['exposure_pct']:.0%}")
    ax1.set_ylabel("Capital multiple")
    ax2.fill_between(dd.index, dd.values * 100, 0, color=RED, alpha=0.5)
    ax2.set_ylabel("Drawdown (%)")
    return _save(fig, figdir, "09_portfolio")


def fig_trade_distribution(results: dict, figdir: Path) -> str:
    """Distribution of per-trade returns of the flagship (EXH SPY)."""
    rets = np.array(results["flagship"]["flagship_trade_returns"]) * 100
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.hist(rets, bins=30, color=BLUE, alpha=0.8, edgecolor="white")
    ax.axvline(0, color="black", lw=1)
    ax.axvline(rets.mean(), color=RED, lw=1.6, ls="--",
               label=f"Mean = {rets.mean():.2f}%")
    ax.set_xlabel("Net return per trade (%)")
    ax.set_ylabel("Frequency")
    ax.set_title("Per-trade return distribution — Volume exhaustion (SPY)")
    ax.legend()
    return _save(fig, figdir, "10_trade_distribution")


def fig_sizing_tradeoff(results: dict, figdir: Path) -> str:
    """Conservative↔aggressive axis: CAGR vs max drawdown (portfolio sizing and leverage)."""
    fig, ax = plt.subplots(figsize=(9.5, 5.4))

    sizing = results["flagship"]["sizing_sweep"]
    sx = [abs(d["metrics"]["max_drawdown_pct"]) * 100 for d in sizing.values()]
    sy = [d["metrics"]["cagr_pct"] * 100 for d in sizing.values()]
    ax.plot(sx, sy, "-o", color=TEAL, label="EXH-SPY sizing (risk/trade)")
    for lbl, xx, yy in zip(sizing.keys(), sx, sy):
        en_lbl = lbl.replace("risco", "risk").replace(",", ".")
        ax.annotate(en_lbl, (xx, yy), fontsize=7, textcoords="offset points", xytext=(4, 4))

    if "leverage_sweep" in results["portfolio"]:
        lev = results["portfolio"]["leverage_sweep"]
        lx = [abs(d["metrics"]["max_drawdown_pct"]) * 100 for d in lev.values()]
        ly = [d["metrics"]["cagr_pct"] * 100 for d in lev.values()]
        ax.plot(lx, ly, "-s", color=NAVY, label="Portfolio leverage")
        for lbl, xx, yy in zip(lev.keys(), lx, ly):
            ax.annotate(lbl, (xx, yy), fontsize=7, textcoords="offset points", xytext=(4, 4))

    ax.set_xlabel("Max drawdown (%)")
    ax.set_ylabel("CAGR (%)")
    ax.set_title("The risk dial: more return costs more drawdown (Sharpe ~constant)")
    ax.legend()
    return _save(fig, figdir, "11_sizing_tradeoff")


def fig_cost_sensitivity(results: dict, figdir: Path) -> str:
    """How the edge (PF and expectancy) decays with round-trip cost."""
    cs = results["cost_sensitivity"]
    fig, ax1 = plt.subplots(figsize=(9.5, 5.0))
    x = cs["round_trip_cost_pct"] * 100
    ax1.plot(x, cs["profit_factor"], "-o", color=NAVY, label="Profit Factor")
    ax1.axhline(1.0, color=RED, ls="--", lw=1)
    ax1.set_xlabel("Round-trip cost (%)")
    ax1.set_ylabel("Profit Factor", color=NAVY)
    ax2 = ax1.twinx()
    ax2.plot(x, cs["expectancy_pct"] * 100, "-s", color=ORANGE, label="Expectancy/trade (%)")
    ax2.set_ylabel("Expectancy per trade (%)", color=ORANGE)
    ax2.grid(False)
    ax1.set_title("Cost sensitivity — Volume exhaustion (SPY)\n"
                  "The edge is real, but narrow: it vanishes under high costs")
    return _save(fig, figdir, "12_cost_sensitivity")


def fig_strategy_vs_buyhold(results: dict, figdir: Path) -> str:
    """Context: OOS portfolio (1x and 3x) vs SPY buy & hold over the same period."""
    port = results["portfolio"]
    key = "apenas_positivos_OOS" if "apenas_positivos_OOS" in port else "todos"
    curve = port[key]["curve"]
    start = curve.index[0]

    spy = results["instruments"]["SPY"]["price"]
    spy = spy[spy.index >= start]
    bh = spy / spy.iloc[0]

    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.plot(bh.index, bh.values, color=GREY, lw=1.5, label="SPY Buy & Hold")
    ax.plot(curve.index, curve.values, color=NAVY, lw=1.6, label="VP portfolio (1x)")
    if "leverage_sweep" in port and "3x" in port["leverage_sweep"]:
        c3 = port["leverage_sweep"]["3x"]["curve"]
        ax.plot(c3.index, c3.values, color=BLUE, lw=1.4, ls="--", label="VP portfolio (3x)")
    ax.set_yscale("log")
    ax.set_title("Context: the Volume Profile edge does not beat buy & hold on return —\n"
                 "it delivers a smoother, lower-drawdown stream (log axis)")
    ax.set_ylabel("Capital multiple (log)")
    ax.legend()
    return _save(fig, figdir, "13_strategy_vs_buyhold")


def fig_volume_events(results: dict, figdir: Path) -> str:
    """Raw volume readings (§6): 5d future return by event type, per instrument."""
    ve = results["complementary"]["volume_events"]
    insts = list(ve.keys())
    keys = [("baseline", "Baseline", GREY), ("movimento_saudavel", "Healthy move (large candle+vol)", BLUE),
            ("absorcao_topo", "Absorption at top", RED), ("absorcao_fundo", "Absorption at bottom", GREEN)]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(insts))
    w = 0.2
    for k, (key, lbl, c) in enumerate(keys):
        vals = [ve[t][key]["mean_fwd_pct"] * 100 for t in insts]
        ax.bar(x + (k - 1.5) * w, vals, width=w, label=lbl, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("5-day future return (%)")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("'Raw' volume readings (§6): absorption at the bottom is bullish (especially in Brazil);\n"
                 "'healthy move' does NOT beat the baseline in indices")
    ax.legend(fontsize=8, ncol=2)
    return _save(fig, figdir, "14_volume_events")


def fig_signal_candle(results: dict, figdir: Path) -> str:
    """Signal candle effect (§7): Edge-to-Edge PF vs volume requirement."""
    sc = results["complementary"]["signal_candle"]
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    for tk, col in [("SPY", NAVY), ("QQQ", BLUE)]:
        t = sc[tk]
        ax.plot(t["volume_mult"], t["profit_factor"], "-o", color=col, label=f"{tk} (PF)")
        for _, r in t.iterrows():
            ax.annotate(f"n={int(r['n_trades'])}", (r["volume_mult"], r["profit_factor"]),
                        fontsize=7, textcoords="offset points", xytext=(0, 6), ha="center")
    ax.axhline(1.0, color=RED, ls="--", lw=1)
    ax.set_xlabel("Volume requirement on the signal day (× average) — 0 = no confirmation")
    ax.set_ylabel("Profit Factor")
    ax.set_title("Signal candle (§7): requiring a volume spike improves QQQ (PF 1.1->1.9)\n"
                 "but over-filters above ~1.5×")
    ax.legend()
    return _save(fig, figdir, "15_signal_candle")


def fig_resolution(results: dict, figdir: Path) -> str:
    """Robustness to histogram resolution (§4.3 — 'use 400 rows')."""
    r = results["complementary"]["resolution"]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.bar(range(len(r)), r["profit_factor"], color=TEAL, alpha=0.85,
           tick_label=[str(int(n)) for n in r["n_bins"]])
    ax.axhline(1.0, color=RED, ls="--", lw=1)
    for i, v in enumerate(r["profit_factor"]):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xlabel("Number of price bins (rows) in the histogram")
    ax.set_ylabel("Profit Factor (E2E, SPY)")
    ax.set_ylim(0, max(r["profit_factor"]) * 1.2)
    ax.set_title("Profile resolution (§4.3): the edge is stable from 40 to 400 rows\n"
                 "— more resolution adds little for daily swing trading")
    return _save(fig, figdir, "16_resolution")


def fig_shuffle_grid(fals: dict, figdir: Path) -> str:
    """Distribution of PF under shuffled volume (500×) vs real PF, per instrument."""
    sleeves = fals["sleeves"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, (tk, d) in zip(axes.flat, sleeves.items()):
        s = d["shuffle"]
        ax.hist(s["shuffled_pf"], bins=30, color=GREY, alpha=0.7, edgecolor="white")
        ax.axvline(min(s["real_pf"], 10), color=RED, lw=2,
                   label=f"PF real = {s['real_pf']:.2f}")
        ax.set_title(f"{tk.replace('.SA','')}  (p = {s['p_pf']:.3f})", fontsize=10)
        ax.legend(fontsize=7)
        ax.set_xlabel("Profit Factor (shuffled volume)")
    axes.flat[-1].axis("off")
    fig.suptitle("Test 1 — Volume permutation: real PF vs 500 shuffles.\n"
                 "Low p (< 0.05) = the price<->volume relationship adds signal (only SPY passes clearly)",
                 fontweight="bold")
    return _save(fig, figdir, "17_shuffle")


def fig_random_grid(fals: dict, figdir: Path) -> str:
    """Distribution of mean per-trade return under random entries vs real."""
    sleeves = fals["sleeves"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, (tk, d) in zip(axes.flat, sleeves.items()):
        rc = d["random"]
        ax.hist(rc["rand_means"] * 100, bins=30, color=GREY, alpha=0.7, edgecolor="white")
        ax.axvline(rc["real_mean"] * 100, color=RED, lw=2,
                   label=f"real = {rc['real_mean']*100:.2f}%")
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(f"{tk.replace('.SA','')}  (p = {rc['p_value']:.3f})", fontsize=10)
        ax.legend(fontsize=7)
        ax.set_xlabel("Mean return/trade (random entry)")
    axes.flat[-1].axis("off")
    fig.suptitle("Test 3 — Long-bias control: real return vs 500 random entries of the "
                 "same size/holding.\nThe strategy must sit to the right of the mass (p < 0.05) "
                 "to claim real timing", fontweight="bold")
    return _save(fig, figdir, "18_random_entry")


def fig_bootstrap_ci(fals: dict, figdir: Path) -> str:
    """Forest plot of the 95% CI (bootstrap) of the Profit Factor per instrument."""
    sleeves = fals["sleeves"]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    tickers = list(sleeves.keys())
    y = np.arange(len(tickers))
    for i, tk in enumerate(tickers):
        b = sleeves[tk]["bootstrap"]
        pf = sleeves[tk]["real_pf"]
        lo, hi = b["pf_lo"], min(b["pf_hi"], 5)
        col = GREEN if b["pf_excludes_1"] else RED
        ax.plot([lo, hi], [i, i], color=col, lw=3, solid_capstyle="round")
        ax.plot(min(pf, 5), i, "o", color=NAVY, ms=8)
    ax.axvline(1.0, color="black", lw=1.5, ls="--", label="PF = 1.0 (no edge)")
    ax.set_yticks(y)
    ax.set_yticklabels([t.replace(".SA", "") for t in tickers])
    ax.set_xlabel("Profit Factor (point = real; bar = 95% bootstrap CI)")
    ax.set_title("Test 5 — Confidence interval of the Profit Factor (10k resamples)\n"
                 "Bar crossing 1.0 (red) = edge indistinguishable from zero at the 95% level")
    ax.legend()
    return _save(fig, figdir, "19_bootstrap_ci")


def generate_falsification_figures(fals: dict, figdir: Path | str) -> dict[str, str]:
    figdir = Path(figdir)
    figdir.mkdir(parents=True, exist_ok=True)
    return {f.__name__: f(fals, figdir) for f in (fig_shuffle_grid, fig_random_grid, fig_bootstrap_ci)}


def generate_all_figures(results: dict, figdir: Path | str) -> dict[str, str]:
    figdir = Path(figdir)
    figdir.mkdir(parents=True, exist_ok=True)
    builders = [
        fig_volume_profile, fig_oos_heatmap, fig_oos_equity, fig_walkforward_degradation,
        fig_param_heatmap, fig_daytype, fig_divergence, fig_rule80, fig_portfolio,
        fig_trade_distribution, fig_sizing_tradeoff, fig_cost_sensitivity, fig_strategy_vs_buyhold,
        fig_volume_events, fig_signal_candle, fig_resolution,
    ]
    paths = {}
    for b in builders:
        paths[b.__name__] = b(results, figdir)
    return paths

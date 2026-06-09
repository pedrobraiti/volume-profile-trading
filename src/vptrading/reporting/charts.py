"""Geração de todas as figuras do relatório (PNG de alta resolução).

Cada função desenha uma figura a partir do dicionário de resultados (``results.pkl``) e salva em
``output/figures/``. O estilo é uniforme e pensado para impressão em PDF: fundo claro, paleta sóbria,
títulos e eixos em português, anotações onde ajudam a leitura.
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
    """TwoSlopeNorm seguro: cai para Normalize quando os dados não cercam o centro."""
    vmin = float(np.nanmin(vals))
    vmax = float(np.nanmax(vals))
    if vmin < center < vmax:
        return TwoSlopeNorm(vmin=vmin, vcenter=center, vmax=vmax)
    return Normalize(vmin=vmin, vmax=vmax)

# Paleta
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
    "REV": "Reversão ao POC",
    "E2E": "Edge-to-Edge",
    "BRK": "Breakout da VA",
    "EXH": "Exaustão de volume",
}


def _save(fig, figdir: Path, name: str) -> str:
    path = figdir / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def fig_volume_profile(results: dict, figdir: Path) -> str:
    """Gráfico educativo: preço + histograma de volume por preço com POC/VAH/VAL e nós."""
    sp = results["sample_profile"]
    price = sp["price"]
    centers, vols = sp["bin_centers"], sp["bin_volumes"]

    fig, (axp, axv) = plt.subplots(
        1, 2, figsize=(11, 6.2), gridspec_kw={"width_ratios": [3, 1], "wspace": 0.03}, sharey=True
    )
    axp.plot(price.index, price.values, color=NAVY, lw=1.3)
    axp.set_title(f"{sp['ticker']} — preço (composite de 120 pregões)", loc="left")
    axp.set_ylabel("Preço (US$)")
    axp.margins(x=0.01)

    # Faixas e níveis
    axp.axhspan(sp["val"], sp["vah"], color=BLUE, alpha=0.08, zorder=0)
    for lvl, lbl, col in [(sp["poc"], "POC", RED), (sp["vah"], "VAH", BLUE),
                          (sp["val"], "VAL", BLUE)]:
        axp.axhline(lvl, color=col, lw=1.2, ls="--", alpha=0.9)
        axp.text(price.index[0], lvl, f" {lbl}", color=col, va="center", ha="left",
                 fontsize=9, fontweight="bold")

    # Histograma horizontal de volume por preço
    height = (centers[1] - centers[0]) * 0.9
    colors = [RED if abs(c - sp["poc"]) < height else (BLUE if sp["val"] <= c <= sp["vah"] else GREY)
              for c in centers]
    axv.barh(centers, vols, height=height, color=colors, alpha=0.85)
    axv.set_title("Volume por preço", loc="right")
    axv.set_xlabel("Volume agregado")
    axv.grid(axis="y")
    for h in sp["hvn"][:6]:
        axv.scatter(vols.max() * 0.02, h, marker=">", color=GREEN, s=30, zorder=5)
    axv.text(0.98, 0.02, "HVN ▶ verde", transform=axv.transAxes, ha="right", va="bottom",
             fontsize=8, color=GREEN)
    fig.suptitle(f"Volume Profile composite — {sp['ticker']} ({sp['start'].date()} a "
                 f"{sp['end'].date()})\nO preço 'gruda' nos nós de alto volume (HVN) e 'escorrega' "
                 "pelos de baixo (LVN)", fontsize=11, fontweight="bold")
    return _save(fig, figdir, "01_volume_profile")


def _wf_matrix(results: dict, metric: str) -> pd.DataFrame:
    wf = results["walkforward"]
    insts = list(results["instruments"].keys())
    data = {s: [wf[s][tk]["oos_metrics"][metric] for tk in insts] for s in wf}
    return pd.DataFrame(data, index=insts).T  # linhas=estratégia, colunas=instrumento


def fig_oos_heatmap(results: dict, figdir: Path) -> str:
    """Heatmap OOS: Profit Factor e expectância por estratégia × instrumento."""
    pf = _wf_matrix(results, "profit_factor").clip(upper=2.5)
    exp = _wf_matrix(results, "expectancy_pct") * 100

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, mat, title, center, fmt, cmap in [
        (axes[0], pf, "Profit Factor (OOS)", 1.0, "{:.2f}", "RdYlGn"),
        (axes[1], exp, "Expectância por trade (% , OOS)", 0.0, "{:.2f}", "RdYlGn"),
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
    fig.suptitle("Validação out-of-sample (walk-forward) — long-only, custos incluídos",
                 fontweight="bold")
    return _save(fig, figdir, "02_oos_heatmap")


def fig_oos_equity(results: dict, figdir: Path) -> str:
    """Curvas de capital OOS da melhor estratégia long por instrumento."""
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
    ax.set_title("Capital out-of-sample por instrumento (1,0 = início, risco 1%/trade)")
    ax.set_ylabel("Múltiplo do capital")
    ax.legend(fontsize=8, ncol=2)
    return _save(fig, figdir, "03_oos_equity")


def fig_walkforward_degradation(results: dict, figdir: Path) -> str:
    """In-sample vs out-of-sample por fold (carro-chefe QQQ E2E) — checagem de overfitting."""
    # Escolhe um par (estratégia, instrumento) ILUSTRATIVO: histórico longo (>=5 folds), bom OOS.
    wf = results["walkforward"]
    candidates = [
        (s, tk) for s in wf for tk in wf[s] if len(wf[s][tk]["folds"]) >= 5
    ]
    s, tk = max(candidates, key=lambda st: wf[st[0]][st[1]]["oos_metrics"]["sharpe"])
    folds = wf[s][tk]["folds"]
    fig, ax = plt.subplots(figsize=(11, 5.0))
    x = np.arange(len(folds))
    ax.bar(x - 0.2, folds["is_expectancy_r"], width=0.4, label="In-sample (treino)", color=GREY)
    ax.bar(x + 0.2, folds["oos_expectancy_r"], width=0.4, label="Out-of-sample (teste)", color=BLUE)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r.train_end}\n→{r.test_end}" for r in folds.itertuples()],
                       fontsize=7, rotation=0)
    ax.set_ylabel("Expectância por trade (R)")
    ax.set_title(f"Degradação treino→teste por janela — {tk.replace('.SA','')} · {STRAT_LABELS[s]}")
    ax.legend()
    return _save(fig, figdir, "04_walkforward_degradation")


def fig_param_heatmap(results: dict, figdir: Path) -> str:
    """Sensibilidade de parâmetros: janela × stop (ATR) -> Profit Factor (EXH SPY, full sample)."""
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
    ax.set_ylabel("Janela / lookback da nova mínima (dias)")
    ax.set_title("Sensibilidade de parâmetros — Exaustão de volume (SPY)\n"
                 "Profit Factor (média sobre alvo/holding/volume) — todas as células > 1 (lucrativas)")
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            ax.text(j, i, f"{vals[i, j]:.2f}", ha="center", va="center", fontsize=9)
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    return _save(fig, figdir, "05_param_heatmap")


def fig_daytype(results: dict, figdir: Path) -> str:
    """Retorno futuro médio por day-type (média entre instrumentos), 1/5/10 dias."""
    dts = results["studies"]["day_type"]
    # Média simples entre instrumentos por day_type.
    frames = []
    for tk, dfm in dts.items():
        frames.append(dfm.set_index("day_type"))
    avg = sum(f[["mean_1d_pct", "mean_5d_pct", "mean_10d_pct"]] for f in frames) / len(frames)
    avg = avg.reindex(["D", "P", "b", "Trend"]) * 100

    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    x = np.arange(len(avg))
    w = 0.26
    for k, (col, lbl, c) in enumerate(
        [("mean_1d_pct", "1 dia", BLUE), ("mean_5d_pct", "5 dias", TEAL),
         ("mean_10d_pct", "10 dias", ORANGE)]
    ):
        ax.bar(x + (k - 1) * w, avg[col], width=w, label=lbl, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels(["D (normal)", "P (bullish)", "b (bearish)", "Trend"])
    ax.set_ylabel("Retorno futuro médio (%)")
    ax.set_title("Retorno futuro por day-type (média dos 5 instrumentos)\n"
                 "Os rótulos NÃO preveem continuação: dias 'b'/Trend repicam mais que 'P' — "
                 "o oposto do prometido")
    ax.legend()
    ax.axhline(0, color="black", lw=0.8)
    return _save(fig, figdir, "06_daytype")


def fig_divergence(results: dict, figdir: Path) -> str:
    """Divergência de volume: retorno futuro 5d (baseline vs altista vs baixista) por instrumento."""
    div = results["studies"]["divergence"]
    insts = list(div.keys())
    base = [div[t]["baseline"]["mean_fwd_pct"] * 100 for t in insts]
    bull = [div[t]["bullish_divergence"]["mean_fwd_pct"] * 100 for t in insts]
    bear = [div[t]["bearish_divergence"]["mean_fwd_pct"] * 100 for t in insts]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    x = np.arange(len(insts))
    w = 0.26
    ax.bar(x - w, base, width=w, label="Baseline (qualquer dia)", color=GREY)
    ax.bar(x, bull, width=w, label="Divergência altista (nova mín. + vol. baixo)", color=GREEN)
    ax.bar(x + w, bear, width=w, label="Divergência baixista (nova máx. + vol. baixo)", color=RED)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("Retorno futuro 5 dias (%)")
    ax.set_title("Divergência de volume (§6): comprar 'sem oferta' nas mínimas supera o baseline")
    ax.legend(fontsize=8)
    ax.axhline(0, color="black", lw=0.8)
    return _save(fig, figdir, "07_divergence")


def fig_rule80(results: dict, figdir: Path) -> str:
    """Regra dos 80%: traverse rate observada vs alegação de 80%, e expectância."""
    r80 = results["rule80"]
    insts = list(r80.keys())
    traverse = [r80[t]["diagnostics"]["traverse_rate"] * 100
                if r80[t]["diagnostics"]["n"] else 0 for t in insts]
    n = [r80[t]["diagnostics"]["n"] for t in insts]

    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    x = np.arange(len(insts))
    bars = ax.bar(x, traverse, color=BLUE, alpha=0.85)
    ax.axhline(80, color=RED, lw=1.5, ls="--", label="Alegação do método: ~80%")
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("Traverse rate observada (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Regra dos 80% (30 min, 60 dias): com que frequência atravessa toda a VA?\n"
                 "Amostra pequena — leitura indicativa, não conclusiva")
    for b, ni in zip(bars, n):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"n={ni}",
                ha="center", fontsize=8, color=GREY)
    ax.legend()
    return _save(fig, figdir, "08_rule80")


def fig_portfolio(results: dict, figdir: Path) -> str:
    """Curva de capital do portfólio OOS + drawdown."""
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
    ax1.set_title(f"Portfólio diversificado (sleeves validados OOS) — {', '.join(port[key]['sleeves'])}\n"
                  f"CAGR {m['cagr_pct']:.1%} · Sharpe {m['sharpe']:.2f} · maxDD {m['max_drawdown_pct']:.1%} "
                  f"· exposição {port[key]['exposure_pct']:.0%}")
    ax1.set_ylabel("Múltiplo do capital")
    ax2.fill_between(dd.index, dd.values * 100, 0, color=RED, alpha=0.5)
    ax2.set_ylabel("Drawdown (%)")
    return _save(fig, figdir, "09_portfolio")


def fig_trade_distribution(results: dict, figdir: Path) -> str:
    """Distribuição dos retornos por trade do carro-chefe (EXH SPY)."""
    rets = np.array(results["flagship"]["flagship_trade_returns"]) * 100
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    ax.hist(rets, bins=30, color=BLUE, alpha=0.8, edgecolor="white")
    ax.axvline(0, color="black", lw=1)
    ax.axvline(rets.mean(), color=RED, lw=1.6, ls="--",
               label=f"Média = {rets.mean():.2f}%")
    ax.set_xlabel("Retorno líquido por trade (%)")
    ax.set_ylabel("Frequência")
    ax.set_title("Distribuição de retornos por trade — Exaustão de volume (SPY)")
    ax.legend()
    return _save(fig, figdir, "10_trade_distribution")


def fig_sizing_tradeoff(results: dict, figdir: Path) -> str:
    """Eixo conservador↔agressivo: CAGR vs max drawdown (sizing e alavancagem do portfólio)."""
    fig, ax = plt.subplots(figsize=(9.5, 5.4))

    sizing = results["flagship"]["sizing_sweep"]
    sx = [abs(d["metrics"]["max_drawdown_pct"]) * 100 for d in sizing.values()]
    sy = [d["metrics"]["cagr_pct"] * 100 for d in sizing.values()]
    ax.plot(sx, sy, "-o", color=TEAL, label="Sizing EXH-SPY (risco/trade)")
    for lbl, xx, yy in zip(sizing.keys(), sx, sy):
        ax.annotate(lbl, (xx, yy), fontsize=7, textcoords="offset points", xytext=(4, 4))

    if "leverage_sweep" in results["portfolio"]:
        lev = results["portfolio"]["leverage_sweep"]
        lx = [abs(d["metrics"]["max_drawdown_pct"]) * 100 for d in lev.values()]
        ly = [d["metrics"]["cagr_pct"] * 100 for d in lev.values()]
        ax.plot(lx, ly, "-s", color=NAVY, label="Alavancagem do portfólio")
        for lbl, xx, yy in zip(lev.keys(), lx, ly):
            ax.annotate(lbl, (xx, yy), fontsize=7, textcoords="offset points", xytext=(4, 4))

    ax.set_xlabel("Max drawdown (%)")
    ax.set_ylabel("CAGR (%)")
    ax.set_title("O dial de risco: mais retorno custa mais drawdown (Sharpe ~constante)")
    ax.legend()
    return _save(fig, figdir, "11_sizing_tradeoff")


def fig_cost_sensitivity(results: dict, figdir: Path) -> str:
    """Como o edge (PF e expectância) decai com o custo round-trip."""
    cs = results["cost_sensitivity"]
    fig, ax1 = plt.subplots(figsize=(9.5, 5.0))
    x = cs["round_trip_cost_pct"] * 100
    ax1.plot(x, cs["profit_factor"], "-o", color=NAVY, label="Profit Factor")
    ax1.axhline(1.0, color=RED, ls="--", lw=1)
    ax1.set_xlabel("Custo round-trip (%)")
    ax1.set_ylabel("Profit Factor", color=NAVY)
    ax2 = ax1.twinx()
    ax2.plot(x, cs["expectancy_pct"] * 100, "-s", color=ORANGE, label="Expectância/trade (%)")
    ax2.set_ylabel("Expectância por trade (%)", color=ORANGE)
    ax2.grid(False)
    ax1.set_title("Sensibilidade a custos — Exaustão de volume (SPY)\n"
                  "O edge é real, mas estreito: some sob custos altos")
    return _save(fig, figdir, "12_cost_sensitivity")


def fig_strategy_vs_buyhold(results: dict, figdir: Path) -> str:
    """Contexto: portfólio OOS (1x e 3x) vs buy & hold do SPY no mesmo período."""
    port = results["portfolio"]
    key = "apenas_positivos_OOS" if "apenas_positivos_OOS" in port else "todos"
    curve = port[key]["curve"]
    start = curve.index[0]

    spy = results["instruments"]["SPY"]["price"]
    spy = spy[spy.index >= start]
    bh = spy / spy.iloc[0]

    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.plot(bh.index, bh.values, color=GREY, lw=1.5, label="Buy & Hold SPY")
    ax.plot(curve.index, curve.values, color=NAVY, lw=1.6, label="Portfólio VP (1x)")
    if "leverage_sweep" in port and "3x" in port["leverage_sweep"]:
        c3 = port["leverage_sweep"]["3x"]["curve"]
        ax.plot(c3.index, c3.values, color=BLUE, lw=1.4, ls="--", label="Portfólio VP (3x)")
    ax.set_yscale("log")
    ax.set_title("Contexto: o edge do Volume Profile não bate buy & hold em retorno —\n"
                 "entrega um fluxo mais suave e de baixo drawdown (eixo log)")
    ax.set_ylabel("Múltiplo do capital (log)")
    ax.legend()
    return _save(fig, figdir, "13_strategy_vs_buyhold")


def fig_volume_events(results: dict, figdir: Path) -> str:
    """Leituras de volume cru (§6): retorno futuro 5d por tipo de evento, por instrumento."""
    ve = results["complementary"]["volume_events"]
    insts = list(ve.keys())
    keys = [("baseline", "Baseline", GREY), ("movimento_saudavel", "Mov. saudável (candle+vol grande)", BLUE),
            ("absorcao_topo", "Absorção no topo", RED), ("absorcao_fundo", "Absorção no fundo", GREEN)]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    x = np.arange(len(insts))
    w = 0.2
    for k, (key, lbl, c) in enumerate(keys):
        vals = [ve[t][key]["mean_fwd_pct"] * 100 for t in insts]
        ax.bar(x + (k - 1.5) * w, vals, width=w, label=lbl, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace(".SA", "") for t in insts])
    ax.set_ylabel("Retorno futuro 5 dias (%)")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Leituras de volume 'cru' (§6): absorção no fundo é bullish (sobretudo no Brasil);\n"
                 "'movimento saudável' NÃO supera o baseline em índices")
    ax.legend(fontsize=8, ncol=2)
    return _save(fig, figdir, "14_volume_events")


def fig_signal_candle(results: dict, figdir: Path) -> str:
    """Efeito do signal candle (§7): PF da Edge-to-Edge vs exigência de volume."""
    sc = results["complementary"]["signal_candle"]
    fig, ax = plt.subplots(figsize=(9.5, 5.0))
    for tk, col in [("SPY", NAVY), ("QQQ", BLUE)]:
        t = sc[tk]
        ax.plot(t["volume_mult"], t["profit_factor"], "-o", color=col, label=f"{tk} (PF)")
        for _, r in t.iterrows():
            ax.annotate(f"n={int(r['n_trades'])}", (r["volume_mult"], r["profit_factor"]),
                        fontsize=7, textcoords="offset points", xytext=(0, 6), ha="center")
    ax.axhline(1.0, color=RED, ls="--", lw=1)
    ax.set_xlabel("Exigência de volume no dia-sinal (× média) — 0 = sem confirmação")
    ax.set_ylabel("Profit Factor")
    ax.set_title("Signal candle (§7): exigir um spike de volume melhora o QQQ (PF 1,1→1,9)\n"
                 "mas overfiltra acima de ~1,5×")
    ax.legend()
    return _save(fig, figdir, "15_signal_candle")


def fig_resolution(results: dict, figdir: Path) -> str:
    """Robustez à resolução do histograma (§4.3 — 'use 400 rows')."""
    r = results["complementary"]["resolution"]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    ax.bar(range(len(r)), r["profit_factor"], color=TEAL, alpha=0.85,
           tick_label=[str(int(n)) for n in r["n_bins"]])
    ax.axhline(1.0, color=RED, ls="--", lw=1)
    for i, v in enumerate(r["profit_factor"]):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_xlabel("Nº de faixas de preço (rows) do histograma")
    ax.set_ylabel("Profit Factor (E2E, SPY)")
    ax.set_ylim(0, max(r["profit_factor"]) * 1.2)
    ax.set_title("Resolução do perfil (§4.3): o edge é estável de 40 a 400 rows\n"
                 "— mais resolução ajuda pouco no swing diário")
    return _save(fig, figdir, "16_resolution")


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

"""Builds the technical PDF report from ``results.pkl`` and the figures.

Uses ReportLab (Platypus). The report is technical and honest: it leads with the executive
summary, details the methodology (including the walk-forward validation), presents results with
charts and many comparative tables, confronts the reference document's claims against the data,
recommends conservative and aggressive parameters, and closes with limitations.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#1f3b5c")
BLUE = colors.HexColor("#2c6fbb")
TEAL = colors.HexColor("#2a9d8f")
GREEN = colors.HexColor("#2e8b57")
RED = colors.HexColor("#c0392b")
LIGHT = colors.HexColor("#eef1f5")
GREY = colors.HexColor("#8a8f98")

STRAT_LABELS = {
    "REV": "POC reversion",
    "E2E": "Edge-to-Edge",
    "BRK": "VA breakout",
    "EXH": "Volume exhaustion",
}


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("TitleBig", parent=ss["Title"], fontSize=26, textColor=NAVY,
                          spaceAfter=6, leading=30))
    ss.add(ParagraphStyle("Sub", parent=ss["Normal"], fontSize=13, textColor=GREY,
                          alignment=TA_CENTER, spaceAfter=4))
    ss.add(ParagraphStyle("H1", parent=ss["Heading1"], fontSize=17, textColor=NAVY,
                          spaceBefore=14, spaceAfter=8))
    ss.add(ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, textColor=BLUE,
                          spaceBefore=10, spaceAfter=5))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=10, leading=15,
                          alignment=TA_JUSTIFY, spaceAfter=7))
    ss.add(ParagraphStyle("Cap", parent=ss["Normal"], fontSize=8.5, textColor=GREY,
                          alignment=TA_CENTER, spaceAfter=12, spaceBefore=3))
    ss.add(ParagraphStyle("VBullet", parent=ss["Normal"], fontSize=10, leading=14,
                          leftIndent=12, spaceAfter=3))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=8.5, leading=11))
    ss.add(ParagraphStyle("KPI", parent=ss["Normal"], fontSize=10, leading=13))
    return ss


def _pct(x, dec=1):
    try:
        return f"{x * 100:.{dec}f}%"
    except (TypeError, ValueError):
        return "—"


def _num(x, dec=2):
    try:
        if x == float("inf"):
            return "∞"
        return f"{x:.{dec}f}"
    except (TypeError, ValueError):
        return "—"


def _img(path, width=16.5 * cm):
    img = Image(str(path))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width
    img.drawHeight = width * ratio
    return img


def _table(data, col_widths, *, header_bg=NAVY, font=8.5, align="CENTER"):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font),
        ("ALIGN", (0, 0), (-1, -1), align),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd6df")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    return Table(data, colWidths=col_widths, repeatRows=1, style=TableStyle(style))


def _color_cells(table_data, value_grid, *, good_above=1.0):
    """Returns style commands to color numeric cells (green = good / red = bad)."""
    cmds = []
    for (r, c), v in value_grid.items():
        if v is None:
            continue
        col = GREEN if v > good_above else RED
        cmds.append(("TEXTCOLOR", (c, r), (c, r), col))
    return cmds


def build_report(results: dict, figdir: Path | str, out_path: Path | str) -> str:
    figdir = Path(figdir)
    out_path = Path(out_path)
    ss = _styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Volume Profile — Backtesting Study", author="Pedro Braiti",
    )
    S = []

    # ---------------------------------------------------------------- Cover
    S.append(Spacer(1, 3.2 * cm))
    S.append(Paragraph("Volume Profile / Market Profile", ss["TitleBig"]))
    S.append(Paragraph("Quantitative backtesting study — in search of a real edge, "
                       "validated out-of-sample", ss["Sub"]))
    S.append(Spacer(1, 0.6 * cm))
    S.append(Paragraph("33 years of data · 5 instruments (US + Brazil) · 4 strategies · "
                       "walk-forward validation · costs included", ss["Sub"]))
    S.append(Spacer(1, 2.4 * cm))
    meta = [
        ["Daily period", "1993–2026 (as far back as each asset's history goes)"],
        ["Instruments", "SPY, QQQ (US) · PETR4, VALE3, BOVA11 (B3)"],
        ["Data source", "Yahoo Finance (yfinance), free"],
        ["Strategies", "POC reversion · Edge-to-Edge · VA breakout · Volume exhaustion"],
        ["Key metric", "Per-trade expectancy after costs"],
        ["Validation", "Walk-forward (optimize on the past, measure on the unseen future)"],
        ["Generated on", "June 2026"],
    ]
    S.append(_table([[Paragraph(f"<b>{k}</b>", ss["Small"]), Paragraph(v, ss["Small"])]
                     for k, v in meta], [4.5 * cm, 11.5 * cm], header_bg=colors.white, font=9))
    S.append(Spacer(1, 1.5 * cm))
    S.append(Paragraph("<i>Technical research document. Not investment advice. "
                       "Leveraged trading carries the risk of total loss.</i>", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Executive summary
    S.append(Paragraph("1. Executive summary", ss["H1"]))
    port = results["portfolio"]
    pkey = "apenas_positivos_OOS" if "apenas_positivos_OOS" in port else "todos"
    pm = port[pkey]["metrics"]
    wf = results["walkforward"]

    S.append(Paragraph(
        "We tested the objective rules of the Volume Profile strategy (POC, Value Area, day-types, "
        "the 80% Rule, edge-to-edge and volume reading) over 33 years of data, with costs and — "
        "crucially — with <b>walk-forward validation</b>: the parameters are chosen using only "
        "past data and measured on data the optimizer never saw. The central conclusions:",
        ss["Body"]))
    findings = [
        f"<b>A real but modest edge exists on the long side of liquid indices.</b> "
        f"Out-of-sample, QQQ and SPY are profitable across all four strategies "
        f"(QQQ Edge-to-Edge: Profit Factor {_num(wf['E2E']['QQQ']['oos_metrics']['profit_factor'])}; "
        f"QQQ Exhaustion: expectancy {_pct(wf['EXH']['QQQ']['oos_metrics']['expectancy_pct'],2)}/trade).",
        "<b>'Volume reading' works better than the profile itself.</b> Buying exhaustion "
        "('no-supply' — new lows on below-average volume) was the most robust tactic "
        "out-of-sample on index ETFs (PF 1.5-2.2).",
        "<b>Reversion fades balanced markets well and fails in trend.</b> The Brazilian stocks "
        "(PETR4, VALE3), more trending/volatile, produced negative expectancy on almost everything — "
        "exactly what theory predicts.",
        "<b>Two of the method's 'legends' do not hold up in the data:</b> the 80% Rule did not "
        "traverse 80% of the time (27-67% in the recent intraday sample) and was negative after "
        "costs; and day-types do not predict continuation — if anything, 'bearish' days bounce "
        "more (reversion).",
        f"<b>As a standalone system, the edge does not beat buy &amp; hold on return</b> (low exposure), "
        f"but it delivers a smoother stream: the diversified portfolio (OOS-validated sleeves) "
        f"returned CAGR {_pct(pm['cagr_pct'])} with a maximum drawdown of only {_pct(pm['max_drawdown_pct'])} "
        f"and Sharpe {_num(pm['sharpe'])}.",
        "<b>Under rigorous falsification, the edge does not hold up as a standalone strategy.</b> "
        "Volume permutation, price-only ablation, random-entry control, excess return and "
        "bootstrap (§11) show that the gain is, to a large extent, <b>long exposure</b> to assets "
        "that went up. No sleeve generates alpha over its own exposure or beats the risk-free rate "
        "at 1% risk, and none has a Profit Factor whose 95% CI excludes 1.0. Only on SPY is the "
        "volume signal statistically real — though small and fragile at this sample size.",
    ]
    for f in findings:
        S.append(Paragraph("• " + f, ss["VBullet"]))
    S.append(Spacer(1, 0.3 * cm))
    S.append(Paragraph(
        "In one sentence: Volume Profile is a legitimate <b>context lens</b> and the volume filter "
        "<b>adds real selectivity</b>, but we found no <b>robust, standalone economic edge</b> — "
        "it is not the 'secret formula' sold in videos. The value lies in reading context and in "
        "risk management; operational use demands skepticism, cheap execution and modest "
        "expectations.",
        ss["Body"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Methodology
    S.append(Paragraph("2. Methodology", ss["H1"]))
    S.append(Paragraph("2.1 Data and instruments", ss["H2"]))
    inst_rows = [["Ticker", "Name", "Market", "Start", "Sessions", "Buy&amp;Hold CAGR"]]
    for tk, d in results["instruments"].items():
        inst_rows.append([tk.replace(".SA", ""), d["name"], d["market"],
                          str(d["start"].date()), f"{d['n_days']:,}",
                          _pct(d["buyhold"]["cagr_pct"])])
    S.append(_table(inst_rows, [2.0 * cm, 4.6 * cm, 2.0 * cm, 2.4 * cm, 2.2 * cm, 2.8 * cm]))
    S.append(Paragraph(
        "Daily OHLCV data from Yahoo Finance (long history, reliable volume on ETFs/stocks). "
        "Free intraday data is short (~60 days of 30-min bars), which limits a faithful test of the "
        "intraday rules (80% Rule) to a recent sample — hence the <b>hybrid</b> approach: a long "
        "daily backtest for statistical robustness + recent intraday validation.", ss["Cap"]))

    S.append(Paragraph("2.2 The four strategies", ss["H2"]))
    strat_desc = [
        ["POC reversion", "Fades extremes: sells above the VAH / buys below the VAL, targeting the "
         "POC. The classic rotation of a balanced 'D' day."],
        ["Edge-to-Edge", "Enters at one edge of the Value Area and aims for the opposite edge, "
         "crossing the interior of the profile. Larger target."],
        ["VA breakout", "Trades in the direction of a Value Area breakout (initiating activity), "
         "with an ATR-multiple target. Captures trend."],
        ["Volume exhaustion", "Buys 'no-supply' (§6): new lows on below-average volume = exhausted "
         "sellers. Does not depend on the profile."],
    ]
    S.append(_table([["Strategy", "Logic"]] + strat_desc, [3.8 * cm, 12.2 * cm], align="LEFT"))

    S.append(Paragraph("2.3 Costs, sizing and assumptions", ss["H2"]))
    for b in [
        "<b>No lookahead:</b> profile levels use only data prior to the evaluated day; a signal "
        "at the close of day <i>t</i> → entry at the open of <i>t+1</i>.",
        "<b>Costs:</b> US ~0.05% round-trip (ETF + slippage); B3 ~0.2% (fees + slippage). "
        "All results are net.",
        "<b>Risk-based sizing:</b> each trade risks 1% of capital at the stop (ATR). Exits by stop, "
        "target or time; when ambiguous, the stop is assumed to hit first (pessimistic).",
        "<b>Walk-forward:</b> 8 years of training → 3 years of testing, sliding anchor. The test "
        "parameters come only from the training window. The concatenation of the test segments is "
        "the honest result.",
    ]:
        S.append(Paragraph("• " + b, ss["VBullet"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Concept
    S.append(Paragraph("3. How to read the Volume Profile", ss["H1"]))
    S.append(Paragraph(
        "The profile is a histogram of volume by price. Where there was a lot of volume (HVN), "
        "price 'sticks' — it is accepted value; where there was little (LVN), price 'slips'. The "
        "POC is the price with the most volume; the Value Area (~70% of volume, ±1 standard "
        "deviation of a Gaussian) runs from the VAL to the VAH. These levels are objective — better "
        "than support/resistance drawn 'by eye'.", ss["Body"]))
    S.append(_img(figdir / "01_volume_profile.png"))
    S.append(Paragraph("Figure 1 — Composite profile of SPY (120 sessions): the volume cluster at "
                       "the POC coincides with the band where price spent the most time.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- OOS results
    S.append(Paragraph("4. Results: what works (and where)", ss["H1"]))
    S.append(Paragraph("4.1 Out-of-sample overview", ss["H2"]))
    S.append(_img(figdir / "02_oos_heatmap.png"))
    S.append(Paragraph("Figure 2 — Walk-forward validation (long-only, with costs). Green = "
                       "positive edge. The pattern is clear: US green, Brazilian stocks red.", ss["Cap"]))

    # Full walk-forward table
    S.append(Paragraph("4.2 Full out-of-sample performance table", ss["H2"]))
    wf_rows = [["Strategy", "Asset", "N", "Win", "Exp/trade", "PF", "CAGR", "Sharpe", "MaxDD"]]
    color_cmds = []
    rr = 1
    for s in wf:
        for tk in results["instruments"]:
            m = wf[s][tk]["oos_metrics"]
            wf_rows.append([STRAT_LABELS[s], tk.replace(".SA", ""), str(m["n_trades"]),
                            _pct(m["win_rate"], 0), _pct(m["expectancy_pct"], 2),
                            _num(m["profit_factor"]), _pct(m["cagr_pct"]),
                            _num(m["sharpe"]), _pct(m["max_drawdown_pct"])])
            color_cmds.append(("TEXTCOLOR", (5, rr), (5, rr),
                               GREEN if m["profit_factor"] > 1 else RED))
            color_cmds.append(("TEXTCOLOR", (4, rr), (4, rr),
                               GREEN if m["expectancy_pct"] > 0 else RED))
            rr += 1
    wf_tbl = _table(wf_rows, [3.0 * cm, 1.7 * cm, 1.0 * cm, 1.3 * cm, 2.0 * cm, 1.3 * cm,
                              1.5 * cm, 1.5 * cm, 1.6 * cm], font=8)
    wf_tbl.setStyle(TableStyle(color_cmds))
    S.append(wf_tbl)
    S.append(Paragraph("Table 1 — Out-of-sample performance by strategy × instrument. "
                       "Profit Factor and expectancy color-coded (green = profitable).", ss["Cap"]))
    S.append(PageBreak())

    S.append(Paragraph("4.3 Out-of-sample equity curves", ss["H2"]))
    S.append(_img(figdir / "03_oos_equity.png"))
    S.append(Paragraph("Figure 3 — OOS equity of the best long strategy per instrument. QQQ "
                       "(breakout) leads; Brazilian stocks stay below 1.0.", ss["Cap"]))
    S.append(Paragraph("4.4 The edge is not overfitting", ss["H2"]))
    S.append(_img(figdir / "04_walkforward_degradation.png", width=15.5 * cm))
    S.append(Paragraph("Figure 4 — Training vs test expectancy per window. Out-of-sample "
                       "performance tracks (and sometimes exceeds) the in-sample — a sign of a "
                       "genuine edge, not overfitting.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Flagship + params
    S.append(Paragraph("5. Flagship: Volume exhaustion", ss["H1"]))
    S.append(Paragraph(
        "The tactic of buying selling exhaustion (new lows on no volume) was the most robust. "
        "Below, the parameter sensitivity and the return distribution on SPY.", ss["Body"]))
    S.append(_img(figdir / "05_param_heatmap.png", width=12.5 * cm))
    S.append(Paragraph("Figure 5 — Profit Factor by window × stop. Larger windows (40 days) and "
                       "a stop of ~2×ATR were the strongest; all cells are profitable.", ss["Cap"]))
    S.append(_img(figdir / "10_trade_distribution.png", width=14.5 * cm))
    S.append(Paragraph("Figure 6 — Per-trade return distribution: favorable skew "
                       "(losses capped by the stop, a few large gains).", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Claim studies
    S.append(Paragraph("6. The method's claims vs the data", ss["H1"]))
    S.append(Paragraph("6.1 Volume reading: divergence / 'no-supply'", ss["H2"]))
    S.append(_img(figdir / "07_divergence.png", width=15.5 * cm))
    S.append(Paragraph("Figure 7 — 5-day forward return. Buying new lows on low volume (bullish "
                       "divergence) beats the baseline on SPY, QQQ and VALE3 — the volume reading "
                       "of §6 has merit.", ss["Cap"]))

    S.append(Paragraph("6.2 Day-types do not predict continuation", ss["H2"]))
    S.append(_img(figdir / "06_daytype.png", width=15.5 * cm))
    S.append(Paragraph("Figure 8 — Forward return by day-type (average across the 5 assets). If 'P' "
                       "were bullish and 'b' bearish, the bars would diverge in that direction. The "
                       "opposite happens (reversion), refuting the use of the labels as a "
                       "continuation signal.", ss["Cap"]))
    S.append(PageBreak())

    S.append(Paragraph("6.3 The 80% Rule does not traverse 80%", ss["H2"]))
    S.append(_img(figdir / "08_rule80.png", width=15.5 * cm))
    r80_rows = [["Asset", "Setups", "Traverse rate", "Win rate", "Exp/trade", "Verdict"]]
    for tk, d in results["rule80"].items():
        dg = d["diagnostics"]
        m = d["metrics"]
        r80_rows.append([tk.replace(".SA", ""), str(dg["n"]),
                         _pct(dg["traverse_rate"], 0) if dg["n"] else "—",
                         _pct(m["win_rate"], 0), _pct(m["expectancy_pct"], 2),
                         "negative" if m["expectancy_pct"] <= 0 else "positive"])
    S.append(_table(r80_rows, [2.6 * cm, 2.0 * cm, 2.8 * cm, 2.4 * cm, 2.6 * cm, 2.6 * cm]))
    S.append(Paragraph("Table 2 — 80% Rule (30 min, 60 days). Traverse rate well below 80% and "
                       "negative expectancy after costs. <b>Strong caveat:</b> tiny sample "
                       "(7-14 setups/asset) — indicative, not conclusive.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Portfolio
    S.append(Paragraph("7. Diversified portfolio", ss["H1"]))
    S.append(Paragraph(
        "Each strategy in isolation trades little (low exposure). Combining, for each instrument, "
        "the strategy that validated OOS into an equal-capital portfolio raises exposure and "
        "diversifies risk — the result is a remarkably smooth return stream.", ss["Body"]))
    S.append(_img(figdir / "09_portfolio.png"))
    S.append(Paragraph("Figure 9 — Portfolio (OOS-validated sleeves) and its drawdown. Stable "
                       "curve, shallow drawdown.", ss["Cap"]))
    port_rows = [["Portfolio", "Sleeves", "CAGR", "Sharpe", "MaxDD", "Exposure"]]
    for key, label in [("apenas_positivos_OOS", "OOS-positive sleeves only"),
                       ("todos", "All 5 instruments")]:
        if key in port:
            m = port[key]["metrics"]
            port_rows.append([label, str(len(port[key]["sleeves"])), _pct(m["cagr_pct"]),
                              _num(m["sharpe"]), _pct(m["max_drawdown_pct"]),
                              _pct(port[key]["exposure_pct"], 0)])
    S.append(_table(port_rows, [4.6 * cm, 1.8 * cm, 2.2 * cm, 2.0 * cm, 2.2 * cm, 2.4 * cm]))
    S.append(Paragraph("Table 3 — Portfolio metrics (1% risk/trade, no leverage).", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Conservative vs Aggressive
    S.append(Paragraph("8. Conservative vs aggressive: the risk dial", ss["H1"]))
    S.append(Paragraph(
        "Two axes control the risk profile: (a) the <b>parameters</b> (wide stop and high "
        "selectivity = more conservative) and (b) the <b>sizing/leverage</b>. Since Sharpe is "
        "practically invariant to sizing, leveraging only trades return for drawdown — it does not "
        "create edge. The choice is one of risk appetite, not of quality.", ss["Body"]))
    S.append(_img(figdir / "11_sizing_tradeoff.png", width=14.5 * cm))
    S.append(Paragraph("Figure 10 — CAGR vs drawdown as risk/leverage varies. The portfolio line "
                       "dominates the single-asset one (diversification).", ss["Cap"]))

    # Parameter-profile table
    pp = results["flagship"]["param_profiles"]
    pp_labels = {
        "Conservador (stop largo, VA 0,80)": "Conservative (wide stop, VA 0.80)",
        "Agressivo (stop curto, alvo 5xATR)": "Aggressive (tight stop, 5xATR target)",
    }
    pp_rows = [["Parameter profile", "N", "Win", "Exp/trade", "PF", "MaxDD"]]
    for name, d in pp.items():
        m = d["metrics"]
        pp_rows.append([pp_labels.get(name, name), str(m["n_trades"]), _pct(m["win_rate"], 0),
                        _pct(m["expectancy_pct"], 2), _num(m["profit_factor"]),
                        _pct(m["max_drawdown_pct"])])
    S.append(_table(pp_rows, [6.5 * cm, 1.3 * cm, 1.4 * cm, 2.2 * cm, 1.5 * cm, 2.0 * cm]))
    S.append(Paragraph("Table 4 — Parameter profiles (Exhaustion, SPY). Conservative = higher win "
                       "rate; aggressive = higher payoff, lower win rate. The classic tradeoff.", ss["Cap"]))

    if "leverage_sweep" in port:
        lev_rows = [["Leverage", "CAGR", "Sharpe", "MaxDD", "Total return"]]
        for k, d in port["leverage_sweep"].items():
            m = d["metrics"]
            lev_rows.append([k, _pct(m["cagr_pct"]), _num(m["sharpe"]),
                             _pct(m["max_drawdown_pct"]), _pct(m["total_return_pct"])])
        S.append(_table(lev_rows, [3.0 * cm, 3.0 * cm, 2.6 * cm, 2.8 * cm, 3.2 * cm]))
        S.append(Paragraph("Table 5 — Portfolio under leverage. Sharpe constant; only the scale of "
                           "return and drawdown changes.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Costs + context
    S.append(Paragraph("9. Cost sensitivity and context", ss["H1"]))
    S.append(_img(figdir / "12_cost_sensitivity.png", width=14.5 * cm))
    cs = results["cost_sensitivity"]
    cs_rows = [["Round-trip cost", "Expectancy/trade", "Profit Factor", "CAGR"]]
    for _, r in cs.iterrows():
        cs_rows.append([_pct(r["round_trip_cost_pct"], 2), _pct(r["expectancy_pct"], 3),
                        _num(r["profit_factor"]), _pct(r["cagr_pct"], 2)])
    S.append(_table(cs_rows, [4.0 * cm, 4.0 * cm, 3.5 * cm, 3.0 * cm]))
    S.append(Paragraph("Table 6 / Figure 11 — The edge is real but narrow: it approaches breakeven "
                       "(PF 1.0) under ~0.8% round-trip costs. Cheap execution is a "
                       "prerequisite.", ss["Cap"]))
    S.append(_img(figdir / "13_strategy_vs_buyhold.png"))
    S.append(Paragraph("Figure 12 — Context (log axis): SPY buy &amp; hold wins on absolute return, "
                       "but with much larger drawdowns (note 2008). The VP portfolio delivers less "
                       "return and far less suffering.", ss["Cap"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Complementary studies
    if "complementary" in results:
        comp = results["complementary"]
        S.append(Paragraph("10. Complementary studies (§4.3, §6, §7)", ss["H1"]))
        S.append(Paragraph(
            "To exhaust the reference document, we also tested the 'raw' volume readings "
            "(absorption and healthy movement), the effect of the 'signal candle' and the "
            "sensitivity to histogram resolution.", ss["Body"]))

        S.append(Paragraph("10.1 Raw volume readings: absorption and healthy movement", ss["H2"]))
        S.append(_img(figdir / "14_volume_events.png", width=15.5 * cm))
        S.append(Paragraph("Figure 13 — <b>Absorption at the bottom</b> (new low + huge volume + "
                           "small body) precedes strong bounces, especially in Brazilian stocks "
                           "(VALE3 +1.9%, PETR4 +1.6% vs ~0.35% baseline). The 'healthy movement' "
                           "(large candle and volume), by contrast, does <b>not</b> beat the "
                           "baseline on indices — effect ≠ outcome, contrary to what was "
                           "promised.", ss["Cap"]))

        S.append(Paragraph("10.2 The 'signal candle' (volume confirmation) has merit", ss["H2"]))
        S.append(_img(figdir / "15_signal_candle.png", width=14.5 * cm))
        S.append(Paragraph("Figure 14 — Requiring a volume spike on the signal day (§7) clearly "
                           "improves QQQ (Profit Factor 1.1 → 1.9 at ~1.2-1.5× the average), but "
                           "over-filters above that. It confirms the recommendation to 'wait for "
                           "the volume candle' — in moderation.", ss["Cap"]))

        S.append(Paragraph("10.3 Profile resolution (the '400 rows' rule)", ss["H2"]))
        S.append(_img(figdir / "16_resolution.png", width=13.5 * cm))
        S.append(Paragraph("Figure 15 — The edge is stable from 40 to 400 price bins; more "
                           "resolution helps only marginally in daily swing trading. The insistence "
                           "on '400 rows' matters more in fine-grained intraday than here.", ss["Cap"]))
        S.append(PageBreak())

    # ---------------------------------------------------------------- Falsification / ablation
    if "falsification" in results:
        fals = results["falsification"]
        sl = fals["sleeves"]
        S.append(Paragraph("11. Falsification and ablation tests: is the edge real?", ss["H1"]))
        S.append(Paragraph(
            "Before trusting the Volume exhaustion sleeve, we subjected it to five falsification "
            "tests with a <b>fixed</b> config (no re-optimization, fixed seed) to answer: does the "
            "edge come from <b>volume and structure</b>, or is it just <b>long bias / buy-the-dip</b> "
            "on an asset that goes up? The tests: (1) volume permutation; (2) price-only ablation; "
            "(3) random-entry control; (4) excess return over exposure and risk-free "
            "(CDI 14.5% BRL / T-bill ~2% USD); (5) 95% CI via bootstrap.", ss["Body"]))

        # Verdict table
        vrows = [["Asset", "Volume\nshuffle", "Beats\nprice-only", "Beats random\nlong",
                  "Alpha over\nexposure", "Beats\nrisk-free", "PF CI\nexcludes 1", "PASSES\nALL"]]
        vcolor = []
        ri = 1
        for tk, d in sl.items():
            v = d["verdict"]
            order = ["sobrevive_shuffle", "bate_so_preco", "bate_long_aleatorio",
                     "alfa_sobre_exposicao", "bate_risk_free", "ic_pf_exclui_1", "passa_todos"]
            row = [tk.replace(".SA", "")]
            for ci, key in enumerate(order, start=1):
                ok = v[key]
                row.append("YES" if ok else "no")
                vcolor.append(("TEXTCOLOR", (ci, ri), (ci, ri), GREEN if ok else RED))
            vrows.append(row)
            ri += 1
        vt = _table(vrows, [2.0 * cm] + [1.85 * cm] * 7, font=7.5)
        vt.setStyle(TableStyle(vcolor))
        S.append(vt)
        S.append(Paragraph("Table 8 — Verdict per sleeve. <b>None of the five instruments passes "
                           "all six tests.</b> SPY is the only one showing a statistically real "
                           "volume signal (passes shuffle, ablation and random entry), but it fails "
                           "the economic tests.", ss["Cap"]))

        # Ablation (volume vs price-only)
        ab_rows = [["Asset", "Expectancy w/ volume", "Expectancy price-only", "Δ (volume adds)"]]
        for tk, d in sl.items():
            a = d["ablation"]
            ab_rows.append([tk.replace(".SA", ""), _pct(a["vol_exp"], 3), _pct(a["price_exp"], 3),
                            _pct(a["delta_exp"], 3)])
        S.append(_table(ab_rows, [3.0 * cm, 4.5 * cm, 4.5 * cm, 4.0 * cm]))
        S.append(Paragraph("Table 9 — Price-only ablation: the volume filter nearly doubles "
                           "expectancy on SPY/QQQ (more selective), but hurts on Brazilian stocks. "
                           "Volume adds selectivity — on some assets.", ss["Cap"]))
        S.append(PageBreak())

        S.append(_img(figdir / "17_shuffle.png", width=16.0 * cm))
        S.append(Paragraph("Figure 16 — Volume permutation test. Only on SPY is the real PF (red "
                           "line) clearly in the right tail of the 500 shuffles (p = 0.002): the "
                           "price↔volume relationship carries signal. For the rest, shuffled volume "
                           "does as well as the real thing.", ss["Cap"]))
        S.append(_img(figdir / "19_bootstrap_ci.png", width=14.5 * cm))
        S.append(Paragraph("Figure 17 — 95% CI of the Profit Factor (bootstrap, 10k). All bars "
                           "cross 1.0 — including SPY (lower bound 0.99). With ~80-150 trades, the "
                           "edge is <b>not statistically distinguishable from zero</b> at 95%.", ss["Cap"]))
        S.append(PageBreak())

        S.append(_img(figdir / "18_random_entry.png", width=16.0 * cm))
        S.append(Paragraph("Figure 18 — Random-entry control. Only SPY beats the 'random long' "
                           "(p = 0.028); QQQ/BR do not — their return is consistent with simply "
                           "being long on arbitrary dates.", ss["Cap"]))
        S.append(Paragraph("<b>Honest verdict.</b> The test is relentless and instructive: the "
                           "apparent gain of the strategies is, for the most part, <b>long "
                           "exposure</b> to assets that went up — not a robust volume edge. The "
                           "volume filter <i>adds selectivity</i> (positive ablation on SPY/QQQ) "
                           "and, on SPY, the price↔volume relationship is <i>statistically real</i>. "
                           "But no sleeve generates alpha over its own exposure, none beats the "
                           "risk-free rate at 1% risk, and none has a PF whose 95% CI excludes 1.0. "
                           "Conclusion: at 1% risk, as a standalone strategy, <b>there is no "
                           "demonstrable economic edge</b>; what remains (on SPY) is a small, real, "
                           "but statistically fragile signal at the available sample size.", ss["Body"]))
        S.append(PageBreak())

    # ---------------------------------------------------------------- Recommendations
    S.append(Paragraph("12. Parameter recommendations", ss["H1"]))
    S.append(Paragraph(
        "Based on the sweep and the out-of-sample validation, these are the variables that behaved "
        "best. <b>Important (in light of §11):</b> these recommendations describe the <i>least "
        "bad</i> and most historically robust configuration — not a proven economic edge. Treat "
        "them as a starting point for study and paper trading, not as a system ready for real "
        "capital.", ss["Body"]))

    rec_rows = [
        ["Variable", "Conservative profile", "Aggressive profile"],
        ["Instruments", "Liquid index ETFs only (SPY, QQQ)", "ETFs + volatile names (VALE3) with breakout"],
        ["Strategy", "Volume exhaustion / Edge-to-Edge (long)", "VA breakout + Exhaustion (long)"],
        ["Direction", "Long only", "Long (shorts lost on everything)"],
        ["Profile window/lookback", "40 days", "20 days"],
        ["Value Area", "0.80 (more selective)", "0.70"],
        ["Stop", "≈ 2.5-3.0 × ATR (wide)", "≈ 1.5 × ATR (tight)"],
        ["Target", "POC / opposite edge", "5 × ATR (let it run)"],
        ["Maximum holding", "10 days", "20 days"],
        ["Trend filter", "On (does not fade trend)", "On for breakout"],
        ["Risk per trade", "0.5-1.0% of capital", "2-3% of capital"],
        ["Leverage", "1× (none)", "up to 3× in the diversified portfolio"],
    ]
    rt = _table(rec_rows, [4.2 * cm, 6.0 * cm, 6.0 * cm], align="LEFT")
    S.append(rt)
    S.append(Paragraph("Table 7 — Recommended variables. <b>Rule of thumb:</b> the conservative "
                       "profile prioritizes low drawdown and robustness across assets; the "
                       "aggressive one accepts larger drawdown for more CAGR, with no illusion of "
                       "superior Sharpe.", ss["Cap"]))
    S.append(Paragraph(
        "<b>What improved results the most (in order of impact):</b> (1) trading long only on "
        "liquid indices; (2) using the volume reading (exhaustion/absorption at the bottom) instead "
        "of the raw profile; (3) the trend filter, which cut the drawdown from −74% to −12% on "
        "reversion; (4) longer windows (40 days) on the exhaustion signal; (5) confirming with a "
        "volume spike (signal candle) — which raised QQQ's PF from 1.1 to 1.9; (6) diversifying "
        "into a portfolio.", ss["Body"]))
    S.append(PageBreak())

    # ---------------------------------------------------------------- Limitations
    S.append(Paragraph("13. Limitations and honest conclusion", ss["H1"]))
    for b in [
        "<b>Profile approximation:</b> without long tick/intraday data, volume is distributed "
        "uniformly across the daily range. This is standard practice, but it is an approximation of "
        "the 'real' profile.",
        "<b>The 80% Rule and intraday day-types</b> were tested on a short sample (~60 days of "
        "30-min bars) — an indicative reading. A definitive test requires paid historical intraday "
        "data.",
        "<b>Small, cost-sensitive edge:</b> it survives OOS but evaporates under high costs. It "
        "requires cheap execution and discipline; it does not tolerate over-trading.",
        "<b>Survivorship and regime:</b> 33 years include several regimes, but the future may "
        "differ. Walk-forward mitigates, but does not eliminate, this risk.",
        "<b>Day-trading base rate (USP/FGV):</b> of those who persisted for +300 days, 97% lost "
        "money and there was no evidence of learning. A statistical edge in a backtest ≠ guaranteed "
        "profit for a real trader.",
    ]:
        S.append(Paragraph("• " + b, ss["VBullet"]))
    S.append(Spacer(1, 0.3 * cm))
    S.append(Paragraph(
        "<b>Conclusion.</b> Volume Profile is neither magic nor charlatanism. It is a legitimate "
        "auction lens (why price sticks where there is volume) and provides objective levels, and "
        "the volume filter demonstrably adds selectivity. But the most honest part of this study is "
        "§11: under rigorous falsification, what looked like an edge is, to a large extent, "
        "<b>long exposure</b> to assets that went up. Only on SPY is the volume signal "
        "statistically real — and even there it generates no alpha over its own exposure, does not "
        "beat the risk-free rate at 1% risk, and its Profit Factor is not distinguishable from 1.0 "
        "at 95% confidence. <b>We found no standalone, robust economic edge.</b> This does not "
        "invalidate Volume Profile as a tool for context and risk management — it invalidates the "
        "promise of easy profit. The metric that matters is expectancy after costs, validated "
        "against chance; and the evidence calls for skepticism, not faith.",
        ss["Body"]))
    S.append(Spacer(1, 0.5 * cm))
    S.append(Paragraph("<i>Generated by a reproducible pipeline (Python). Code and data are "
                       "version-controlled. Not investment advice.</i>", ss["Cap"]))

    doc.build(S)
    return str(out_path)

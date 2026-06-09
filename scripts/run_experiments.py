"""Orquestra todos os experimentos e salva os resultados para o relatório.

Produz:
- output/results.pkl  -> dicionário completo (métricas, curvas, folds, estudos, portfólio).
- output/data/*.csv   -> tabelas legíveis (cross-section, grids, folds, estudos).

Cobre, end-to-end:
1. Benchmark buy & hold por instrumento.
2. Matriz cross-section (estratégia × instrumento × direção) com config default.
3. Walk-forward OOS (in-sample -> out-of-sample) para cada estratégia × instrumento.
4. Perfis conservador vs agressivo da estratégia-carro-chefe.
5. Portfólio diversificado de sleeves validados OOS.
6. Regra dos 80% intraday (P&L + diagnóstico de traverse rate).
7. Estudos: retorno por day-type, divergência de volume.
8. Sensibilidade a custos.
9. Perfil de volume de exemplo (para o gráfico educativo).
"""

from __future__ import annotations

import pickle
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from vptrading.analysis.studies import (  # noqa: E402
    combine_portfolio_returns,
    day_type_forward_returns,
    rule80_diagnostics,
    volume_divergence_study,
    volume_event_study,
)
from vptrading.backtest.costs import COST_MODELS, CostModel  # noqa: E402
from vptrading.backtest.metrics import compute_metrics  # noqa: E402
from vptrading.core.composite import rolling_composite_levels  # noqa: E402
from vptrading.core.profile import build_volume_profile  # noqa: E402
from vptrading.data import INSTRUMENTS, load_daily, load_intraday  # noqa: E402
from vptrading.optimization.search import (  # noqa: E402
    expand_daily_grid,
    full_sample_grid,
    metrics_on_window,
    run_daily_strategy,
    walk_forward,
)
from vptrading.strategies.daily import (  # noqa: E402
    DailyParams,
    edge_to_edge_signals,
    va_breakout_signals,
    va_reversion_signals,
    volume_exhaustion_signals,
)
from vptrading.strategies.rule80 import Rule80Params, backtest_rule80  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "output"
DATA_OUT = OUT / "data"
OUT.mkdir(exist_ok=True)
DATA_OUT.mkdir(exist_ok=True)

# Estratégias diárias: (signal_fn, label, descrição curta, grade de parâmetros, base).
VP_GRID = {
    "window": [40, 60, 90, 120],
    "value_area_pct": [0.70, 0.80],
    "stop_atr_mult": [1.0, 1.5, 2.5],
    "max_holding_days": [10, 20, 40],
}
BRK_GRID = {
    "window": [40, 60, 90, 120],
    "value_area_pct": [0.70, 0.80],
    "stop_atr_mult": [1.5, 2.5],
    "target_atr_mult": [2.0, 3.0, 5.0],
    "max_holding_days": [10, 20, 40],
}
EXH_GRID = {
    "window": [10, 20, 40],
    "stop_atr_mult": [1.5, 2.0, 3.0],
    "target_atr_mult": [2.0, 3.0, 5.0],
    "max_holding_days": [5, 10, 20],
    "volume_mult": [0.8, 1.0],
}

STRATEGIES = {
    "REV": (va_reversion_signals, "Reversão ao POC (fade de extremos)", VP_GRID),
    "E2E": (edge_to_edge_signals, "Edge-to-Edge (borda a borda da VA)", VP_GRID),
    "BRK": (va_breakout_signals, "Breakout da Value Area (atividade iniciante)", BRK_GRID),
    "EXH": (volume_exhaustion_signals, "Exaustão de volume (no-supply / sem oferta)", EXH_GRID),
}


def buyhold(df: pd.DataFrame) -> dict:
    close = df["Close"]
    daily = close.pct_change().fillna(0.0)
    curve = (1 + daily).cumprod()
    years = (df.index[-1] - df.index[0]).days / 365.25
    cagr = float(curve.iloc[-1] ** (1 / years) - 1)
    dd = float(((curve / curve.cummax()) - 1).min())
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0
    return {
        "total_return_pct": float(curve.iloc[-1] - 1),
        "cagr_pct": cagr,
        "max_drawdown_pct": dd,
        "sharpe": sharpe,
        "curve": curve,
        "years": years,
    }


def cross_section(results: dict) -> pd.DataFrame:
    """Config default por estratégia, em todos os instrumentos, long+short e long-only."""
    rows = []
    for tk, inst in INSTRUMENTS.items():
        df = load_daily(tk)
        cm = COST_MODELS[inst.market]
        for sname, (fn, _, _) in STRATEGIES.items():
            for ld, sd, dlbl in [(True, True, "L+S"), (True, False, "L")]:
                base = dict(allow_long=ld, allow_short=sd, trend_filter=(sname != "EXH"))
                if sname == "EXH":
                    p = DailyParams(window=20, stop_atr_mult=2.0, target_atr_mult=3.0,
                                    max_holding_days=10, **base)
                elif sname == "BRK":
                    p = DailyParams(window=60, stop_atr_mult=2.0, target_atr_mult=3.0,
                                    max_holding_days=20, **base)
                else:
                    p = DailyParams(window=60, stop_atr_mult=1.5, max_holding_days=15, **base)
                m = run_daily_strategy(df, fn, p, cost_model=cm, cache_key=tk).metrics
                row = {"instrument": tk, "market": inst.market, "strategy": sname,
                       "direction": dlbl}
                row.update({k: getattr(m, k) for k in
                            ["n_trades", "win_rate", "expectancy_r", "expectancy_pct",
                             "profit_factor", "cagr_pct", "sharpe", "max_drawdown_pct"]})
                rows.append(row)
    return pd.DataFrame(rows)


def run_walkforward(results: dict) -> dict:
    """Walk-forward OOS long-only para cada estratégia × instrumento."""
    wf_out: dict = {}
    for sname, (fn, label, grid) in STRATEGIES.items():
        wf_out[sname] = {}
        base = DailyParams(allow_long=True, allow_short=False, trend_filter=(sname != "EXH"))
        plist = expand_daily_grid(base, grid)
        for tk, inst in INSTRUMENTS.items():
            df = load_daily(tk)
            cm = COST_MODELS[inst.market]
            wf = walk_forward(df, fn, plist, cost_model=cm, cache_key=tk,
                              train_years=8, test_years=3, min_trades_is=25)
            m = wf.oos_metrics
            curve = (1 + wf.oos_daily_returns).cumprod() if len(wf.oos_daily_returns) else pd.Series(dtype=float)
            wf_out[sname][tk] = {
                "label": label,
                "oos_metrics": m.as_row(),
                "oos_curve": curve,
                "oos_daily_returns": wf.oos_daily_returns,
                "folds": wf.folds,
                "n_combos": len(plist),
            }
            wf.folds.to_csv(DATA_OUT / f"wf_folds_{sname}_{tk.replace('.', '_')}.csv", index=False)
    return wf_out


def flagship_deepdive(results: dict) -> dict:
    """Deep-dive do carro-chefe: grade completa em SPY + sensibilidade de parâmetros + perfis."""
    df = load_daily("SPY")
    cm = COST_MODELS["US"]
    deep = {}

    # Grade completa EXH long-only em SPY (para heatmap de sensibilidade).
    base = DailyParams(allow_long=True, allow_short=False, trend_filter=False)
    plist = expand_daily_grid(base, EXH_GRID)
    table, _ = full_sample_grid(df, volume_exhaustion_signals, plist, cost_model=cm, cache_key="SPY")
    table.to_csv(DATA_OUT / "grid_EXH_SPY.csv", index=False)
    deep["exh_spy_grid"] = table

    # E2E long-only grade em SPY também (segundo carro-chefe).
    base2 = DailyParams(allow_long=True, allow_short=False, trend_filter=True)
    plist2 = expand_daily_grid(base2, VP_GRID)
    table2, _ = full_sample_grid(df, edge_to_edge_signals, plist2, cost_model=cm, cache_key="SPY")
    table2.to_csv(DATA_OUT / "grid_E2E_SPY.csv", index=False)
    deep["e2e_spy_grid"] = table2

    # Config validada (boa) usada como base para isolar o efeito de SIZING/risco.
    good = DailyParams(window=20, stop_atr_mult=2.0, target_atr_mult=3.0, max_holding_days=10,
                       volume_mult=1.0, allow_long=True, allow_short=False, trend_filter=False)

    # Eixo conservador -> agressivo = mesmo edge, risco por trade crescente (max_leverage alto para
    # não ser o cap a limitar; assim o risco por trade é que controla a fração investida).
    sizing = {}
    for label, risk in [("0,5% risco", 0.005), ("1% risco", 0.01),
                        ("2% risco", 0.02), ("3% risco", 0.03)]:
        res = run_daily_strategy(df, volume_exhaustion_signals, good, cost_model=cm,
                                 cache_key="SPY", risk_per_trade=risk, max_leverage=10.0)
        m = res.metrics
        sizing[label] = {"risk_per_trade": risk, "metrics": m.as_row(), "curve": m.equity_curve}
    deep["sizing_sweep"] = sizing
    deep["good_config"] = good.__dict__.copy()

    # Distribuição de retornos por trade da config-base (para histograma).
    base_res = run_daily_strategy(df, volume_exhaustion_signals, good, cost_model=cm,
                                  cache_key="SPY")
    deep["flagship_trade_returns"] = [t.return_pct for t in base_res.trades]
    deep["flagship_curve"] = base_res.metrics.equity_curve
    deep["flagship_metrics"] = base_res.metrics.as_row()

    # Perfis de PARÂMETRO conservador vs agressivo (ambos long-only, risco 1%).
    param_profiles = {
        "Conservador (stop largo, VA 0,80)": DailyParams(
            window=20, stop_atr_mult=3.0, target_atr_mult=3.0, max_holding_days=10,
            volume_mult=1.0, allow_long=True, allow_short=False, trend_filter=False),
        "Agressivo (stop curto, alvo 5xATR)": DailyParams(
            window=20, stop_atr_mult=1.5, target_atr_mult=5.0, max_holding_days=20,
            volume_mult=1.0, allow_long=True, allow_short=False, trend_filter=False),
    }
    pprof = {}
    for name, p in param_profiles.items():
        m = run_daily_strategy(df, volume_exhaustion_signals, p, cost_model=cm,
                               cache_key="SPY").metrics
        pprof[name] = {"params": p.__dict__.copy(), "metrics": m.as_row(), "curve": m.equity_curve}
    deep["param_profiles"] = pprof
    return deep


def build_portfolio(wf_out: dict) -> dict:
    """Portfólio diversificado: para cada instrumento, usa a melhor estratégia long OOS."""
    best_sleeves = {}
    for tk in INSTRUMENTS:
        best = None
        for sname in STRATEGIES:
            m = wf_out[sname][tk]["oos_metrics"]
            score = m["expectancy_r"] * (m["n_trades"] ** 0.5) if m["n_trades"] >= 15 else -1e9
            if best is None or score > best[0]:
                best = (score, sname, wf_out[sname][tk]["oos_daily_returns"], m)
        best_sleeves[tk] = best

    sleeves_all = {f"{tk}:{b[1]}": b[2] for tk, b in best_sleeves.items() if len(b[2])}
    sleeves_pos = {
        f"{tk}:{b[1]}": b[2]
        for tk, b in best_sleeves.items()
        if len(b[2]) and b[3]["expectancy_r"] > 0
    }

    out = {"chosen": {tk: b[1] for tk, b in best_sleeves.items()}}
    for label, sleeves in [("todos", sleeves_all), ("apenas_positivos_OOS", sleeves_pos)]:
        if not sleeves:
            continue
        ret = combine_portfolio_returns(sleeves)
        m = compute_metrics([], daily_returns=ret)
        out[label] = {
            "sleeves": list(sleeves.keys()),
            "curve": (1 + ret).cumprod(),
            "metrics": m.as_row(),
            "exposure_pct": float((ret != 0).mean()),
            "daily_returns": ret,
        }

    # Sweep de alavancagem sobre o portfólio só-positivos (eixo conservador -> agressivo).
    if "apenas_positivos_OOS" in out:
        base_ret = out["apenas_positivos_OOS"]["daily_returns"]
        lev_sweep = {}
        for lev in [1.0, 2.0, 3.0, 5.0]:
            m = compute_metrics([], daily_returns=base_ret * lev)
            lev_sweep[f"{lev:.0f}x"] = {
                "leverage": lev,
                "metrics": m.as_row(),
                "curve": (1 + base_ret * lev).cumprod(),
            }
        out["leverage_sweep"] = lev_sweep
    return out


def run_rule80(results: dict) -> dict:
    out = {}
    for tk, inst in INSTRUMENTS.items():
        df30 = load_intraday(tk, interval="30m")
        cm = COST_MODELS[inst.market]
        res = backtest_rule80(df30, cost_model=cm, p=Rule80Params())
        out[tk] = {
            "metrics": res.metrics.as_row(),
            "diagnostics": rule80_diagnostics(res.trades),
            "n_sessions": int(df30.index.normalize().nunique()),
        }
    return out


def run_studies(results: dict) -> dict:
    day_type = {}
    divergence = {}
    for tk in INSTRUMENTS:
        df = load_daily(tk)
        dt = day_type_forward_returns(df)
        dt.to_csv(DATA_OUT / f"daytype_{tk.replace('.', '_')}.csv", index=False)
        day_type[tk] = dt
        divergence[tk] = volume_divergence_study(df)
    return {"day_type": day_type, "divergence": divergence}


def cost_sensitivity() -> pd.DataFrame:
    """Como a expectância da EXH long em SPY varia com o nível de custo."""
    df = load_daily("SPY")
    p = DailyParams(window=20, stop_atr_mult=2.0, target_atr_mult=3.0, max_holding_days=10,
                    allow_long=True, allow_short=False, trend_filter=False)
    rows = []
    for slip in [0.0, 0.0005, 0.001, 0.002, 0.004]:
        cm = CostModel(commission_pct=0.0, exchange_fee_pct=0.00003, slippage_pct=slip)
        m = run_daily_strategy(df, volume_exhaustion_signals, p, cost_model=cm, cache_key="SPY").metrics
        rows.append({"slippage_pct": slip, "round_trip_cost_pct": cm.round_trip_pct(),
                     "expectancy_pct": m.expectancy_pct, "profit_factor": m.profit_factor,
                     "cagr_pct": m.cagr_pct, "n_trades": m.n_trades})
    return pd.DataFrame(rows)


def complementary_studies() -> dict:
    """Estudos complementares: leituras de volume §6, signal candle §7 e resolução §4.3."""
    out: dict = {}

    # §6 — leituras de volume "cru" (movimento saudável, absorção) por instrumento.
    out["volume_events"] = {tk: volume_event_study(load_daily(tk)) for tk in INSTRUMENTS}

    # §7 — efeito do "signal candle" (confirmação por volume) na Edge-to-Edge.
    conf = {}
    for tk in ["SPY", "QQQ"]:
        df = load_daily(tk)
        cm = COST_MODELS[INSTRUMENTS[tk].market]
        rows = []
        for vm in [0.0, 1.2, 1.5, 2.0]:
            p = DailyParams(window=60, stop_atr_mult=1.5, max_holding_days=15,
                            allow_long=True, allow_short=False, trend_filter=True, volume_mult=vm)
            m = run_daily_strategy(df, edge_to_edge_signals, p, cost_model=cm, cache_key=tk).metrics
            rows.append({"volume_mult": vm, "n_trades": m.n_trades, "win_rate": m.win_rate,
                         "expectancy_pct": m.expectancy_pct, "profit_factor": m.profit_factor})
        conf[tk] = pd.DataFrame(rows)
    out["signal_candle"] = conf

    # §4.3 — robustez à resolução do histograma (nº de "rows").
    df = load_daily("SPY")
    cm = COST_MODELS["US"]
    rows = []
    for nb in [40, 80, 160, 400]:
        p = DailyParams(window=60, n_bins=nb, stop_atr_mult=1.5, max_holding_days=15,
                        allow_long=True, allow_short=False, trend_filter=True)
        m = run_daily_strategy(df, edge_to_edge_signals, p, cost_model=cm,
                               cache_key=f"SPY_nb{nb}").metrics
        rows.append({"n_bins": nb, "n_trades": m.n_trades, "expectancy_pct": m.expectancy_pct,
                     "profit_factor": m.profit_factor, "cagr_pct": m.cagr_pct})
    out["resolution"] = pd.DataFrame(rows)
    return out


def sample_profile() -> dict:
    """Perfil de volume composite recente do SPY (para o gráfico educativo)."""
    df = load_daily("SPY").iloc[-120:]
    prof = build_volume_profile(df["High"].to_numpy(), df["Low"].to_numpy(),
                                df["Volume"].to_numpy(), n_bins=80, value_area_pct=0.70)
    return {
        "ticker": "SPY",
        "start": df.index[0],
        "end": df.index[-1],
        "price": df["Close"],
        "bin_centers": prof.bin_centers,
        "bin_volumes": prof.bin_volumes,
        "poc": prof.poc,
        "vah": prof.vah,
        "val": prof.val,
        "hvn": prof.hvn_prices,
        "lvn": prof.lvn_prices,
    }


def main():
    t0 = time.time()
    results: dict = {"meta": {"generated_for": "Pedro", "instruments": dict(
        (tk, {"name": i.name, "market": i.market, "currency": i.currency})
        for tk, i in INSTRUMENTS.items())}}

    print("[1/9] Buy & hold + dados por instrumento...")
    results["instruments"] = {}
    for tk, inst in INSTRUMENTS.items():
        df = load_daily(tk)
        bh = buyhold(df)
        results["instruments"][tk] = {
            "name": inst.name, "market": inst.market, "currency": inst.currency,
            "start": df.index[0], "end": df.index[-1], "n_days": len(df),
            "buyhold": bh, "price": df["Close"],
        }

    print("[2/9] Matriz cross-section (estratégia × instrumento × direção)...")
    cs = cross_section(results)
    cs.to_csv(DATA_OUT / "cross_section.csv", index=False)
    results["cross_section"] = cs

    print("[3/9] Walk-forward OOS (pode levar alguns minutos)...")
    results["walkforward"] = run_walkforward(results)

    print("[4/9] Deep-dive do carro-chefe + perfis conservador/agressivo...")
    results["flagship"] = flagship_deepdive(results)

    print("[5/9] Portfólio diversificado...")
    results["portfolio"] = build_portfolio(results["walkforward"])

    print("[6/9] Regra dos 80% (intraday 30m)...")
    results["rule80"] = run_rule80(results)

    print("[7/9] Estudos (day-type, divergência)...")
    results["studies"] = run_studies(results)

    print("[8/9] Sensibilidade a custos...")
    cstab = cost_sensitivity()
    cstab.to_csv(DATA_OUT / "cost_sensitivity.csv", index=False)
    results["cost_sensitivity"] = cstab

    print("[9/10] Estudos complementares (§4.3, §6, §7)...")
    results["complementary"] = complementary_studies()

    print("[10/10] Perfil de volume de exemplo...")
    results["sample_profile"] = sample_profile()

    with open(OUT / "results.pkl", "wb") as f:
        pickle.dump(results, f)
    print(f"OK -> {OUT / 'results.pkl'}  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()

"""Roda a suíte de falsificação/ablação do sleeve de Exaustão de volume.

Config FIXA (não reotimizada) para validar o teste de permutação. Salva output/falsification.pkl.
"""

from __future__ import annotations

import pickle
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from vptrading.analysis.falsification import run_suite  # noqa: E402
from vptrading.backtest.costs import COST_MODELS  # noqa: E402
from vptrading.data import INSTRUMENTS, load_daily  # noqa: E402
from vptrading.strategies.daily import DailyParams  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "output"

# Config fixa do sleeve de Exaustão (a validada como robusta): long-only, sem reotimização.
FIXED = DailyParams(window=20, stop_atr_mult=2.0, target_atr_mult=3.0, max_holding_days=10,
                    volume_mult=1.0, allow_long=True, allow_short=False, trend_filter=False)


def main():
    t0 = time.time()
    print("Rodando suíte de falsificação (permutações 500, bootstrap 10k)...")
    results = run_suite(INSTRUMENTS, load_daily, COST_MODELS, FIXED, n_perm=500, n_boot=10000)
    with open(OUT / "falsification.pkl", "wb") as f:
        pickle.dump(results, f)

    print(f"\n=== TABELA-VEREDITO ({time.time() - t0:.0f}s) ===")
    cols = ["shuffle", "só-preço", "long-aleat", "alfa-expo", "risk-free", "IC>1", "TODOS"]
    print(f"{'Ativo':10} " + " ".join(f"{c:>10}" for c in cols))
    for tk, d in results["sleeves"].items():
        v = d["verdict"]
        vals = [v["sobrevive_shuffle"], v["bate_so_preco"], v["bate_long_aleatorio"],
                v["alfa_sobre_exposicao"], v["bate_risk_free"], v["ic_pf_exclui_1"], v["passa_todos"]]
        print(f"{tk:10} " + " ".join(f"{'SIM' if x else 'não':>10}" for x in vals))
    print(f"\nSalvo -> {OUT / 'falsification.pkl'}")


if __name__ == "__main__":
    main()

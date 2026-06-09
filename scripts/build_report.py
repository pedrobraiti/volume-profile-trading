"""Gera as figuras e o relatório PDF a partir de ``output/results.pkl``."""

from __future__ import annotations

import pickle
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from vptrading.reporting.charts import (  # noqa: E402
    generate_all_figures,
    generate_falsification_figures,
)
from vptrading.reporting.pdf_report import build_report  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "output"


def main():
    with open(OUT / "results.pkl", "rb") as f:
        results = pickle.load(f)
    figdir = OUT / "figures"
    generate_all_figures(results, figdir)

    # Inclui a seção de falsificação se o pickle existir (scripts/run_falsification.py).
    fals_path = OUT / "falsification.pkl"
    if fals_path.exists():
        with open(fals_path, "rb") as f:
            results["falsification"] = pickle.load(f)
        generate_falsification_figures(results["falsification"], figdir)

    pdf = build_report(results, figdir, OUT / "relatorio_volume_profile.pdf")
    print(f"Relatório gerado: {pdf}")


if __name__ == "__main__":
    main()

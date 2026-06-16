"""Generates the figures and the PDF report from ``output/results.pkl``."""

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

    # Include the falsification section if the pickle exists (scripts/run_falsification.py).
    fals_path = OUT / "falsification.pkl"
    if fals_path.exists():
        with open(fals_path, "rb") as f:
            results["falsification"] = pickle.load(f)
        generate_falsification_figures(results["falsification"], figdir)

    pdf = build_report(results, figdir, OUT / "volume_profile_study.pdf")
    print(f"Report generated: {pdf}")


if __name__ == "__main__":
    main()

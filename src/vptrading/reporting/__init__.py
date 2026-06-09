"""Geração de gráficos e do relatório PDF."""

from vptrading.reporting.charts import generate_all_figures
from vptrading.reporting.pdf_report import build_report

__all__ = ["generate_all_figures", "build_report"]

"""Modelos de custo de transação por mercado.

Custo total por trade = (comissão + emolumentos) sobre o notional + slippage de entrada e saída.
O slippage é modelado como uma fração do preço (proxy de spread + impacto), aplicada nas duas
pontas. Valores default são realistas para varejo atual; documentados no relatório e ajustáveis.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """Custos de transação de ida e volta (round-trip)."""

    commission_pct: float   # comissão proporcional ao notional, por ponta
    exchange_fee_pct: float  # emolumentos/taxas de bolsa, por ponta
    slippage_pct: float      # slippage estimado, por ponta

    def per_side_pct(self) -> float:
        return self.commission_pct + self.exchange_fee_pct + self.slippage_pct

    def round_trip_pct(self) -> float:
        """Custo total estimado de entrada + saída, como fração do preço."""
        return 2.0 * self.per_side_pct()


# Mercado US (ETFs como SPY/QQQ): corretagem zero no varejo moderno; spread mínimo + slippage leve.
COST_US = CostModel(commission_pct=0.0, exchange_fee_pct=0.00003, slippage_pct=0.0005)

# Mercado BR (B3): corretagem ~zero no varejo atual; emolumentos B3 ~0.03%; slippage maior.
COST_BR = CostModel(commission_pct=0.0, exchange_fee_pct=0.0003, slippage_pct=0.0010)

COST_MODELS: dict[str, CostModel] = {"US": COST_US, "BR": COST_BR}

"""Per-market transaction cost models.

Total cost per trade = (commission + exchange fee) on the notional + entry and exit slippage.
Slippage is modeled as a fraction of price (a proxy for spread + impact), applied on both
sides. Default values are realistic for current retail trading; documented in the report and adjustable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """Round-trip transaction costs."""

    commission_pct: float   # commission proportional to the notional, per side
    exchange_fee_pct: float  # exchange fees/charges, per side
    slippage_pct: float      # estimated slippage, per side

    def per_side_pct(self) -> float:
        return self.commission_pct + self.exchange_fee_pct + self.slippage_pct

    def round_trip_pct(self) -> float:
        """Estimated total entry + exit cost, as a fraction of price."""
        return 2.0 * self.per_side_pct()


# US market (ETFs such as SPY/QQQ): zero commission in modern retail; minimal spread + light slippage.
COST_US = CostModel(commission_pct=0.0, exchange_fee_pct=0.00003, slippage_pct=0.0005)

# BR market (B3): ~zero commission in current retail; B3 exchange fees ~0.03%; higher slippage.
COST_BR = CostModel(commission_pct=0.0, exchange_fee_pct=0.0003, slippage_pct=0.0010)

COST_MODELS: dict[str, CostModel] = {"US": COST_US, "BR": COST_BR}

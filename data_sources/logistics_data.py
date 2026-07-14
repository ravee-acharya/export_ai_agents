"""
Mock logistics/freight data per destination country. Stand-in for a
real freight-rate/transit-time API (e.g. Freightos, a forwarder's rate
sheet) until one is integrated. Deterministic, no LLM needed — this is
a lookup-and-compute job like Demand Signal and Scheme/Compliance.
"""

# sea_transit_days: typical door-to-port transit time by sea from India
# freight_cost_usd_per_kg: blended sea+inland freight cost estimate
# customs_complexity: 0 (simple) - 1 (complex), based on documentation
#   burden, inspection rates, and de minimis thresholds
_LOGISTICS_DATA = {
    "US": {"sea_transit_days": 28, "freight_cost_usd_per_kg": 0.85, "customs_complexity": 0.5},
    "DE": {"sea_transit_days": 24, "freight_cost_usd_per_kg": 0.75, "customs_complexity": 0.6},
    "GB": {"sea_transit_days": 26, "freight_cost_usd_per_kg": 0.80, "customs_complexity": 0.6},
    "CA": {"sea_transit_days": 32, "freight_cost_usd_per_kg": 0.95, "customs_complexity": 0.5},
    "AU": {"sea_transit_days": 18, "freight_cost_usd_per_kg": 0.70, "customs_complexity": 0.4},
    "AE": {"sea_transit_days": 10, "freight_cost_usd_per_kg": 0.45, "customs_complexity": 0.3},
    "SG": {"sea_transit_days": 8, "freight_cost_usd_per_kg": 0.40, "customs_complexity": 0.2},
}

# Used when a country isn't in the table above.
_DEFAULT_LOGISTICS = {
    "sea_transit_days": 30,
    "freight_cost_usd_per_kg": 1.00,
    "customs_complexity": 0.6,
}


def get_logistics_data(country: str) -> dict:
    return _LOGISTICS_DATA.get(country.upper(), _DEFAULT_LOGISTICS)

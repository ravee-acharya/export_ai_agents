"""
Mock trade data source.

Stands in for a real customs/import data API (UN Comtrade, ImportGenius,
Panjiva, etc.) so the Demand Signal Agent can be built and tested without
a paid API subscription. The response shape mirrors what a real trade
data API typically returns: monthly import volumes by HS code and
destination country, which the agent then turns into growth rates and
surge flags.

To go live: replace `fetch_import_data()` with a real HTTP client call,
keep the return shape identical, and nothing else in the agent changes.
"""

import random
from datetime import date, timedelta
from typing import TypedDict


class MonthlyVolume(TypedDict):
    month: str
    volume_usd: float


class ImportDataResponse(TypedDict):
    hs_code: str
    destination_country: str
    sector: str
    monthly_volumes: list[MonthlyVolume]
    active_indian_suppliers: int
    data_source: str
    as_of: str


# Seed data seeded from the deck's textiles example: US home textiles,
# HS 6302, 23% MoM surge, 6 active Indian exporters serving this demand.
_SEED_PROFILES = {
    ("6302", "US"): {
        "base_volume": 4_200_000,
        "monthly_growth": 0.23,
        "active_suppliers": 6,
        "surge": True,
    },
    ("5911", "EU"): {
        "base_volume": 1_800_000,
        "monthly_growth": 0.09,
        "active_suppliers": 14,
        "surge": False,
    },
    ("6204", "UAE"): {
        "base_volume": 950_000,
        "monthly_growth": 0.14,
        "active_suppliers": 4,
        "surge": True,
    },
    ("6006", "JP"): {
        "base_volume": 600_000,
        "monthly_growth": 0.06,
        "active_suppliers": 9,
        "surge": False,
    },
}

_DEFAULT_PROFILE = {
    "base_volume": 1_000_000,
    "monthly_growth": 0.05,
    "active_suppliers": 10,
    "surge": False,
}


def fetch_import_data(
    hs_code: str,
    destination_country: str,
    sector: str,
    lookback_months: int = 6,
) -> ImportDataResponse:
    """
    Simulates fetching monthly import volume data for a given HS code
    and destination country over the lookback period.

    In production this becomes an authenticated HTTP call to a real
    trade data provider. The function signature and return shape are
    designed to stay stable across that swap.
    """
    profile = _SEED_PROFILES.get(
        (hs_code, destination_country.upper()), _DEFAULT_PROFILE
    )

    rng = random.Random(f"{hs_code}-{destination_country}-{sector}")

    volumes: list[MonthlyVolume] = []
    volume = profile["base_volume"] / (
        (1 + profile["monthly_growth"]) ** lookback_months
    )
    today = date.today()

    for i in range(lookback_months, 0, -1):
        month_date = today - timedelta(days=30 * i)
        noise = rng.uniform(-0.04, 0.04)
        growth_rate = profile["monthly_growth"] + noise
        volume = volume * (1 + growth_rate)
        volumes.append(
            {
                "month": month_date.strftime("%Y-%m"),
                "volume_usd": round(volume, 2),
            }
        )

    return {
        "hs_code": hs_code,
        "destination_country": destination_country.upper(),
        "sector": sector,
        "monthly_volumes": volumes,
        "active_indian_suppliers": profile["active_suppliers"],
        "data_source": "mock_trade_api (replace with real provider)",
        "as_of": today.isoformat(),
    }

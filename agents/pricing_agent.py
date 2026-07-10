"""
Pricing Agent

Version 1 (Mock)

This agent estimates export pricing until live trade-price
sources are integrated.
"""

from dataclasses import dataclass


@dataclass
class PricingSignal:

    hs_code: str
    destination_country: str

    average_import_price: float
    average_indian_export_price: float
    estimated_retail_price: float

    recommended_fob_price: float

    expected_margin_pct: float

    competitiveness_score: float


@dataclass
class PricingAgentOutput:

    pricing: list[PricingSignal]


# ------------------------------------------------------------------
# Mock pricing data
# ------------------------------------------------------------------

MOCK_DATA = {

    "6302": {
        "US": (8.60, 6.10, 22.40),
        "DE": (8.20, 6.00, 20.10),
        "CA": (8.10, 5.90, 19.30),
        "AU": (8.30, 6.20, 20.90),
        "AE": (7.60, 5.70, 18.20),
    },

    "5911": {
        "US": (17.5, 14.2, 42.0),
        "DE": (16.8, 13.9, 40.1),
    },

    "6204": {
        "US": (15.6, 11.8, 37.0),
        "DE": (14.9, 11.2, 35.5),
    }

}


def run_pricing_agent(
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
):

    output = []

    for hs in hs_codes:

        if hs not in MOCK_DATA:
            continue

        for country in target_countries:

            if country not in MOCK_DATA[hs]:
                continue

            import_price, indian_price, retail = MOCK_DATA[hs][country]

            fob = round(indian_price * 1.08, 2)

            margin = round(
                ((fob - indian_price) / indian_price) * 100,
                1,
            )

            competitiveness = round(
                (import_price / fob) * 10,
                1,
            )

            output.append(

                PricingSignal(

                    hs_code=hs,

                    destination_country=country,

                    average_import_price=import_price,

                    average_indian_export_price=indian_price,

                    estimated_retail_price=retail,

                    recommended_fob_price=fob,

                    expected_margin_pct=margin,

                    competitiveness_score=min(
                        competitiveness,
                        10.0,
                    ),

                )

            )

    return PricingAgentOutput(
        pricing=output
    )
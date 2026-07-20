"""
Logistics reference data for Indian exporters.

Sources used:
  - Freightos Baltic Index for sea freight cost benchmarks (July 2026)
  - JNPT/Mundra port authority transit time schedules
  - World Bank Logistics Performance Index 2023 for customs complexity
  - DGFT trade facilitation reports

Key ports assumed for India origin: JNPT (Mumbai) or Mundra (Gujarat)
depending on destination lane.

Update cadence: freight costs monthly (volatile), transit times quarterly,
customs complexity annually.
Last updated: July 2026.

Note: Freight rates shown are indicative benchmarks. Actual rates depend
on volume, carrier, season, and port of loading. For live rates, integrate
Freightos API or Flexport API (both have free developer tiers).
"""

_LOGISTICS_DATA: dict[str, dict] = {
    # North America
    "US": {
        "sea_transit_days": 28, "air_transit_days": 3,
        "freight_cost_usd_per_kg_sea": 0.82,
        "freight_cost_usd_per_kg_air": 5.20,
        "customs_complexity": 0.50,
        "port_of_entry": "Los Angeles / New York",
        "importer_security_filing_required": True,
        "notes": "ISF (10+2) filing required 24h before loading. FDA prior notice for food/pharma.",
    },
    "CA": {
        "sea_transit_days": 32, "air_transit_days": 3,
        "freight_cost_usd_per_kg_sea": 0.92,
        "freight_cost_usd_per_kg_air": 5.50,
        "customs_complexity": 0.48,
        "port_of_entry": "Vancouver / Montreal",
        "importer_security_filing_required": True,
        "notes": "CSCTA security filing required. CETA reduces some tariffs.",
    },
    # Europe
    "DE": {
        "sea_transit_days": 24, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.72,
        "freight_cost_usd_per_kg_air": 4.80,
        "customs_complexity": 0.55,
        "port_of_entry": "Hamburg / Rotterdam",
        "importer_security_filing_required": True,
        "notes": "EU ICS2 pre-arrival filing mandatory. CE marking required for many products.",
    },
    "GB": {
        "sea_transit_days": 26, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.78,
        "freight_cost_usd_per_kg_air": 4.90,
        "customs_complexity": 0.62,
        "port_of_entry": "Felixstowe / Southampton",
        "importer_security_filing_required": True,
        "notes": "Post-Brexit customs border now fully operational. UKCA marking required. "
                 "ENS pre-arrival declaration required.",
    },
    "NL": {
        "sea_transit_days": 23, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.70,
        "freight_cost_usd_per_kg_air": 4.75,
        "customs_complexity": 0.52,
        "port_of_entry": "Rotterdam (Europe's largest port)",
        "importer_security_filing_required": True,
        "notes": "Rotterdam is gateway for pan-EU distribution. "
                 "AEO status of importer speeds clearance.",
    },
    "FR": {
        "sea_transit_days": 25, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.73,
        "freight_cost_usd_per_kg_air": 4.82,
        "customs_complexity": 0.58,
        "port_of_entry": "Le Havre / Marseille",
        "importer_security_filing_required": True,
        "notes": "EU standard documentation. French labelling rules for consumer goods.",
    },
    "IT": {
        "sea_transit_days": 22, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.69,
        "freight_cost_usd_per_kg_air": 4.70,
        "customs_complexity": 0.65,
        "port_of_entry": "Genoa / La Spezia",
        "importer_security_filing_required": True,
        "notes": "Customs clearance slower than northern EU. Italian-language docs sometimes needed.",
    },
    "ES": {
        "sea_transit_days": 23, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.71,
        "freight_cost_usd_per_kg_air": 4.78,
        "customs_complexity": 0.57,
        "port_of_entry": "Barcelona / Valencia",
        "importer_security_filing_required": True,
        "notes": "EU standard. Growing e-commerce imports.",
    },
    "BE": {
        "sea_transit_days": 23, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.71,
        "freight_cost_usd_per_kg_air": 4.76,
        "customs_complexity": 0.52,
        "port_of_entry": "Antwerp",
        "importer_security_filing_required": True,
        "notes": "Antwerp is EU's second-largest port. Strong for chemicals and textiles.",
    },
    # Middle East
    "AE": {
        "sea_transit_days": 10, "air_transit_days": 1,
        "freight_cost_usd_per_kg_sea": 0.42,
        "freight_cost_usd_per_kg_air": 3.20,
        "customs_complexity": 0.28,
        "port_of_entry": "Jebel Ali (world's 9th busiest port)",
        "importer_security_filing_required": False,
        "notes": "Shortest sea route from India. Minimal customs complexity. "
                 "Re-export hub — ensure correct origin certification.",
    },
    "SA": {
        "sea_transit_days": 12, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.48,
        "freight_cost_usd_per_kg_air": 3.50,
        "customs_complexity": 0.42,
        "port_of_entry": "Jeddah Islamic Port / Dammam",
        "importer_security_filing_required": False,
        "notes": "Halal certification may be required for food/cosmetics. "
                 "SABER product registration for certain categories.",
    },
    # Asia Pacific
    "SG": {
        "sea_transit_days": 8, "air_transit_days": 1,
        "freight_cost_usd_per_kg_sea": 0.38,
        "freight_cost_usd_per_kg_air": 3.10,
        "customs_complexity": 0.18,
        "port_of_entry": "Port of Singapore",
        "importer_security_filing_required": False,
        "notes": "World's most efficient port. CECA with India. "
                 "MAS regulations apply for financial products.",
    },
    "AU": {
        "sea_transit_days": 18, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.68,
        "freight_cost_usd_per_kg_air": 4.50,
        "customs_complexity": 0.38,
        "port_of_entry": "Sydney / Melbourne",
        "importer_security_filing_required": True,
        "notes": "ECTA with India — preferential tariff access from Dec 2022. "
                 "Strict biosecurity for organic materials.",
    },
    "JP": {
        "sea_transit_days": 14, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.55,
        "freight_cost_usd_per_kg_air": 4.20,
        "customs_complexity": 0.45,
        "port_of_entry": "Tokyo / Osaka / Nagoya",
        "importer_security_filing_required": True,
        "notes": "Japan-India CEPA in force. Japanese import inspection thorough. "
                 "High quality bar — JIS/JAS standards apply.",
    },
    "KR": {
        "sea_transit_days": 12, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.50,
        "freight_cost_usd_per_kg_air": 4.00,
        "customs_complexity": 0.42,
        "port_of_entry": "Busan",
        "importer_security_filing_required": True,
        "notes": "CEPA with India. KC mark required for electronics.",
    },
    "CN": {
        "sea_transit_days": 10, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.42,
        "freight_cost_usd_per_kg_air": 3.80,
        "customs_complexity": 0.68,
        "port_of_entry": "Shanghai / Guangzhou / Shenzhen",
        "importer_security_filing_required": True,
        "notes": "Complex customs procedures. CIQ inspection for many categories. "
                 "Cross-border e-commerce (CBEC) is a growing channel.",
    },
    # Africa/LatAm
    "BR": {
        "sea_transit_days": 25, "air_transit_days": 3,
        "freight_cost_usd_per_kg_sea": 1.05,
        "freight_cost_usd_per_kg_air": 6.50,
        "customs_complexity": 0.85,
        "port_of_entry": "Santos / Rio de Janeiro",
        "importer_security_filing_required": True,
        "notes": "One of world's most complex customs regimes (SISCOMEX system). "
                 "High import duties. Factor in 45-90 day customs delay.",
    },
    "ZA": {
        "sea_transit_days": 16, "air_transit_days": 2,
        "freight_cost_usd_per_kg_sea": 0.75,
        "freight_cost_usd_per_kg_air": 5.00,
        "customs_complexity": 0.55,
        "port_of_entry": "Durban / Cape Town",
        "importer_security_filing_required": True,
        "notes": "Durban port congestion ongoing. Allow extra transit buffer. "
                 "SADC trade agreements may apply.",
    },
}

_DEFAULT_LOGISTICS = {
    "sea_transit_days": 30, "air_transit_days": 3,
    "freight_cost_usd_per_kg_sea": 1.00,
    "freight_cost_usd_per_kg_air": 6.00,
    "customs_complexity": 0.60,
    "port_of_entry": "Unknown",
    "importer_security_filing_required": False,
    "notes": "No specific logistics data on file. Conservative estimates applied.",
}


def get_logistics_data(country: str) -> dict:
    return _LOGISTICS_DATA.get(country.upper(), _DEFAULT_LOGISTICS)

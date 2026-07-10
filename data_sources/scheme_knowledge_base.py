"""
Government scheme knowledge base.

Static reference data on Indian export-promotion schemes, eligibility
rules, and compliance requirements. Unlike trade demand data, this
doesn't change daily — it's appropriate to hand-curate and update
quarterly/on-policy-change rather than fetch from a live API, which is
why the Scheme/Compliance Agent built on top of this is cheap to run
(no per-call data cost) compared to the Demand Signal Agent.

To go live with fresher data: this could later be backed by a
periodically-scraped DGFT/Udyam source, but the interface to the agent
stays the same.
"""

from typing import TypedDict


class SchemeEligibility(TypedDict):
    max_revenue_cr: float | None  # None = no upper limit
    min_revenue_cr: float  # 0 = no lower limit
    sectors: list[str]  # empty list = all sectors
    requires_udyam_registration: bool


class Scheme(TypedDict):
    scheme_id: str
    name: str
    issuing_body: str
    benefit_summary: str
    eligibility: SchemeEligibility
    application_notes: str


SCHEMES: list[Scheme] = [
    {
        "scheme_id": "PLI_TEXTILES",
        "name": "Production Linked Incentive (PLI) Scheme for Textiles",
        "issuing_body": "Ministry of Textiles",
        "benefit_summary": "Incentive payouts of 3-7% on incremental turnover "
        "for man-made fiber apparel, fabrics, and technical textiles, paid "
        "over 5 years to manufacturers meeting investment thresholds.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": ["textiles"],
            "requires_udyam_registration": False,
        },
        "application_notes": "Requires minimum investment commitment "
        "(Rs 100 Cr for large category, Rs 25 Cr for MMF apparel/technical "
        "textiles category). Apply via Ministry of Textiles PLI portal.",
    },
    {
        "scheme_id": "EEPC_MEMBERSHIP",
        "name": "EEPC India Membership and Market Access Support",
        "issuing_body": "Engineering Export Promotion Council (EEPC)",
        "benefit_summary": "Market intelligence, buyer-seller meets, trade "
        "fair subsidies, and export documentation support for engineering "
        "goods exporters.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": ["engineering"],
            "requires_udyam_registration": False,
        },
        "application_notes": "Annual membership fee scaled by export "
        "turnover. Apply directly via eepcindia.org.",
    },
    {
        "scheme_id": "MEIS_RODTEP",
        "name": "Remission of Duties and Taxes on Exported Products (RoDTEP)",
        "issuing_body": "Directorate General of Foreign Trade (DGFT)",
        "benefit_summary": "Refund of embedded duties/taxes not refunded "
        "under other mechanisms, credited as transferable scrips, "
        "applicable across most export sectors.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": [],  # all sectors
            "requires_udyam_registration": False,
        },
        "application_notes": "Claimed automatically via shipping bill at "
        "time of export through ICEGATE; rates vary by HS code.",
    },
    {
        "scheme_id": "SIDBI_EXPORT_CREDIT",
        "name": "SIDBI Export Credit and Working Capital Support",
        "issuing_body": "Small Industries Development Bank of India (SIDBI)",
        "benefit_summary": "Pre- and post-shipment export credit at "
        "concessional rates, plus working capital support for first-time "
        "exporters.",
        "eligibility": {
            "max_revenue_cr": 250,
            "min_revenue_cr": 0,
            "sectors": [],
            "requires_udyam_registration": True,
        },
        "application_notes": "Requires Udyam registration. Apply through "
        "SIDBI branch or empanelled bank partner.",
    },
    {
        "scheme_id": "MARKET_ACCESS_INITIATIVE",
        "name": "Market Access Initiative (MAI) Scheme",
        "issuing_body": "Department of Commerce",
        "benefit_summary": "Financial assistance for export promotion "
        "activities — trade fairs, buyer-seller meets, market studies — "
        "for export promotion councils and individual exporters in "
        "focus sectors.",
        "eligibility": {
            "max_revenue_cr": 50,
            "min_revenue_cr": 0,
            "sectors": ["textiles", "engineering", "chemicals", "agri"],
            "requires_udyam_registration": True,
        },
        "application_notes": "Apply via the relevant Export Promotion "
        "Council; co-funding ratio depends on category of assistance.",
    },
    {
        "scheme_id": "AGRI_EXPORT_POLICY",
        "name": "Agriculture Export Policy — Cluster-Based Support",
        "issuing_body": "APEDA (Agricultural and Processed Food Products "
        "Export Development Authority)",
        "benefit_summary": "Infrastructure and certification cost support "
        "for agri-export clusters, including cold chain and packaging "
        "subsidies.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": ["agri"],
            "requires_udyam_registration": False,
        },
        "application_notes": "Apply via APEDA registration; cluster-level "
        "applications often have higher approval priority than individual.",
    },
    {
        "scheme_id": "INDIA_UAE_CEPA",
        "name": "India-UAE Comprehensive Economic Partnership Agreement (CEPA)",
        "issuing_body": "Ministry of Commerce and Industry",
        "benefit_summary": "Preferential/zero tariffs on covered HS codes "
        "for exports to UAE, including most textiles and engineering "
        "goods categories.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": ["textiles", "engineering", "chemicals"],
            "requires_udyam_registration": False,
        },
        "application_notes": "Requires Certificate of Origin under CEPA "
        "rules of origin; apply via DGFT-authorized certifying agencies.",
    },
    {
        "scheme_id": "PLI_CHEMICALS",
        "name": "Production Linked Incentive (PLI) Scheme for Specialty Chemicals",
        "issuing_body": "Department of Chemicals and Petrochemicals",
        "benefit_summary": "Incentive on incremental sales for specialty "
        "chemical manufacturers reducing import dependency.",
        "eligibility": {
            "max_revenue_cr": None,
            "min_revenue_cr": 0,
            "sectors": ["chemicals"],
            "requires_udyam_registration": False,
        },
        "application_notes": "Investment threshold and product list vary by "
        "chemical sub-category; check current notified product list.",
    },
]


COMPLIANCE_REQUIREMENTS: dict[str, list[str]] = {
    "US": [
        "FDA registration (for textiles with treated/coated components)",
        "CPSIA compliance for children's products",
        "Customs bond for shipments above de minimis value",
    ],
    "EU": [
        "EUDR (deforestation-free supply chain) declaration where applicable",
        "REACH compliance for chemical content in textiles",
        "CE marking for relevant technical textile categories",
    ],
    "UAE": [
        "Certificate of Origin under India-UAE CEPA for preferential tariff",
        "UAE ESMA conformity marking for applicable product categories",
    ],
    "JP": [
        "Japan Industrial Standards (JIS) certification where applicable",
        "PSE marking for electrical/electronic components",
    ],
}


def get_schemes_for_sector(sector: str) -> list[Scheme]:
    """Returns all schemes applicable to a sector (sector-specific +
    sector-agnostic ones)."""
    return [
        s
        for s in SCHEMES
        if not s["eligibility"]["sectors"] or sector in s["eligibility"]["sectors"]
    ]


def get_compliance_requirements(country: str) -> list[str]:
    return COMPLIANCE_REQUIREMENTS.get(country.upper(), [])

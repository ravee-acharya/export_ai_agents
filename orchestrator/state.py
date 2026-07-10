"""
Shared state for the main orchestrator's LangGraph graph.
"""

from typing import Optional, TypedDict

from agents.demand_signal_agent import DemandSignalAgentOutput
from agents.scheme_compliance_agent import SchemeComplianceAgentOutput
from agents.pricing_agent import PricingAgentOutput


class OpportunityScore(TypedDict):
    hs_code: str
    destination_country: str
    score: float
    score_breakdown: dict
    note: str


class OrchestratorState(TypedDict, total=False):

    # -----------------------
    # Input
    # -----------------------

    query: str
    sector: str
    hs_codes: list[str]
    target_countries: list[str]

    sme_revenue_cr: Optional[float]
    has_udyam_registration: bool

    # -----------------------
    # Planner
    # -----------------------

    agents_to_call: list[str]

    # -----------------------
    # Agent Outputs
    # -----------------------

    demand_signal_output: Optional[
        DemandSignalAgentOutput
    ]

    scheme_compliance_output: Optional[
        SchemeComplianceAgentOutput
    ]

    pricing_output: Optional[
        PricingAgentOutput
    ]

    # Future

    # capability_gap_output
    # risk_output
    # logistics_output
    # market_output

    # -----------------------
    # Final Output
    # -----------------------

    opportunity_scores: list[
        OpportunityScore
    ]

    summary: str

    errors: list[str]
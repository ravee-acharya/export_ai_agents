"""
Shared state for the main orchestrator's LangGraph graph.
"""

from typing import Optional, TypedDict

from agents.demand_signal_agent import DemandSignalAgentOutput
from agents.scheme_compliance_agent import SchemeComplianceAgentOutput
from agents.pricing_agent import PricingAgentOutput
from agents.capability_gap_agent import CapabilityGapAgentOutput
from agents.logistics_agent import LogisticsAgentOutput
from agents.risk_agent import RiskAgentOutput
from agents.competitor_agent import CompetitorAgentOutput
from agents.buyer_discovery_agent import BuyerDiscoveryOutput
from agents.fta_agent import FTAAgentOutput
from agents.document_intelligence_agent import DocumentIntelligenceOutput
from agents.certification_agent import CertificationAgentOutput
from agents.rag_agent import RAGAgentOutput
from agents.forecast_agent import ForecastAgentOutput


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

    # Set by the planner when the person asked a market-discovery
    # question ("which markets should I target?") without naming any
    # country, so a default candidate list was substituted. The
    # synthesizer uses this to tell the person plainly that these
    # markets were chosen for them, not requested.
    markets_auto_selected: bool

    sme_revenue_cr: Optional[float]
    has_udyam_registration: bool
    sme_certifications: Optional[list[str]]

    # LLM provider selection, threaded through by the planner so
    # LLM-backed sub-agents (like Capability Gap) can access it without
    # every node needing it passed as a separate function argument.
    provider: Optional[str]

    # Prior-turn context injected by the memory layer (see
    # orchestrator/memory.py), so follow-up questions in the same
    # session can be answered with continuity. Empty string/absent for
    # the first turn in a session.
    conversation_context: Optional[str]

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

    capability_gap_output: Optional[
        CapabilityGapAgentOutput
    ]

    logistics_output: Optional[
        LogisticsAgentOutput
    ]

    risk_output: Optional[
        RiskAgentOutput
    ]

    competitor_output: Optional[
        CompetitorAgentOutput
    ]

    buyer_discovery_output: Optional[
        BuyerDiscoveryOutput
    ]

    fta_output: Optional[
        FTAAgentOutput
    ]

    document_intelligence_output: Optional[
        DocumentIntelligenceOutput
    ]

    certification_output: Optional[
        CertificationAgentOutput
    ]

    rag_output: Optional[
        RAGAgentOutput
    ]

    forecast_output: Optional[
        ForecastAgentOutput
    ]

    # -----------------------
    # Final Output
    # -----------------------

    opportunity_scores: list[
        OpportunityScore
    ]

    summary: str

    errors: list[str]
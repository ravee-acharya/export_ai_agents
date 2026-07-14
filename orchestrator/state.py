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

    # -----------------------
    # Final Output
    # -----------------------

    opportunity_scores: list[
        OpportunityScore
    ]

    summary: str

    errors: list[str]
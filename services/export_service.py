from orchestrator.main_agent import build_graph
from orchestrator.memory import ConversationMemory


class ExportService:

    def __init__(self, provider="gemini"):

        self.provider = provider
        self.graph = None
        # One ExportService instance is created per Streamlit session
        # (see app.py), so a single ConversationMemory instance here
        # naturally scopes history to that session -- no explicit
        # session_id needed for the current single-session-per-instance
        # usage pattern. If ExportService is ever reused across
        # multiple concurrent sessions, this would need a session_id
        # parameter threaded through instead.
        self.memory = ConversationMemory()
        self._session_id = "default"

    def _get_graph(self):

        if self.graph is None:
            self.graph = build_graph(provider=self.provider)

        return self.graph

    def analyze_query(self, query, certifications=None):

        graph = self._get_graph()

        conversation_context = self.memory.get_context_string(self._session_id)

        result = graph.invoke(
            {
                "query": query,
                "sme_certifications": certifications or [],
                "conversation_context": conversation_context,
            }
        )

        self.memory.add_turn(
            self._session_id,
            query=query,
            sector=result.get("sector"),
            target_countries=result.get("target_countries", []),
            summary=result.get("summary", ""),
        )

        return result

    def analyze_structured(
        self,
        sector,
        hs_codes,
        countries,
        revenue=40,
        udyam=True,
        certifications=None,
    ):

        graph = self._get_graph()

        conversation_context = self.memory.get_context_string(self._session_id)

        result = graph.invoke(
            {
                "sector": sector,
                "hs_codes": hs_codes,
                "target_countries": countries,
                "sme_revenue_cr": revenue,
                "has_udyam_registration": udyam,
                "sme_certifications": certifications or [],
                "conversation_context": conversation_context,
            }
        )

        self.memory.add_turn(
            self._session_id,
            query=f"[structured] sector={sector}, countries={countries}",
            sector=sector,
            target_countries=countries,
            summary=result.get("summary", ""),
        )

        return result

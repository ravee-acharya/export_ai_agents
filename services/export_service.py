import os

from orchestrator.main_agent import build_graph


class ExportService:

    def __init__(self, provider="gemini"):

        self.provider = provider
        self.graph = None

    def _get_graph(self):

        if self.graph is None:
            self.graph = build_graph(provider=self.provider)

        return self.graph

    def analyze_query(self, query):

        graph = self._get_graph()

        return graph.invoke(
            {
                "query": query
            }
        )

    def analyze_structured(
        self,
        sector,
        hs_codes,
        countries,
        revenue=40,
        udyam=True,
    ):

        graph = self._get_graph()

        return graph.invoke(
            {
                "sector": sector,
                "hs_codes": hs_codes,
                "target_countries": countries,
                "sme_revenue_cr": revenue,
                "has_udyam_registration": udyam,
            }
        )
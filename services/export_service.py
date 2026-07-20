"""
ExportService — HTTP client for the FastAPI backend.

In the prototype, ExportService ran the LangGraph orchestrator
directly in the Streamlit process. In Phase 6, it calls the FastAPI
backend over HTTP instead. This means:
  - Streamlit is a thin frontend — no agent code runs inside it
  - Session state is managed by the backend (Redis)
  - Multiple Streamlit instances share the same backend

Backwards compatibility: the same .analyze_query() and
.analyze_structured() interface is preserved, so app.py and all
other callers need zero changes.

Fallback: if API_BASE_URL is not set, falls back to the direct
in-process mode (original prototype behaviour) so local dev without
a running API server still works.
"""

import os
import uuid

import requests as _requests

_API_BASE = os.environ.get("API_BASE_URL", "").rstrip("/")
_TIMEOUT = 120  # seconds — agents can take a while


class ExportService:

    def __init__(self, provider: str = "openrouter"):
        self.provider = provider
        self._session_id = str(uuid.uuid4())
        self._graph = None

    def analyze_query(self, query: str, certifications: list | None = None) -> dict:
        if _API_BASE:
            return self._api_call("/api/v1/query", {
                "query": query,
                "session_id": self._session_id,
                "provider": self.provider,
                "certifications": certifications or [],
            })
        return self._local_query(query, certifications)

    def analyze_structured(
        self,
        sector: str,
        hs_codes: list,
        target_countries: list,
        revenue: float = 40,
        udyam: bool = True,
        certifications: list | None = None,
    ) -> dict:
        if _API_BASE:
            return self._api_call("/api/v1/query/structured", {
                "session_id": self._session_id,
                "sector": sector,
                "hs_codes": hs_codes,
                "target_countries": target_countries,
                "sme_revenue_cr": revenue,
                "has_udyam_registration": udyam,
                "provider": self.provider,
                "certifications": certifications or [],
            })
        return self._local_structured(
            sector, hs_codes, target_countries, revenue, udyam, certifications
        )

    def clear_session(self) -> None:
        if _API_BASE:
            try:
                _requests.delete(
                    f"{_API_BASE}/api/v1/sessions/{self._session_id}",
                    timeout=10,
                )
            except Exception:
                pass
        self._session_id = str(uuid.uuid4())
        self._graph = None

    def _api_call(self, path: str, payload: dict) -> dict:
        url = f"{_API_BASE}{path}"
        try:
            resp = _requests.post(url, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            agent_outputs = data.pop("agent_outputs", {})
            data.update(agent_outputs)
            return data
        except _requests.exceptions.Timeout:
            return {"summary": "Request timed out. Please try again.", "errors": ["API timeout"]}
        except _requests.exceptions.ConnectionError:
            return {"summary": "Could not connect to the API server.", "errors": ["API unreachable"]}
        except Exception as e:
            return {"summary": str(e), "errors": [str(e)]}

    def _get_graph(self):
        if self._graph is None:
            from orchestrator.main_agent import build_graph
            self._graph = build_graph(provider=self.provider)
        return self._graph

    def _local_query(self, query: str, certifications: list | None) -> dict:
        if not hasattr(self, "_memory"):
            from orchestrator.memory import ConversationMemory
            self._memory = ConversationMemory()
        from orchestrator.token_tracker import token_tracker
        token_tracker.reset(model=self.provider)
        context = self._memory.get_context_string(self._session_id)
        result = self._get_graph().invoke({
            "query": query,
            "sme_certifications": certifications or [],
            "conversation_context": context,
        })
        result["token_usage"] = token_tracker.get_summary().to_dict()
        self._memory.add_turn(
            self._session_id,
            query=query,
            sector=result.get("sector"),
            target_countries=result.get("target_countries", []),
            summary=result.get("summary", ""),
        )
        return result

    def _local_structured(
        self, sector, hs_codes, target_countries,
        revenue, udyam, certifications,
    ) -> dict:
        if not hasattr(self, "_memory"):
            from orchestrator.memory import ConversationMemory
            self._memory = ConversationMemory()
        from orchestrator.token_tracker import token_tracker
        token_tracker.reset(model=self.provider)
        context = self._memory.get_context_string(self._session_id)
        result = self._get_graph().invoke({
            "sector": sector,
            "hs_codes": hs_codes,
            "target_countries": target_countries,
            "sme_revenue_cr": revenue,
            "has_udyam_registration": udyam,
            "sme_certifications": certifications or [],
            "conversation_context": context,
        })
        result["token_usage"] = token_tracker.get_summary().to_dict()
        self._memory.add_turn(
            self._session_id,
            query=f"[structured] sector={sector}",
            sector=result.get("sector"),
            target_countries=result.get("target_countries", []),
            summary=result.get("summary", ""),
        )
        return result

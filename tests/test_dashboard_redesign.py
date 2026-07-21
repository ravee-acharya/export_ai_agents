"""
Tests for the redesigned decision-first dashboard (ui/dashboard.py) and
the token_usage bug fix in services/export_service.py.

Covers:
- _score_tier tier boundaries
- _best_per_country aggregation
- Comparison chart only renders with 2+ markets
- Dashboard never crashes on missing/partial data
- token_usage now actually flows through ExportService's local
  (non-API) path, which was the real production bug: analyze_query()/
  analyze_structured() in orchestrator/graph.py had the token tracker
  wiring, but ExportService bypasses those and calls
  self._get_graph().invoke() directly, so the tracker was never reset
  or attached to the result.
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _stub_streamlit():
    st_stub = types.ModuleType('streamlit')
    for name in ['subheader', 'markdown', 'write', 'caption', 'success',
                'warning', 'error', 'info', 'divider', 'metric', 'html']:
        setattr(st_stub, name, MagicMock())

    class FakeExpander:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    st_stub.expander = MagicMock(return_value=FakeExpander())
    st_stub.container = MagicMock(return_value=FakeExpander())
    st_stub.columns = MagicMock(
        side_effect=lambda spec: [MagicMock() for _ in (spec if isinstance(spec, list) else range(spec))]
    )
    st_stub.tabs = MagicMock(side_effect=lambda names: [FakeExpander() for _ in names])
    st_stub.plotly_chart = MagicMock()

    components_pkg = types.ModuleType('streamlit.components')
    v1 = types.ModuleType('streamlit.components.v1')
    v1.html = MagicMock()
    v1.iframe = MagicMock()
    components_pkg.v1 = v1
    st_stub.components = components_pkg

    sys.modules['streamlit'] = st_stub
    sys.modules['streamlit.components'] = components_pkg
    sys.modules['streamlit.components.v1'] = v1
    return st_stub


@pytest.fixture
def st_stub():
    stub = _stub_streamlit()
    # ui.dashboard binds `st` and `go` at import time, so a fresh
    # streamlit stub per test is invisible unless we force a re-import.
    for mod in ['ui.dashboard', 'ui.trade_globe', 'ui.theme']:
        sys.modules.pop(mod, None)
    return stub


# ------------------------------------------------------------------
# _score_tier
# ------------------------------------------------------------------

def test_score_tier_strong(st_stub):
    from ui.dashboard import _score_tier
    label, color, emoji = _score_tier(72)
    assert label == "Strong"
    assert color == "#3FB8AF"


def test_score_tier_moderate(st_stub):
    from ui.dashboard import _score_tier
    label, _, _ = _score_tier(45)
    assert label == "Moderate"


def test_score_tier_weak(st_stub):
    from ui.dashboard import _score_tier
    label, _, _ = _score_tier(15)
    assert label == "Weak"


def test_score_tier_boundaries(st_stub):
    from ui.dashboard import _score_tier
    assert _score_tier(60)[0] == "Strong"
    assert _score_tier(59.9)[0] == "Moderate"
    assert _score_tier(30)[0] == "Moderate"
    assert _score_tier(29.9)[0] == "Weak"


# ------------------------------------------------------------------
# _best_per_country
# ------------------------------------------------------------------

def test_best_market_picks_max_score_per_country(st_stub):
    from ui.dashboard import _best_per_country
    scores = [
        {"destination_country": "US", "score": 72.0},
        {"destination_country": "US", "score": 45.0},
        {"destination_country": "AE", "score": 81.0},
    ]
    best = _best_per_country(scores)
    assert best["US"]["score"] == 72.0
    assert best["AE"]["score"] == 81.0


def test_best_market_empty_list(st_stub):
    from ui.dashboard import _best_per_country
    assert _best_per_country([]) == {}
    assert _best_per_country(None) == {}


# ------------------------------------------------------------------
# Dashboard rendering — never crashes, comparison chart logic
# ------------------------------------------------------------------

def test_dashboard_handles_empty_result(st_stub):
    from ui.dashboard import render_dashboard
    render_dashboard({})
    render_dashboard(None)  # must not raise


def test_dashboard_renders_full_result_without_crashing(st_stub):
    from ui.dashboard import render_dashboard
    result = {
        "summary": "Test summary.",
        "opportunity_scores": [
            {"hs_code": "6907", "destination_country": "US", "score": 72.0,
             "score_breakdown": {"demand_growth_pct": 12.5}, "note": ""},
            {"hs_code": "6907", "destination_country": "AE", "score": 45.0,
             "score_breakdown": {}, "note": ""},
        ],
        "token_usage": {
            "model": "openrouter/auto", "total_input_tokens": 500,
            "total_output_tokens": 300, "total_tokens": 800,
            "total_cost_usd": 0.0,
            "per_agent": [{"agent": "synthesizer", "input_tokens": 500,
                          "output_tokens": 300, "total_tokens": 800, "cost_usd": 0.0}],
        },
    }
    render_dashboard(result)  # must not raise


def test_comparison_chart_skipped_for_single_market(st_stub):
    from ui.dashboard import render_dashboard
    result = {
        "opportunity_scores": [
            {"hs_code": "6907", "destination_country": "US", "score": 72.0,
             "score_breakdown": {}, "note": ""},
        ],
    }
    render_dashboard(result)
    assert not st_stub.plotly_chart.called


def test_comparison_chart_renders_for_multiple_markets(st_stub):
    from ui.dashboard import render_dashboard
    result = {
        "opportunity_scores": [
            {"hs_code": "6907", "destination_country": "US", "score": 72.0,
             "score_breakdown": {}, "note": ""},
            {"hs_code": "6907", "destination_country": "AE", "score": 45.0,
             "score_breakdown": {}, "note": ""},
        ],
    }
    render_dashboard(result)
    assert st_stub.plotly_chart.called


def test_dashboard_handles_missing_agent_outputs_gracefully(st_stub):
    """A result with only opportunity_scores and no other agent outputs
    (e.g. errors on every other agent) must still render cleanly."""
    from ui.dashboard import render_dashboard
    result = {
        "opportunity_scores": [
            {"hs_code": "6907", "destination_country": "US", "score": 50.0,
             "score_breakdown": {}, "note": ""},
        ],
        "errors": ["Pricing Agent failed: timeout"],
    }
    render_dashboard(result)  # must not raise despite no pricing/risk/etc output


# ------------------------------------------------------------------
# token_usage bug fix — ExportService's local (non-API) path
# ------------------------------------------------------------------

def test_export_service_local_query_includes_token_usage():
    """
    Regression test for the real production bug: ExportService bypasses
    orchestrator/graph.py's analyze_query()/analyze_structured() (which
    reset the token tracker and attach token_usage to the result) by
    calling self._get_graph().invoke() directly. This meant token_usage
    never appeared in the dashboard despite the tracker existing.
    """
    sys.path.insert(0, '.')

    class FakeResponse:
        content = "stub summary"
        response_metadata = {
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model_name": "openrouter/auto",
        }

    class FakeLLM:
        def invoke(self, prompt):
            p = prompt.lower()
            if "relevant_agents" in p:
                return FakeResponse()
            return FakeResponse()

    with patch("orchestrator.synthesizer.get_llm", return_value=FakeLLM()), \
         patch("orchestrator.graph.get_llm", return_value=FakeLLM()), \
         patch("orchestrator.query_parser.get_llm", return_value=FakeLLM()):

        import importlib
        import services.export_service as svc
        importlib.reload(svc)

        service = svc.ExportService(provider="openrouter")
        result = service.analyze_query("test query")

    assert "token_usage" in result
    assert result["token_usage"]["total_tokens"] > 0


def test_export_service_local_structured_includes_token_usage():
    sys.path.insert(0, '.')

    class FakeResponse:
        content = "stub summary"
        response_metadata = {
            "token_usage": {"prompt_tokens": 80, "completion_tokens": 40},
            "model_name": "openrouter/auto",
        }

    class FakeLLM:
        def invoke(self, prompt):
            return FakeResponse()

    with patch("orchestrator.synthesizer.get_llm", return_value=FakeLLM()), \
         patch("orchestrator.graph.get_llm", return_value=FakeLLM()):

        import importlib
        import services.export_service as svc
        importlib.reload(svc)

        service = svc.ExportService(provider="openrouter")
        result = service.analyze_structured(
            sector="ceramics", hs_codes=["6907"], target_countries=["US"],
        )

    assert "token_usage" in result
    assert result["token_usage"]["total_tokens"] > 0

"""Tests for prompts/manager.py"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch


def test_render_prompt_capability_gap():
    from prompts.manager import render_prompt
    result = render_prompt(
        "capability_gap",
        sector="textiles",
        target_countries="US, DE",
        sme_certifications='["ISO 9001"]',
        all_requirements='["ISO 9001", "OEKO-TEX"]',
    )
    assert "textiles" in result
    assert "US, DE" in result
    assert "ISO 9001" in result
    assert "gap_score" in result


def test_render_prompt_buyer_discovery():
    from prompts.manager import render_prompt
    result = render_prompt(
        "buyer_discovery",
        sector="leather",
        hs_codes='["4202"]',
        target_countries="US, UK",
    )
    assert "leather" in result
    assert "BUYER PERSONAS" in result
    assert "real company" in result


def test_render_prompt_query_parser():
    from prompts.manager import render_prompt
    result = render_prompt(
        "query_parser",
        context_block="",
        available_agents="demand_signal, pricing",
        query="export cotton towels to US",
    )
    assert "ONLY a JSON object" in result
    assert "demand_signal" in result
    assert "export cotton towels" in result


def test_render_prompt_synthesizer_main():
    from prompts.manager import render_prompt
    result = render_prompt(
        "synthesizer_main",
        context_block="",
        scores_json="[]",
        pricing_lines="(not requested)",
        risk_lines="(not requested)",
        competitor_lines="(not requested)",
        buyer_lines="(not requested)",
        fta_lines="(not requested)",
        doc_lines="(not requested)",
        cert_lines="(not requested)",
        rag_lines="(none retrieved)",
        schemes="(not requested)",
    )
    assert "ExportAI" in result
    assert "180 words" in result


def test_render_prompt_synthesizer_schemes():
    from prompts.manager import render_prompt
    result = render_prompt("synthesizer_schemes", schemes="RoDTEP, MAI")
    assert "RoDTEP" in result
    assert "100 words" in result


def test_missing_template_raises_file_not_found():
    from prompts.manager import render_prompt
    with pytest.raises(FileNotFoundError):
        render_prompt("nonexistent_prompt_xyz")


def test_safe_format_map_leaves_unknown_keys_unchanged():
    """Literal JSON braces in templates must not cause KeyError."""
    from prompts.manager import render_prompt
    # capability_gap template has {{ }} in JSON schema -- must not raise
    result = render_prompt(
        "capability_gap",
        sector="textiles",
        target_countries="US",
        sme_certifications="[]",
        all_requirements="[]",
    )
    # The {{ }} should have been rendered as literal { }
    assert "{" in result


def test_version_override():
    """Passing version= should look in a different directory."""
    from prompts.manager import render_prompt
    with pytest.raises(FileNotFoundError) as exc:
        render_prompt("capability_gap", version="v99")
    assert "v99" in str(exc.value)


def test_prompt_version_env_var(tmp_path, monkeypatch):
    """PROMPT_VERSION env var selects the active version directory."""
    v2_dir = tmp_path / "v2"
    v2_dir.mkdir()
    (v2_dir / "test_prompt.txt").write_text("hello {greeting}")

    import importlib
    import prompts.manager as pm
    importlib.reload(pm)

    with patch.object(pm, '_PROMPTS_DIR', tmp_path):
        with patch.object(pm, '_DEFAULT_VERSION', 'v2'):
            result = pm.render_prompt("test_prompt", greeting="world")
    assert result == "hello world"

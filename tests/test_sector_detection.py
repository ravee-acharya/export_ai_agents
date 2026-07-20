"""
Tests for orchestrator/query_parser.py sector detection.

Regression coverage for a real reported bug: a tiles/ceramics
manufacturer's query was silently answered as if it were about
textiles, because _normalize_sector had only one known sector
("textiles") and force-defaulted every unmatched sector to it --
even when the LLM had correctly extracted "ceramics".
"""

from orchestrator.query_parser import _normalize_sector, SECTOR_KEYWORDS, DEFAULT_HS_CODES


def test_ceramics_extracted_by_llm_is_preserved():
    result = _normalize_sector("ceramics", "I am a tiles and ceramics manufacturer")
    assert result == "ceramics"


def test_tiles_keyword_maps_to_ceramics_canonical():
    result = _normalize_sector("tiles", "I make tiles")
    assert result == "ceramics"


def test_ceramics_detected_from_query_when_llm_sector_empty():
    result = _normalize_sector("", "I am a tiles and ceramics manufacturer based in Gujarat")
    assert result == "ceramics"


def test_the_exact_reported_bug_scenario():
    """
    The exact query from the bug report: previously this silently
    became "textiles" and produced a completely wrong answer about
    home textiles/apparel buyers.
    """
    query = (
        "I am tiles and ceramic manufacturer based in Gujarat. "
        "I want to export my products. Which are top 3 markets for me and why?"
    )
    result = _normalize_sector("", query)
    assert result == "ceramics"
    assert result != "textiles"


def test_llm_extracted_descriptive_phrase_normalizes_to_canonical():
    """
    Real bug: when the LLM extracts a full descriptive phrase as the
    sector (e.g. "tiles and ceramics manufacturing") rather than a bare
    keyword, the old exact-match check (`sector in keywords`) missed
    it entirely and returned the raw phrase unchanged. Every downstream
    exact-key lookup (DEFAULT_HS_CODES, capability_requirements) then
    silently failed, producing empty HS codes and confusing later
    agents into generating answers about the wrong sector entirely.
    """
    result = _normalize_sector("tiles and ceramics manufacturing", "irrelevant")
    assert result == "ceramics"
    assert result != "textiles"

    # And it must still resolve to real HS codes afterward
    assert DEFAULT_HS_CODES.get(result)


def test_llm_extracted_phrase_variants_all_normalize_correctly():
    assert _normalize_sector("ceramics and tiles export", "x") == "ceramics"
    assert _normalize_sector("cotton textile manufacturing", "x") == "textiles"
    assert _normalize_sector("leather goods and footwear", "x") == "leather"
    assert _normalize_sector("auto parts and machinery manufacturing", "x") == "engineering"


def test_unrecognized_sector_from_llm_is_preserved_not_overwritten():
    """
    Critical fix: an LLM-extracted sector that doesn't match any known
    keyword list must be preserved as-is, never silently forced into
    "textiles". A wrong-but-honest passthrough is better than a
    confident-but-wrong default.
    """
    result = _normalize_sector("handicrafts", "I sell wooden handicrafts")
    assert result == "handicrafts"
    assert result != "textiles"


def test_textiles_still_works_as_before():
    assert _normalize_sector("", "I export cotton towels") == "textiles"
    assert _normalize_sector("textiles", "anything") == "textiles"
    assert _normalize_sector("cotton", "anything") == "textiles"


def test_leather_sector_detected():
    result = _normalize_sector("", "I manufacture leather footwear and handbags")
    assert result == "leather"


def test_engineering_sector_detected():
    result = _normalize_sector("", "I make auto parts and machinery components")
    assert result == "engineering"


def test_chemicals_sector_detected():
    result = _normalize_sector("", "I produce specialty chemicals and dyes")
    assert result == "chemicals"


def test_gems_jewellery_sector_detected():
    result = _normalize_sector("", "I export diamond jewellery")
    assert result == "gems_jewellery"


def test_absolute_last_resort_fallback_is_textiles():
    """When truly nothing can be determined, textiles remains the
    documented last-resort default (most complete supporting data)."""
    result = _normalize_sector("", "I want to know about export opportunities")
    assert result == "textiles"


def test_ceramics_has_default_hs_codes():
    assert "ceramics" in DEFAULT_HS_CODES
    assert len(DEFAULT_HS_CODES["ceramics"]) > 0
    assert "6907" in DEFAULT_HS_CODES["ceramics"] or "6908" in DEFAULT_HS_CODES["ceramics"]


def test_all_sector_keywords_have_matching_hs_codes():
    """Every sector with keywords should have a corresponding HS code default."""
    for sector in SECTOR_KEYWORDS:
        assert sector in DEFAULT_HS_CODES, f"{sector} has keywords but no default HS codes"


def test_sector_matching_is_case_insensitive():
    assert _normalize_sector("CERAMICS", "x") == "ceramics"
    assert _normalize_sector("", "I MAKE TILES") == "ceramics"

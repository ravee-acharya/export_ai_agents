"""
Template for new sub-agents.

Copy this file, rename it, and implement one of the two patterns below
depending on whether the job needs judgment or is purely mechanical.
Then register it in orchestrator/main_agent.py's `AVAILABLE_AGENTS` and
add a routing condition.

----------------------------------------------------------------------
PATTERN A: Deterministic sub-agent (like Demand Signal Agent)
----------------------------------------------------------------------
Use when the job is "fetch data, apply a formula, return structured
output" with no ambiguity. Cheaper, faster, fully testable.

    @dataclass
    class RiskAgentOutput:
        sector: str
        risks: list[RiskItem]

    def run_risk_agent(sector: str, target_countries: list[str]) -> RiskAgentOutput:
        # fetch from data_sources/..., apply rules, return typed output
        ...

----------------------------------------------------------------------
PATTERN B: LLM-backed sub-agent (e.g. Capability Gap Agent)
----------------------------------------------------------------------
Use when the job requires judgment calls an LLM is better suited for
than hard-coded rules — e.g. "does this SME's ISO 9001 certification
partially satisfy this target market's BSCI requirement?" That's a
fuzzy-matching judgment call, not a lookup.

    from langchain_anthropic import ChatAnthropic

    def run_capability_gap_agent(sme_profile: dict, target_spec: dict) -> dict:
        llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=800)
        prompt = f\"\"\"
        Compare this SME's capabilities against the target product's
        requirements. Return JSON only: {{"gap_score": 1-5, "missing": [...],
        "upgrade_path": [...]}}.

        SME profile: {sme_profile}
        Target requirements: {target_spec}
        \"\"\"
        response = llm.invoke(prompt)
        return parse_json_safely(response.content)

----------------------------------------------------------------------
Both patterns return plain Python objects (dataclass or dict) — never
raise raw exceptions up to the orchestrator. Catch and return a typed
error/empty state so one failing sub-agent doesn't crash the whole
graph run. See main_agent.py's `_safe_call` wrapper for how the
orchestrator already handles this.
"""

# ExportAI Agent Prototype — Demand Signal Agent + Main Orchestrator

A working LangGraph prototype of the multi-agent architecture: a **main
orchestrator agent** that routes requests and computes opportunity scores,
and one fully built **sub-agent (Demand Signal Agent)** that fetches trade
demand data for a sector/market pair.

This is built so the other four sub-agents (Capability Gap, Risk,
Pricing/Competitor, Scheme/Compliance) can be added later as siblings to
`demand_signal_agent.py` without changing the orchestrator's core shape —
see `agents/_template_agent.py`.

## Structure

```
export_ai_agents/
  agents/
    demand_signal_agent.py     # sub-agent: fetches + analyzes trade demand
    scheme_compliance_agent.py # sub-agent: matches govt schemes + compliance
    _template_agent.py         # copy this to add a new sub-agent
  data_sources/
    mock_trade_api.py          # stand-in for a real customs/trade data API
    scheme_knowledge_base.py   # curated Indian export scheme + compliance data
  orchestrator/
    main_agent.py               # LangGraph graph: fans out to both sub-agents, scores, synthesizes
    state.py                    # shared state schema
  run_demo.py                   # CLI entry point
  requirements.txt
```

## Why this shape

- **Sub-agents are stateless tools**, not separate LLM loops, for both
  Demand Signal and Scheme/Compliance — both are deterministic
  fetch-and-compute or fetch-and-match jobs, so wrapping them in their
  own LLM calls would add latency and cost for no quality gain. The
  *orchestrator* is the one agent that reasons with an LLM (Claude),
  deciding which sub-agents to call and synthesizing their outputs into
  a final opportunity score and natural-language summary.
- This mirrors the recommendation in the architecture doc: sub-agents
  should be narrow and cheap to run; the main agent is where intelligence
  and judgment live.
- **Scheme/Compliance Agent proves the fan-out/merge pattern**: the
  orchestrator now calls two sub-agents per request, each writing to its
  own state field, with independent failure handling (`_safe_call`) so
  one agent timing out doesn't take down the other. This is the pattern
  the remaining three agents (Risk, Capability Gap, Pricing/Competitor)
  will follow.
- When you add agents that genuinely need reasoning (e.g. Capability Gap
  matching, which involves judgment calls about partial certification
  matches), give *that* sub-agent its own LLM call — the template shows
  both patterns (deterministic tool vs. LLM-backed sub-agent).

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Run

```bash
# Single sector/market query, with SME revenue for scheme eligibility
python run_demo.py --sector textiles --markets US,EU --hs-codes 6302,5911 --revenue-cr 40

# Natural language query through the orchestrator (extracts revenue if mentioned)
python run_demo.py --query "What's the demand outlook and applicable schemes for a 40 crore textile exporter selling to the US and Germany?"
```

## What's mocked vs. real

- `data_sources/mock_trade_api.py` simulates customs/import data with
  realistic structure (volumes, growth rates, anomaly flags) seeded from
  your deck's textiles example (HS 6302, US home textiles). Swap this
  module for a real API client (UN Comtrade, ImportGenius, etc.) — the
  Demand Signal Agent's interface doesn't change.
- `data_sources/scheme_knowledge_base.py` is hand-curated, not mocked in
  the same sense — government scheme eligibility rules don't change
  daily, so this is meant to be maintained as real reference data
  (update quarterly or on policy change) rather than swapped for a live
  API. The PLI, RoDTEP, SIDBI, MAI, CEPA, and APEDA entries reflect
  actual current Indian export schemes; verify against official sources
  before using eligibility output in a real pitch or product.
- The orchestrator's scoring formula implements your deck's formula:
  `(Demand Growth × Import Gap × Price Premium) / (Capability Distance +
  Competition Density + Logistics Cost)`. Demand Growth and Competition
  Density now come from the real Demand Signal Agent; the other three
  factors (Import Gap, Price Premium, Capability Distance) still use
  placeholder defaults clearly marked in `orchestrator/main_agent.py` —
  wire in the Pricing/Competitor and Capability Gap agents to replace
  them.

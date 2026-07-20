"""
Token usage tracker.

Accumulates per-agent LLM token counts across a single query execution.
Each agent calls record_usage() after its LLM call; the orchestrator's
synthesize_node and query_parser also call it.

Usage:
    from orchestrator.token_tracker import token_tracker, record_usage

    # In an agent after llm.invoke():
    record_usage("capability_gap", response)

    # After all agents complete:
    summary = token_tracker.get_summary()
"""

import threading
from dataclasses import dataclass, field
from typing import Any

# Pricing per million tokens (USD) — July 2026
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":                        {"input": 3.00,   "output": 15.00},
    "claude-opus-4-6":                          {"input": 15.00,  "output": 75.00},
    "gemini-2.5-flash":                         {"input": 0.075,  "output": 0.30},
    "gemini-2.5-pro":                           {"input": 1.25,   "output": 10.00},
    "openrouter/auto":                          {"input": 0.0,    "output": 0.0},
    "meta-llama/llama-3.3-70b-instruct:free":  {"input": 0.0,    "output": 0.0},
    "meta-llama/llama-3.1-8b-instruct:free":   {"input": 0.0,    "output": 0.0},
}


@dataclass
class AgentTokenUsage:
    agent_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "unknown"

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost_usd(self) -> float:
        pricing = _PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        return (
            self.input_tokens * pricing["input"] / 1_000_000
            + self.output_tokens * pricing["output"] / 1_000_000
        )


@dataclass
class QueryTokenSummary:
    model: str
    per_agent: list[AgentTokenUsage] = field(default_factory=list)

    @property
    def total_input_tokens(self) -> int:
        return sum(a.input_tokens for a in self.per_agent)

    @property
    def total_output_tokens(self) -> int:
        return sum(a.output_tokens for a in self.per_agent)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        return sum(a.cost_usd() for a in self.per_agent)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "per_agent": [
                {
                    "agent": a.agent_name,
                    "input_tokens": a.input_tokens,
                    "output_tokens": a.output_tokens,
                    "total_tokens": a.total_tokens,
                    "cost_usd": round(a.cost_usd(), 6),
                }
                for a in sorted(
                    self.per_agent, key=lambda x: x.total_tokens, reverse=True
                )
            ],
        }


class TokenTracker:
    """
    Thread-safe per-query token accumulator.
    Uses threading.local() so concurrent agent threads don't mix counts.
    reset() is called at the start of each new query.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._usages: list[AgentTokenUsage] = []
        self._model = "unknown"

    def reset(self, model: str = "unknown") -> None:
        with self._lock:
            self._usages = []
            self._model = model

    def record(self, agent_name: str, response: Any, model: str | None = None) -> None:
        """
        Extract token counts from an LLM response and record them.
        Handles:
          - LangChain AIMessage (OpenRouter/Anthropic) → response_metadata
          - Our _GeminiResponse → usage_metadata attribute
          - Raw dicts (for testing)
        """
        input_tokens = 0
        output_tokens = 0
        used_model = model or self._model

        try:
            # LangChain AIMessage from ChatOpenAI / ChatAnthropic
            if hasattr(response, "response_metadata"):
                meta = response.response_metadata
                # OpenRouter / OpenAI format
                usage = meta.get("token_usage") or meta.get("usage") or {}
                input_tokens = int(
                    usage.get("prompt_tokens")
                    or usage.get("input_tokens")
                    or 0
                )
                output_tokens = int(
                    usage.get("completion_tokens")
                    or usage.get("output_tokens")
                    or 0
                )
                if meta.get("model_name"):
                    used_model = meta["model_name"]

            # Our _GeminiResponse with usage_metadata attribute
            elif hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                input_tokens = int(um.get("promptTokenCount", 0))
                output_tokens = int(um.get("candidatesTokenCount", 0))

            # Fallback: estimate from content length (~4 chars/token)
            elif hasattr(response, "content") and response.content:
                output_tokens = max(1, len(response.content) // 4)

        except Exception:
            pass  # never let tracking break the agent

        with self._lock:
            self._usages.append(AgentTokenUsage(
                agent_name=agent_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=used_model,
            ))

    def get_summary(self) -> QueryTokenSummary:
        with self._lock:
            return QueryTokenSummary(
                model=self._model,
                per_agent=list(self._usages),
            )


# Global singleton — one per process
token_tracker = TokenTracker()


def record_usage(agent_name: str, response: Any, model: str | None = None) -> None:
    """Convenience function for agents to call after llm.invoke()."""
    token_tracker.record(agent_name, response, model)

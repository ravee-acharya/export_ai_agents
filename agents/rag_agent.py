"""
RAG Agent.

Pattern A from agents/_template_agent.py in spirit -- retrieval here
is deterministic keyword scoring (see data_sources/knowledge_base.py),
not an LLM judgment call, even though "RAG" often implies an LLM
downstream. This agent's own job is pure retrieval; the LLM usage
happens later, in the synthesizer, when it writes prose grounded in
what this agent retrieved.

Unlike the other Pattern A agents, this one takes the raw query text
as input rather than structured sector/HS-code/country fields, since
retrieval relevance depends on the actual phrasing of what the person
asked. When the request came through the structured input path (no
free-text query), the registry's input builder falls back to a
synthetic query built from sector + countries so retrieval still has
something to work with.
"""

from dataclasses import dataclass, field

from data_sources.knowledge_base import KnowledgeSnippet, retrieve_snippets


@dataclass
class RAGAgentOutput:
    query: str
    snippets: list[KnowledgeSnippet] = field(default_factory=list)


def run_rag_agent(query: str, sector: str | None = None, top_k: int = 3) -> RAGAgentOutput:
    """
    The RAG Agent's entry point, called by the orchestrator like any
    other sub-agent. Never raises on empty/missing query -- returns an
    output with no snippets rather than crashing the graph.
    """
    query = query or ""
    combined_query = f"{query} {sector or ''}".strip()

    if not combined_query:
        return RAGAgentOutput(query=query, snippets=[])

    snippets = retrieve_snippets(combined_query, top_k=top_k)
    return RAGAgentOutput(query=query, snippets=snippets)

"""
Conversation memory.

A lightweight, in-memory (not persisted across process restarts) store
of recent exchanges per session, so follow-up questions in the same
conversation can reference earlier context ("what about pricing for
that same market") without the person having to restate sector/HS
codes/countries every turn.

This is a simplified stand-in for the roadmap's "Memory" component --
a real implementation would likely persist to a database (e.g.
Redis, per your planned Phase 6 stack) and might summarize/compress
history rather than keeping raw turns indefinitely. This version keeps
the last N turns per session in memory, which is enough to prove the
wiring (planner/synthesizer receiving prior context) without adding a
storage dependency to the prototype.
"""

from dataclasses import dataclass, field

_MAX_TURNS_PER_SESSION = 5


@dataclass
class ConversationTurn:
    query: str
    sector: str | None
    target_countries: list[str]
    summary: str


class ConversationMemory:
    """
    Usage:
        memory = ConversationMemory()
        memory.add_turn(session_id, query="...", sector="textiles",
                         target_countries=["US"], summary="...")
        context = memory.get_context_string(session_id)
    """

    def __init__(self):
        self._sessions: dict[str, list[ConversationTurn]] = {}

    def add_turn(
        self,
        session_id: str,
        query: str,
        sector: str | None,
        target_countries: list[str],
        summary: str,
    ) -> None:
        turns = self._sessions.setdefault(session_id, [])
        turns.append(
            ConversationTurn(
                query=query,
                sector=sector,
                target_countries=target_countries,
                summary=summary,
            )
        )
        # Keep only the most recent N turns per session.
        if len(turns) > _MAX_TURNS_PER_SESSION:
            self._sessions[session_id] = turns[-_MAX_TURNS_PER_SESSION:]

    def get_turns(self, session_id: str) -> list[ConversationTurn]:
        return list(self._sessions.get(session_id, []))

    def get_context_string(self, session_id: str) -> str:
        turns = self.get_turns(session_id)
        if not turns:
            return ""

        lines = []
        for i, turn in enumerate(turns, 1):
            countries = ", ".join(turn.target_countries) if turn.target_countries else "unspecified"
            lines.append(
                f"Turn {i}: asked about \"{turn.query}\" "
                f"(sector: {turn.sector or 'unspecified'}, markets: {countries}). "
                f"Summary given: {turn.summary[:200]}"
            )
        return "\n".join(lines)

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

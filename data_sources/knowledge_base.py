"""
Mock knowledge base for the RAG Agent: a small local corpus of
DGFT/WTO/trade reference snippets. Stand-in for a real
embeddings/vector-store pipeline over live DGFT notifications, WTO
publications, and trade reports.

Retrieval here is keyword-overlap scoring, not semantic search -- this
proves the RAG wiring (retrieve -> inject into synthesis) without
requiring an embeddings model or vector DB for the mock. Swapping in
real retrieval later means replacing retrieve_snippets()'s scoring
function; callers (the RAG Agent) don't need to change.
"""

from dataclasses import dataclass


@dataclass
class KnowledgeSnippet:
    title: str
    source: str
    text: str
    tags: tuple[str, ...]


_KNOWLEDGE_BASE: list[KnowledgeSnippet] = [
    KnowledgeSnippet(
        title="RoDTEP Scheme Overview",
        source="DGFT Notification (mock reference)",
        text=(
            "RoDTEP refunds embedded central/state duties and taxes not "
            "otherwise rebated (e.g. VAT on fuel, mandi tax, electricity "
            "duty) via transferable duty credit scrips, usable to pay "
            "future customs duty or transferable to other importers."
        ),
        tags=("rodtep", "duty refund", "scheme", "dgft"),
    ),
    KnowledgeSnippet(
        title="Rules of Origin under FTAs",
        source="WTO Trade Facilitation reference (mock)",
        text=(
            "Preferential tariff treatment under an FTA requires meeting "
            "the agreement's specific rules of origin -- typically a "
            "minimum domestic value-addition threshold and/or a change "
            "in tariff classification from imported inputs to the "
            "finished good. A Certificate of Origin issued under the "
            "correct FTA rules (not a generic non-preferential one) is "
            "usually required to claim the preferential rate at customs."
        ),
        tags=("fta", "rules of origin", "certificate of origin", "tariff"),
    ),
    KnowledgeSnippet(
        title="Anti-Dumping Duty Basics",
        source="WTO Anti-Dumping Agreement reference (mock)",
        text=(
            "Anti-dumping duties are imposed when an importing country's "
            "authority finds that goods are being exported below their "
            "normal (home-market) value and this is causing material "
            "injury to the domestic industry. These duties are specific "
            "to the exporting country and product, apply on top of "
            "standard tariffs, and are typically reviewed periodically "
            "(sunset reviews) rather than being permanent."
        ),
        tags=("anti-dumping", "tariff", "duty", "trade remedy"),
    ),
    KnowledgeSnippet(
        title="Udyam Registration for MSMEs",
        source="Ministry of MSME reference (mock)",
        text=(
            "Udyam Registration is a free, self-declared registration for "
            "Indian micro, small, and medium enterprises, used as an "
            "eligibility gate for many government export incentive "
            "schemes. Registration is based on investment in plant/"
            "machinery and annual turnover thresholds, and is done "
            "entirely online via the Udyam portal using Aadhaar and PAN."
        ),
        tags=("udyam", "msme", "registration", "scheme eligibility"),
    ),
    KnowledgeSnippet(
        title="ECGC Export Credit Cover",
        source="ECGC reference (mock)",
        text=(
            "ECGC (Export Credit Guarantee Corporation) provides credit "
            "insurance cover to Indian exporters against the risk of "
            "buyer payment default, covering both commercial risks "
            "(buyer insolvency, protracted default) and political risks "
            "(war, currency inconvertibility, import restrictions in the "
            "buyer's country). Premiums and cover terms vary by country "
            "risk classification."
        ),
        tags=("ecgc", "risk", "payment default", "credit insurance"),
    ),
    KnowledgeSnippet(
        title="HS Code Classification Basics",
        source="WCO Harmonized System reference (mock)",
        text=(
            "The Harmonized System (HS) classifies traded products using "
            "a 6-digit international code, with countries adding further "
            "digits for national tariff and statistical purposes. "
            "Correct HS classification determines the applicable tariff "
            "rate, FTA eligibility, and any product-specific import "
            "requirements -- misclassification is a common cause of "
            "customs delays and duty disputes."
        ),
        tags=("hs code", "classification", "tariff", "customs"),
    ),
]


_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "what", "how", "who",
    "with", "this", "that", "from", "into", "about", "does", "can",
    "will", "would", "should", "could", "have", "has", "had", "not",
}


def retrieve_snippets(query: str, top_k: int = 3) -> list[KnowledgeSnippet]:
    """
    Keyword-overlap retrieval: scores each snippet by how many query
    words (excluding common stopwords) appear in its tags or text,
    returns the top_k highest-scoring snippets with score > 0.
    Deterministic and dependency-free, unlike a real embeddings-based
    retriever, but sufficient to validate the RAG pipeline's wiring
    end to end.
    """
    query_words = {
        w.lower()
        for w in query.replace(",", " ").split()
        if len(w) > 2 and w.lower() not in _STOPWORDS
    }

    scored = []
    for snippet in _KNOWLEDGE_BASE:
        haystack = " ".join(snippet.tags) + " " + snippet.text.lower()
        score = sum(1 for w in query_words if w in haystack.lower())
        if score > 0:
            scored.append((score, snippet))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [snippet for _, snippet in scored[:top_k]]

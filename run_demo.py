"""
CLI for the ExportAI orchestrator prototype.

Usage:
    python run_demo.py --sector textiles --markets US,EU --hs-codes 6302,5911
    python run_demo.py --query "What's the demand outlook for textile exports to the US?"
"""

import argparse
import json
import os
import sys

from orchestrator.main_agent import build_graph


def main():
    parser = argparse.ArgumentParser(description="ExportAI agent orchestrator demo")
    parser.add_argument("--sector", help="Sector, e.g. textiles")
    parser.add_argument("--markets", help="Comma-separated target countries, e.g. US,EU")
    parser.add_argument("--hs-codes", help="Comma-separated HS codes, e.g. 6302,5911")
    parser.add_argument("--query", help="Natural language query instead of structured args")
    parser.add_argument("--revenue-cr", type=float, help="SME annual revenue in INR crores")
    parser.add_argument(
        "--llm",
        choices=["anthropic", "gemini", "ollama", "openrouter"],
        default=None,
        help="LLM provider to use (default: EXPORT_AI_LLM env var, or anthropic). "
             "gemini = Gemini 2.5 Flash (free tier). "
             "ollama = local Llama 3.1 (no key needed). "
             "openrouter = free models via openrouter.ai.",
    )

    args = parser.parse_args()

    provider = args.llm or os.environ.get("EXPORT_AI_LLM", "anthropic")

    # Validate only the selected provider
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    if provider == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable is not set.")
        sys.exit(1)

    if provider == "openrouter" and not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        sys.exit(1)

    if args.query:
        input_state = {
            "query": args.query
        }

    elif args.sector and args.markets and args.hs_codes:
        input_state = {
            "sector": args.sector,
            "hs_codes": [c.strip() for c in args.hs_codes.split(",")],
            "target_countries": [m.strip() for m in args.markets.split(",")],
            "sme_revenue_cr": args.revenue_cr,
            "has_udyam_registration": True,
        }

    else:
        parser.error(
            "Provide either --query, or all of --sector, --markets, and --hs-codes"
        )
        return

    app = build_graph(provider=provider)
    result = app.invoke(input_state)

    print("=" * 60)
    print("OPPORTUNITY SCORES")
    print("=" * 60)

    scores = result.get("opportunity_scores", [])

    if not scores:
        print("(none generated)")

    for s in scores:
        print(f"\n{s['hs_code']} -> {s['destination_country']}: {s['score']}/100")
        for k, v in s["score_breakdown"].items():
            print(f"   {k}: {v}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(result.get("summary", "(no summary)"))

    scheme_output = result.get("scheme_compliance_output")

    if scheme_output:
        print("\n" + "=" * 60)
        print("ELIGIBLE GOVERNMENT SCHEMES")
        print("=" * 60)

        eligible = scheme_output.eligible_schemes()

        if not eligible:
            print("(none matched)")

        for s in eligible:
            print(f"\n[{s.scheme_id}] {s.name}")
            print(f"   Issued by: {s.issuing_body}")
            print(f"   Benefit: {s.benefit_summary}")

        print("\n" + "=" * 60)
        print("COMPLIANCE REQUIREMENTS BY COUNTRY")
        print("=" * 60)

        for c in scheme_output.compliance_by_country:
            print(f"\n{c.country}:")
            for r in c.requirements:
                print(f"   - {r}")

    if result.get("errors"):
        print("\n" + "=" * 60)
        print("ERRORS")
        print("=" * 60)

        for e in result["errors"]:
            print(f"- {e}")

    print()


if __name__ == "__main__":
    main()
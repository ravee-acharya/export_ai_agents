"""
Tariff & FTA Agent.

Pattern A from agents/_template_agent.py: deterministic lookup, like
Scheme/Compliance, Logistics, Risk, and Competitor. Whether a given
(hs_code, destination_country) pair qualifies for a preferential
tariff rate under an FTA -- and what that rate is -- is reference data
(published agreement schedules), not a judgment call.

Originally scoped as two separate agents on the roadmap (FTA, and a
standalone Tariff agent for anti-dumping/countervailing/special
duties), these were merged: a dedicated Tariff agent would have needed
the same MFN baseline this agent already looks up to compare against
the preferential rate, creating either duplicated data or a
cross-agent dependency that breaks the "agents are independent,
composable via the registry" design the rest of the system follows.
Special duties are tracked as a distinct field per signal precisely
because they apply independently of FTA status -- an FTA zeroing out
the standard tariff doesn't cancel an anti-dumping duty imposed for an
unrelated reason.

Like Scheme/Compliance and Risk, this agent's output does NOT feed the
opportunity scoring formula. Tariff position is a distinct decision
input (conditional on rules-of-origin compliance, and subject to
special duties that can offset FTA savings), so it's surfaced
separately rather than folded into the score.
"""

from dataclasses import dataclass, field

from data_sources.fta_data import get_fta_info


@dataclass
class FTASignal:
    hs_code: str
    destination_country: str
    fta_name: str | None  # None if no FTA covers this market
    mfn_tariff_pct: float
    preferential_tariff_pct: float | None  # None if not FTA-eligible
    tariff_savings_pct: float  # 0 if not eligible
    rules_of_origin: str | None
    eligible: bool
    anti_dumping_duty_pct: float
    countervailing_duty_pct: float
    special_duty_notes: str | None
    effective_tariff_pct: float  # base rate (preferential or MFN) + special duties

    @property
    def has_special_duties(self) -> bool:
        return self.anti_dumping_duty_pct > 0 or self.countervailing_duty_pct > 0


@dataclass
class FTAAgentOutput:
    sector: str
    signals: list[FTASignal] = field(default_factory=list)

    def for_pair(self, hs_code: str, country: str) -> FTASignal | None:
        country = country.upper()
        for signal in self.signals:
            if signal.hs_code == hs_code and signal.destination_country == country:
                return signal
        return None

    def eligible_signals(self) -> list[FTASignal]:
        return [s for s in self.signals if s.eligible]

    def signals_with_special_duties(self) -> list[FTASignal]:
        return [s for s in self.signals if s.has_special_duties]


def run_fta_agent(
    sector: str,
    hs_codes: list[str],
    target_countries: list[str],
) -> FTAAgentOutput:
    """
    The Tariff & FTA Agent's entry point, called by the orchestrator
    like any other sub-agent. Every (hs_code, country) pair gets a
    signal -- unlike Pricing/Competitor, there's no "skip if unmapped"
    behavior here, since "no FTA available, pay standard MFN" is itself
    a meaningful, always-answerable result rather than missing data.
    """
    signals: list[FTASignal] = []

    for hs_code in hs_codes:
        for country in target_countries:
            info = get_fta_info(hs_code, country)

            preferential = info["preferential_tariff_pct"]
            mfn = info["mfn_tariff_pct"]
            eligible = preferential is not None

            savings = round(mfn - preferential, 2) if eligible else 0.0

            anti_dumping = info.get("anti_dumping_duty_pct", 0.0)
            countervailing = info.get("countervailing_duty_pct", 0.0)

            base_rate = preferential if eligible else mfn
            effective_tariff = round(base_rate + anti_dumping + countervailing, 2)

            signals.append(
                FTASignal(
                    hs_code=hs_code,
                    destination_country=country.upper(),
                    fta_name=info["fta_name"],
                    mfn_tariff_pct=mfn,
                    preferential_tariff_pct=preferential,
                    tariff_savings_pct=savings,
                    rules_of_origin=info["rules_of_origin"],
                    eligible=eligible,
                    anti_dumping_duty_pct=anti_dumping,
                    countervailing_duty_pct=countervailing,
                    special_duty_notes=info.get("special_duty_notes"),
                    effective_tariff_pct=effective_tariff,
                )
            )

    return FTAAgentOutput(sector=sector, signals=signals)

"""Schemes, tariff lines, trade notices and deadlines for the demo.

**Every figure in this module is illustrative.** The scheme names and the shape of the
data follow real Indian trade-facilitation programmes, but the rates, ceilings and dates
are invented for the demonstration. The product's whole argument is that guidance must be
traceable to a published record, so presenting fabricated numbers as policy would be the
exact harm it exists to prevent. The interface marks this data as illustrative wherever
it is shown, and every entry names the record it would cite in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

EntityType = Literal["msme", "large"]
Activity = Literal["exporter", "importer", "manufacturer", "trader"]


@dataclass(frozen=True)
class Scheme:
    """A benefit a business may be able to claim."""

    code: str
    name: str
    administered_by: str
    benefit: str
    """What the business actually gets, in plain terms."""
    who_qualifies: str
    how_to_claim: str
    entity_types: frozenset[str]
    activities: frozenset[str]
    sectors: frozenset[str]
    """'any' means the scheme is not sector-restricted."""
    turnover_ceiling_cr: float | None
    """Annual turnover ceiling in crore, or None when there is no limit."""
    window_closes: date | None
    source_title: str
    source_authority: str
    source_issued: date


#: Sector labels used across schemes and the tariff table.
SECTORS = ["textiles", "engineering", "agriculture", "chemicals", "handicrafts", "any"]

SCHEMES: list[Scheme] = [
    Scheme(
        code="RoDTEP",
        name="Remission of Duties and Taxes on Exported Products",
        administered_by="DGFT",
        benefit="A refund of embedded duties and taxes that no other scheme returns, "
                "credited as a transferable scrip against the free-on-board value of "
                "each eligible shipment.",
        who_qualifies="Any exporter of goods, whether or not registered as an MSME. The "
                      "rate depends on the tariff line, not on the size of the exporter.",
        how_to_claim="Declare the intent to claim on the shipping bill at the time of "
                     "export. A claim cannot be added afterwards.",
        entity_types=frozenset({"msme", "large"}),
        activities=frozenset({"exporter", "manufacturer"}),
        sectors=frozenset({"any"}),
        turnover_ceiling_cr=None,
        window_closes=None,
        source_title="Notification 19/2024 — RoDTEP rates and conditions",
        source_authority="DGFT",
        source_issued=date(2024, 3, 18),
    ),
    Scheme(
        code="MSME-EXP",
        name="MSME export incentive",
        administered_by="Ministry of Commerce and Industry",
        benefit="Two per cent of free-on-board value on eligible shipments, up to fifty "
                "lakh rupees a year for each exporter.",
        who_qualifies="Exporters holding a valid Udyam registration as a micro, small or "
                      "medium enterprise, with turnover under 250 crore.",
        how_to_claim="File a quarterly claim with shipping bills and the Udyam "
                     "certificate through the ministry portal.",
        entity_types=frozenset({"msme"}),
        activities=frozenset({"exporter"}),
        sectors=frozenset({"any"}),
        turnover_ceiling_cr=250.0,
        window_closes=date(2026, 9, 30),
        source_title="Scheme guidelines — MSME export incentive",
        source_authority="Ministry of Commerce and Industry",
        source_issued=date(2023, 1, 10),
    ),
    Scheme(
        code="IES",
        name="Interest equalisation on export credit",
        administered_by="RBI, through scheduled banks",
        benefit="Interest on pre-shipment and post-shipment rupee credit reduced by "
                "three percentage points for MSME manufacturers.",
        who_qualifies="MSME manufacturer-exporters with a working-capital facility from "
                      "a scheduled bank.",
        how_to_claim="Nothing to file. The bank applies the reduction and settles with "
                     "the RBI, so check that the sanction letter names the scheme.",
        entity_types=frozenset({"msme"}),
        activities=frozenset({"exporter", "manufacturer"}),
        sectors=frozenset({"any"}),
        turnover_ceiling_cr=150.0,
        window_closes=date(2026, 3, 31),
        source_title="Circular 11/2024 — Interest equalisation, revised eligibility",
        source_authority="RBI",
        source_issued=date(2024, 5, 2),
    ),
    Scheme(
        code="EPCG",
        name="Export Promotion Capital Goods authorisation",
        administered_by="DGFT",
        benefit="Capital goods imported at nil basic customs duty, against a commitment "
                "to export six times the duty saved within six years.",
        who_qualifies="Manufacturer-exporters, and merchant exporters tied to a "
                      "supporting manufacturer.",
        how_to_claim="Apply for an authorisation before importing. Machinery brought in "
                     "first cannot be regularised later.",
        entity_types=frozenset({"msme", "large"}),
        activities=frozenset({"manufacturer", "exporter"}),
        sectors=frozenset({"engineering", "textiles", "chemicals"}),
        turnover_ceiling_cr=None,
        window_closes=None,
        source_title="Public Notice 22/2024 — EPCG procedural conditions",
        source_authority="DGFT",
        source_issued=date(2024, 7, 9),
    ),
    Scheme(
        code="DBK",
        name="Duty drawback",
        administered_by="CBIC",
        benefit="Customs duty paid on imported inputs refunded when the finished goods "
                "are exported, at the rate set for the tariff line.",
        who_qualifies="Any exporter using imported or duty-paid inputs. Cannot be "
                      "combined with an advance authorisation for the same consignment.",
        how_to_claim="Claim on the shipping bill. The refund follows realisation of "
                     "export proceeds.",
        entity_types=frozenset({"msme", "large"}),
        activities=frozenset({"exporter", "importer", "manufacturer"}),
        sectors=frozenset({"any"}),
        turnover_ceiling_cr=None,
        window_closes=None,
        source_title="Circular 14/2024 — All industry drawback rates",
        source_authority="CBIC",
        source_issued=date(2024, 6, 28),
    ),
    Scheme(
        code="MAI",
        name="Market Access Initiative",
        administered_by="Ministry of Commerce and Industry",
        benefit="Up to seventy-five per cent of the cost of taking part in an approved "
                "overseas trade fair, including stall and freight.",
        who_qualifies="Exporters nominated through an Export Promotion Council. First-"
                      "time participants are given preference.",
        how_to_claim="Apply through the relevant council at least sixty days before the "
                     "event.",
        entity_types=frozenset({"msme"}),
        activities=frozenset({"exporter", "trader"}),
        sectors=frozenset({"handicrafts", "textiles", "agriculture"}),
        turnover_ceiling_cr=100.0,
        window_closes=date(2026, 11, 15),
        source_title="Scheme guidelines — Market Access Initiative 2024-27",
        source_authority="Ministry of Commerce and Industry",
        source_issued=date(2024, 4, 22),
    ),
    Scheme(
        code="AA",
        name="Advance authorisation",
        administered_by="DGFT",
        benefit="Inputs imported duty-free where they are physically incorporated into "
                "an export product, against a value-addition commitment.",
        who_qualifies="Manufacturer-exporters, and merchant exporters tied to a "
                      "supporting manufacturer.",
        how_to_claim="Apply against standard input-output norms, or seek ad hoc norms "
                     "where none exist for your product.",
        entity_types=frozenset({"msme", "large"}),
        activities=frozenset({"manufacturer", "exporter"}),
        sectors=frozenset({"chemicals", "engineering", "textiles"}),
        turnover_ceiling_cr=None,
        window_closes=None,
        source_title="Handbook of Procedures — Advance authorisation",
        source_authority="DGFT",
        source_issued=date(2023, 4, 1),
    ),
]


def _plural(word: str) -> str:
    return word if word.endswith("s") else f"{word}s"


def _join(items: list[str]) -> str:
    """Join a list the way a person would read it aloud."""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])} and {items[-1]}"


def eligible(
    entity_type: str | None, activity: str | None, sector: str | None,
    turnover_cr: float | None,
) -> list[dict]:
    """Match a business against the schemes, and say *why* each verdict was reached.

    Returning the reason matters more than returning the verdict. A business told only
    "not eligible" learns nothing it can act on; told "the turnover ceiling is 150 crore"
    it knows what changed and when to look again. The same principle as the no-answer
    path: state the limit, do not just decline.
    """
    results: list[dict] = []
    for scheme in SCHEMES:
        reasons_against: list[str] = []

        if entity_type and entity_type not in scheme.entity_types:
            reasons_against.append(
                "Open to MSMEs only"
                if scheme.entity_types == {"msme"}
                else f"Open to {_join(sorted(scheme.entity_types))} enterprises"
            )
        if activity and activity not in scheme.activities:
            reasons_against.append(
                f"Open to {_join([_plural(a) for a in sorted(scheme.activities)])}, "
                f"not {_plural(activity)}"
            )
        if sector and "any" not in scheme.sectors and sector not in scheme.sectors:
            reasons_against.append(f"Limited to {_join(sorted(scheme.sectors))}")
        if (
            turnover_cr is not None
            and scheme.turnover_ceiling_cr is not None
            and turnover_cr > scheme.turnover_ceiling_cr
        ):
            reasons_against.append(
                f"Turnover must be under {scheme.turnover_ceiling_cr:g} crore"
            )

        results.append({
            "code": scheme.code,
            "name": scheme.name,
            "administered_by": scheme.administered_by,
            "benefit": scheme.benefit,
            "who_qualifies": scheme.who_qualifies,
            "how_to_claim": scheme.how_to_claim,
            "sectors": sorted(scheme.sectors),
            "entity_types": sorted(scheme.entity_types),
            "turnover_ceiling_cr": scheme.turnover_ceiling_cr,
            "window_closes": scheme.window_closes.isoformat() if scheme.window_closes else None,
            "eligible": not reasons_against,
            "reasons_against": reasons_against,
            "source": {
                "title": scheme.source_title,
                "authority": scheme.source_authority,
                "issued_on": scheme.source_issued.isoformat(),
            },
        })
    # Eligible first, then by nearest closing window — a benefit with a deadline is the
    # one a business most needs to see before it lapses.
    results.sort(key=lambda s: (not s["eligible"], s["window_closes"] or "9999-12-31"))
    return results


# --------------------------------------------------------------------------------------
# Tariff lines
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TariffLine:
    heading: str
    description: str
    basic_duty_pct: float
    effective_from: date
    sector: str
    source_title: str
    source_authority: str
    note: str = ""


TARIFF: list[TariffLine] = [
    TariffLine("5205", "Cotton yarn, not put up for retail sale", 5.0,
               date(2024, 7, 1), "textiles",
               "Circular 08/2024 — Basic customs duty on cotton yarn", "CBIC",
               "Reduced from 7.5% with effect from 1 July 2024."),
    TariffLine("5208", "Woven fabrics of cotton, 85% or more by weight", 10.0,
               date(2024, 4, 1), "textiles",
               "Tariff schedule 2024-25, Chapter 52", "CBIC"),
    TariffLine("7308", "Structures and parts of structures, of iron or steel", 7.5,
               date(2024, 4, 1), "engineering",
               "Tariff schedule 2024-25, Chapter 73", "CBIC"),
    TariffLine("8479", "Machines having individual functions, not specified elsewhere",
               7.5, date(2024, 4, 1), "engineering",
               "Tariff schedule 2024-25, Chapter 84", "CBIC",
               "Nil under an EPCG authorisation."),
    TariffLine("2933", "Heterocyclic compounds with nitrogen hetero-atom(s) only", 10.0,
               date(2024, 4, 1), "chemicals",
               "Tariff schedule 2024-25, Chapter 29", "CBIC"),
    TariffLine("4420", "Wood marquetry and inlaid wood; caskets and cases", 10.0,
               date(2023, 4, 1), "handicrafts",
               "Tariff schedule 2023-24, Chapter 44", "CBIC",
               "Export status disputed across two public notices — see the gap queue."),
    TariffLine("0904", "Pepper; dried or crushed fruits of the genus Capsicum", 30.0,
               date(2024, 4, 1), "agriculture",
               "Tariff schedule 2024-25, Chapter 9", "CBIC"),
    TariffLine("1006", "Rice", 0.0, date(2024, 4, 1), "agriculture",
               "Tariff schedule 2024-25, Chapter 10", "CBIC",
               "Export restrictions apply separately to certain varieties."),
]


# --------------------------------------------------------------------------------------
# Trade notices — what changed recently
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Notice:
    reference: str
    authority: str
    issued_on: date
    subject: str
    change: str
    """What actually changed, in plain terms — not the document's own title again."""
    kind: Literal["new", "amended", "superseding", "clarification"]
    affects: list[str] = field(default_factory=list)
    supersedes: str | None = None


NOTICES: list[Notice] = [
    Notice("PN 07/2024", "DGFT", date(2024, 2, 20),
           "Handicraft export status",
           "Wooden handicraft items moved from freely exportable to restricted. A licence "
           "is now required.",
           "superseding", ["handicrafts"], supersedes="PN 41/2023"),
    Notice("Circular 08/2024", "CBIC", date(2024, 6, 15),
           "Basic customs duty on cotton yarn",
           "Duty on heading 5205 reduced from 7.5% to 5%, effective 1 July 2024.",
           "amended", ["textiles"]),
    Notice("Notification 19/2024", "DGFT", date(2024, 3, 18),
           "RoDTEP rates and conditions",
           "Rates revised for 432 tariff lines. The intent to claim must now be declared "
           "on the shipping bill itself.",
           "amended", ["textiles", "engineering", "chemicals"]),
    Notice("PN 22/2024", "DGFT", date(2024, 7, 9),
           "EPCG procedural conditions",
           "Export obligation period clarified at six years from authorisation, not from "
           "the date of first import.",
           "clarification", ["engineering", "textiles"]),
    Notice("Circular 11/2024", "RBI", date(2024, 5, 2),
           "Interest equalisation, revised eligibility",
           "Turnover ceiling for MSME manufacturers set at 150 crore. Traders are no "
           "longer covered.",
           "amended", ["any"]),
    Notice("Notification 12/2024", "DGFT", date(2024, 4, 1),
           "Export licensing of restricted goods",
           "Consolidated licensing conditions for Schedule 2 items. Applications move to "
           "the DGFT portal.",
           "new", ["any"]),
]


# --------------------------------------------------------------------------------------
# Compliance deadlines
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Deadline:
    label: str
    due_on: date
    applies_to: str
    consequence: str
    """What happens if it is missed — the part that makes a date worth acting on."""


DEADLINES: list[Deadline] = [
    Deadline("Quarterly MSME incentive claim", date(2026, 9, 30),
             "MSME exporters claiming under MSME-EXP",
             "The quarter's shipments cannot be claimed later."),
    Deadline("Interest equalisation scheme window", date(2026, 3, 31),
             "MSME manufacturer-exporters with bank credit",
             "The reduced rate lapses; existing sanctions revert to the standard rate."),
    Deadline("Market Access Initiative — autumn fairs", date(2026, 11, 15),
             "Exporters nominated by an Export Promotion Council",
             "Applications close sixty days before the event."),
    Deadline("Annual IEC details confirmation", date(2027, 6, 30),
             "Every holder of an Importer Exporter Code",
             "The code is deactivated until the details are confirmed."),
]

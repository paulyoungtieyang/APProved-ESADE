"""
Requirements-fit engine — deterministic, offline-first matching of a client's
evidence against any external requirement list.

Deliberately generic. "External requirements" covers a public tender, a
reimbursement / HTA submission checklist, a formulary committee's criteria, a
notified-body or FDA pre-submission checklist, a partner's due-diligence list —
anything phrased as a set of discrete requirement lines that a submission has
to answer against. Nothing here assumes a device type, a therapeutic area or a
market; those live only in whatever text the client supplies (the requirement
list itself, the brief, and the free-text "characteristics" they add).

The matching is intentionally legible rather than clever: keyword overlap
against three sources of client-supplied signal (characteristics text, brief
free-text fields, uploaded-evidence categories). It will not catch a paraphrase
and says so — see `MATCHING_CAVEAT` — in keeping with the rest of the offline
engine's rule of never asserting more than the input supports.
"""

from __future__ import annotations

import re
from typing import Any

MATCHING_CAVEAT = (
    "Matching is keyword-based screening, not clinical or regulatory judgement. "
    "Treat every verdict below as a starting point for expert review, not a filed answer."
)

# Generic English signal words for each evidence category already used across the
# platform (core.dataset.classify / the upload categories). These describe what the
# category *means*, not any device or market — the same eight categories work for a
# diagnostic, a drug-device combination, an app, or a piece of lab equipment.
#
# Deliberately biased toward under-claiming: a word only sits here if it's fairly
# specific to that category. Generic words ("performance", "evidence", "value",
# "quality", "effectiveness") are left out even where they'd sometimes be a fair
# signal, because a false "Met" is a worse failure than a false "Partial" for a
# screening tool — the whole point is to surface what still needs a human look.
CATEGORY_SIGNALS: dict[str, set[str]] = {
    "clinical": {"clinical", "accuracy", "study", "trial", "investigation"},
    "safety": {"safety", "adverse", "risk", "tolerability", "hazard", "harm"},
    "efficacy": {"efficacy", "endpoint", "outcome", "statistical", "significance"},
    "demographics": {"demographic", "population", "baseline", "cohort", "eligibility"},
    "economics": {"cost", "price", "pricing", "budget", "economic", "reimbursement", "tender"},
    "software": {"software", "algorithm", "digital", "specification", "functional"},
    "verification": {"verification", "validation", "test", "testing", "qa"},
    "brand": {"brand", "template", "design", "visual", "logo"},
}

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "for", "and", "or", "is", "are", "be", "with",
    "on", "by", "that", "this", "as", "at", "from", "must", "shall", "should", "will",
    "any", "all", "each", "per", "than", "into", "not", "no", "it", "its", "their",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {word for word in words if len(word) > 2 and word not in STOPWORDS}


# --------------------------------------------------------------------------
# Parsing — a requirement list arrives either as free text (one per line, the
# common case when someone has copied it out of a PDF) or as a table with a
# recognisable column.
# --------------------------------------------------------------------------

_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]|(?:\d+|[a-zA-Z])[.)])\s*")

_TEXT_COLUMN_ALIASES = ("requirement", "requirement_text", "criterion", "criteria", "description")
_ID_COLUMN_ALIASES = ("requirement_id", "id", "ref", "reference")
_CATEGORY_COLUMN_ALIASES = ("category", "section", "theme")
_MANDATORY_COLUMN_ALIASES = ("mandatory", "required", "must_have")


def parse_requirements_text(text: str) -> list[dict[str, Any]]:
    """One requirement per non-blank line — bullets, numbering and dashes stripped."""
    requirements = []
    for line in (text or "").splitlines():
        stripped = _BULLET_PREFIX.sub("", line).strip()
        if not stripped:
            continue
        requirements.append({
            "id": f"R{len(requirements) + 1}",
            "text": stripped,
            "category": "",
            "mandatory": None,
            "source": "pasted text",
        })
    return requirements


def parse_requirements_table(rows: list[dict]) -> list[dict[str, Any]]:
    """From an uploaded CSV/XLSX — flexible column naming, first matching alias wins."""
    if not rows:
        return []

    columns = {key.strip().lower(): key for key in rows[0].keys()}

    def find(aliases: tuple[str, ...]) -> str | None:
        for alias in aliases:
            if alias in columns:
                return columns[alias]
        return None

    text_col = find(_TEXT_COLUMN_ALIASES)
    if not text_col:
        return []
    id_col = find(_ID_COLUMN_ALIASES)
    category_col = find(_CATEGORY_COLUMN_ALIASES)
    mandatory_col = find(_MANDATORY_COLUMN_ALIASES)

    requirements = []
    for row in rows:
        text = str(row.get(text_col, "")).strip()
        if not text:
            continue
        mandatory_raw = str(row.get(mandatory_col, "")).strip().lower() if mandatory_col else ""
        requirements.append({
            "id": str(row.get(id_col, "")).strip() or f"R{len(requirements) + 1}",
            "text": text,
            "category": str(row.get(category_col, "")).strip() if category_col else "",
            "mandatory": mandatory_raw in ("yes", "true", "1", "y") if mandatory_raw else None,
            "source": "uploaded file",
        })
    return requirements


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

def match_requirements(
    requirements: list[dict],
    brief: dict,
    stats: dict,
    characteristics: str = "",
) -> list[dict[str, Any]]:
    """
    Score each requirement against the client's own text and uploaded evidence.

    Returns each requirement with a verdict ("Met" / "Partial" / "Not addressed"),
    the basis for that verdict, and argumentation text ready to drop into the
    report — strongest for "Met", most in need of expert input for "Not addressed".
    """
    characteristics_tokens = _tokenize(characteristics)
    brief_text = " ".join(str(brief.get(field) or "") for field in (
        "therapeutic_area", "target_audience", "focus_area", "key_messages",
        "additional_requirements", "regional_tender_spec",
    ))
    brief_tokens = _tokenize(brief_text)

    # `stats["files"]` carries each upload's category (clinical / safety / efficacy /
    # demographics / economics / software / verification / brand — the same strings
    # `core.dataset.classify` and the upload category dropdown use), independent of
    # which per-category summary buckets `dataset_stats()` happens to compute.
    categories_present = {
        entry.get("category") for entry in (stats.get("files") or [])
        if entry.get("category") in CATEGORY_SIGNALS and not entry.get("error")
    }

    results = []
    for requirement in requirements:
        req_tokens = _tokenize(requirement["text"])
        if not req_tokens:
            req_tokens = set()

        char_hits = req_tokens & characteristics_tokens
        brief_hits = req_tokens & brief_tokens

        relevant_categories = {
            category for category, signals in CATEGORY_SIGNALS.items()
            if req_tokens & signals
        }
        covered_categories = relevant_categories & categories_present
        uncovered_categories = relevant_categories - categories_present

        if covered_categories or len(char_hits) >= 2:
            verdict = "Met"
        elif char_hits or brief_hits or relevant_categories:
            verdict = "Partial"
        else:
            verdict = "Not addressed"

        # Basis text always names whatever actually drove the verdict above, so the
        # two can never contradict each other (a "Partial" with no visible reason
        # reads as a bug, not a judgement call).
        basis_parts = []
        if covered_categories:
            basis_parts.append(
                f"evidence uploaded in {', '.join(sorted(covered_categories))}"
            )
        if char_hits:
            basis_parts.append(
                f"stated characteristics ({', '.join(sorted(char_hits))})"
            )
        if brief_hits and not char_hits:
            basis_parts.append("the engagement brief")
        if not basis_parts and uncovered_categories:
            basis_parts.append(
                f"topic looks related to {', '.join(sorted(uncovered_categories))}, "
                "but nothing uploaded covers it"
            )
        basis = "; ".join(basis_parts) if basis_parts else "no matching signal found"

        if verdict == "Met":
            argument = (
                f"Supported by {basis}. Cite the specific figure or document when "
                "drafting the final answer rather than this summary line."
            )
        elif verdict == "Partial":
            if uncovered_categories:
                argument = (
                    f"Referenced ({basis}), but no uploaded evidence file falls under "
                    f"{', '.join(sorted(uncovered_categories))}. Upload direct evidence, "
                    "or write the case for why the existing evidence still applies."
                )
            else:
                argument = (
                    f"Weak signal only ({basis}). Strengthen with a direct data point, "
                    "or draft the argument for why this is still satisfied."
                )
        else:
            argument = (
                "No matching evidence or stated characteristic found. Either this is a "
                "genuine gap — flag it for expert review before submission — or the "
                "differentiator that answers it hasn't been entered above yet."
            )

        results.append({
            **requirement,
            "verdict": verdict,
            "basis": basis,
            "argument": argument,
        })

    return results


def summarise_matches(matches: list[dict]) -> dict[str, int]:
    counts = {"Met": 0, "Partial": 0, "Not addressed": 0}
    for match in matches:
        counts[match["verdict"]] = counts.get(match["verdict"], 0) + 1
    counts["total"] = len(matches)
    return counts


# --------------------------------------------------------------------------
# Prompt composition + offline draft — same three-layer shape as the rest of
# the drafting engine, so this deliverable type behaves like any other.
# --------------------------------------------------------------------------

def build_requirements_prompt(
    label: str,
    requirements: list[dict],
    matches: list[dict],
    characteristics: str,
    brief: dict,
) -> str:
    counts = summarise_matches(matches)
    lines = [
        "# Layer 1 — Client baseline (from the signed brief)",
        f"Device / therapeutic area: {brief.get('therapeutic_area', 'not stated')}",
        f"Target markets: {', '.join(brief.get('target_markets') or []) or 'not stated'}",
        f"Regulatory frameworks: {', '.join(brief.get('regulatory_frameworks') or []) or 'not stated'}",
        "",
        "# Layer 2 — Deliverable template",
        f"Produce a requirements-fit analysis titled '{label}'.",
        "For every requirement below, state the verdict (Met / Partial / Not addressed), "
        "the evidence basis, and — for anything not fully Met — write the argumentation a "
        "submission could use: why the requirement is satisfied despite an imperfect match, "
        "or a clear statement that it is a genuine gap needing expert input.",
        "Do not invent evidence, figures or claims that are not present in the requirement "
        "text, the characteristics below, or the uploaded dataset. Where nothing supports a "
        "requirement, say so plainly rather than writing around it.",
        "",
        f"## Requirements ({counts['total']} total — "
        f"{counts['Met']} met, {counts['Partial']} partial, {counts['Not addressed']} not addressed)",
    ]
    for item in requirements:
        lines.append(f"- [{item['id']}] {item['text']}")

    lines += [
        "",
        "## Match screening already performed (keyword-based — verify, don't just repeat)",
    ]
    for match in matches:
        lines.append(f"- [{match['id']}] {match['verdict']} — {match['basis']}")

    if characteristics.strip():
        lines += ["", "# Layer 3 — Product / service characteristics supplied by the requester",
                   characteristics.strip()]

    return "\n".join(lines)


def draft_requirements_report(
    label: str,
    requirements: list[dict],
    matches: list[dict],
    characteristics: str,
) -> str:
    """Deterministic offline report — the same shape an LLM pass would elaborate on."""
    counts = summarise_matches(matches)
    lines = [
        f"## Requirements Fit — {label}",
        "",
        f"*{MATCHING_CAVEAT}*",
        "",
        f"**{counts['total']} requirements screened** — "
        f"**{counts['Met']} Met**, **{counts['Partial']} Partial**, "
        f"**{counts['Not addressed']} Not addressed**.",
        "",
        "| ID | Requirement | Verdict | Basis |",
        "|---|---|---|---|",
    ]
    for match in matches:
        req_text = match["text"].replace("|", "/")
        lines.append(f"| {match['id']} | {req_text} | **{match['verdict']}** | {match['basis']} |")

    gaps = [match for match in matches if match["verdict"] != "Met"]
    if gaps:
        lines += ["", "### Gap argumentation", ""]
        for match in gaps:
            lines.append(f"**[{match['id']}] {match['text']}** — *{match['verdict']}*")
            lines.append(match["argument"])
            lines.append("")

    if characteristics.strip():
        lines += ["### Characteristics considered", "", characteristics.strip()]

    return "\n".join(lines)

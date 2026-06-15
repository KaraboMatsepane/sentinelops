"""
Scenario data loader - loads contract/vendor data and company history from JSON files.
Agents use this instead of hardcoding data in source files.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_scenario(scenario_id: str) -> dict:
    filename = {
        "a": "scenario_a.json",
        "b": "scenario_b_vendor.json",
    }.get(scenario_id.lower())
    if not filename:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)


def load_company_history() -> dict:
    with open(os.path.join(DATA_DIR, "company_history.json")) as f:
        return json.load(f)


def detect_scenario(message_text: str) -> str:
    text = message_text.lower()
    if "scenario b" in text or "vendor" in text or "cloud" in text or "migration" in text:
        return "b"
    return "a"


def format_scenario_for_prompt(scenario: dict) -> str:
    if scenario.get("scenario") == "A":
        return _format_contract(scenario)
    return _format_vendor(scenario)


def _format_contract(s: dict) -> str:
    sections = "\n".join(
        f'  Section {sec["section"]} (p.{sec["page"]}): {sec["title"]} - {sec["content"]}'
        for sec in s["document_sections"]
    )
    fin = s["key_financials"]
    return (
        f'Document: {s["title"]} ({s.get("duration_years", 3)}-year deal)\n'
        f'Parties: {s["parties"]["company"]} ↔ {s["parties"]["partner"]}\n'
        f'Deal Value: ${s["deal_value"]:,}\n\n'
        f'KEY SECTIONS:\n{sections}\n\n'
        f'KEY FINANCIALS:\n'
        f'  Total value: ${fin["total_value"]:,}\n'
        f'  Annual minimum: ${fin["annual_minimum"]:,}\n'
        f'  Revenue share: {fin["revenue_share_pct"]}%\n'
        f'  Liability cap: ${fin["liability_cap"]:,}\n'
        f'  Penalty schedule: {fin["penalty_schedule"]}'
    )


def _format_vendor(s: dict) -> str:
    lines = [
        f'Decision: {s["title"]}',
        f'Budget: ${s["budget"]:,}/year | Timeline: {s["timeline"]}',
        f'Context: {s["company_context"]["migration_driver"]}',
        f'Traffic projection: {s["company_context"]["traffic_projection"]}',
        "",
        "VENDORS UNDER EVALUATION:",
    ]
    for v in s["vendors"]:
        lines.append(f'\n  {v["name"]} - ${v["annual_cost"]:,}/year')
        lines.append("  Strengths:")
        for h in v["proposal_highlights"]:
            lines.append(f"    + {h}")
        lines.append("  Concerns:")
        for c in v["concerns"]:
            lines.append(f"   - {c}")
    lines.append(f'\nEvaluation criteria: {", ".join(s["evaluation_criteria"])}')
    return "\n".join(lines)


def format_history_for_prompt(history: dict, scenario_id: str = "a") -> str:
    entries = history["history_entries"]
    if scenario_id == "b":
        entries = [e for e in entries if e.get("scenarios", ["a", "b"]) is None or "b" in e.get("scenarios", ["a", "b"])]
    lines = [f'Company: {history["company"]}\n\nINSTITUTIONAL MEMORY:']
    for e in entries:
        lines.append(
            f'\n[{e["date"]}] {e["title"]}\n'
            f'  Type: {e["type"]}\n'
            f'  Detail: {e["detail"]}\n'
            f'  Outcome: {e["outcome"]}\n'
            f'  Relevance: {e.get("relevance", "MEDIUM")}'
        )
    return "\n".join(lines)

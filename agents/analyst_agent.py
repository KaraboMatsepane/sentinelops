"""
SentinelOps — Analyst Agent (Agent 1)
Role: The Mapper

Receives the input document, maps everything into structured data,
and posts to Band — triggering Devil's Advocate and Precedent simultaneously.

Run with: python agents/analyst_agent.py
"""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config

from resilient_adapter import ResilientAdapter
from band_targets import handle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.analyst")

CONTRACT_DATA = json.dumps({
    "title": "GlobalTech Solutions Partnership Agreement",
    "pages": 74,
    "parties": {
        "company": "Meridian Ventures Ltd",
        "partner": "GlobalTech Solutions Inc"
    },
    "deal_value": 1800000,
    "duration_years": 3,
    "sections": [
        {"section": "1.2", "page": 8, "title": "Revenue Share", "content": "GlobalTech Solutions shall receive 35% of all net revenues generated through the partnership channels, applying exclusively to all distribution activities within EMEA and APAC regions."},
        {"section": "2.1", "page": 12, "title": "Best Efforts Commitment", "content": "Meridian Ventures agrees to use its best efforts to promote GlobalTech Solutions products across all applicable markets and shall dedicate reasonable resources to achieve mutual business objectives as determined from time to time."},
        {"section": "3.4", "page": 19, "title": "Minimum Purchase Commitment", "content": "Meridian Ventures commits to minimum annual purchases of $600,000 in GlobalTech Solutions products and services. Failure to meet this commitment triggers automatic penalties outlined in Schedule C."},
        {"section": "4.1", "page": 27, "title": "Intellectual Property", "content": "Any improvements, modifications, or derivative works created by Meridian Ventures using GlobalTech Solutions technology shall become the sole property of GlobalTech Solutions upon creation, without additional compensation."},
        {"section": "5.2", "page": 34, "title": "Exclusivity Clause", "content": "Meridian Ventures agrees to maintain exclusive distribution rights for GlobalTech Solutions within the EMEA region and shall not distribute, promote, or sell competing products or services during the term of this agreement."},
        {"section": "6.3", "page": 41, "title": "Termination Rights", "content": "GlobalTech Solutions may terminate this agreement with 30 days written notice for any material breach, or without cause with 90 days notice. Meridian Ventures may only terminate for GlobalTech Solutions insolvency or material breach with 180 days cure period."},
        {"section": "7.1", "page": 52, "title": "Liability Cap", "content": "In no event shall either party's total liability exceed $500,000 regardless of the nature of the claim, including in cases of gross negligence or willful misconduct."},
        {"section": "8.2", "page": 58, "title": "Data Sharing", "content": "Meridian Ventures grants GlobalTech Solutions irrevocable access to all customer data, sales analytics, and market intelligence gathered during the partnership for GlobalTech Solutions' internal use and product development."},
        {"section": "9.4", "page": 67, "title": "Non-Compete Extension", "content": "The exclusivity obligations in Section 5.2 shall survive termination of this agreement for a period of 24 months. During this period, Meridian Ventures shall not distribute any products competing with GlobalTech Solutions' current or future product lines."},
        {"section": "10.1", "page": 71, "title": "Dispute Resolution", "content": "All disputes shall be resolved through binding arbitration in Delaware, USA under AAA rules. Meridian Ventures waives its right to participate in class actions."}
    ],
    "key_financials": {
        "total_value": 1800000,
        "annual_minimum": 600000,
        "revenue_share_pct": 35,
        "liability_cap": 500000,
        "penalty_schedule": "Schedule C — not provided"
    }
}, indent=2)

SYSTEM_PROMPT = f"""You are the Analyst agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Mapper. You receive enterprise decision documents and extract ALL critical information into a structured breakdown. You do NOT evaluate or judge the merits — you map every key element thoroughly and precisely so other agents can analyze it.

YOUR VOICE: Precise, neutral, clinical. Like a senior analyst preparing a comprehensive briefing book for a board meeting. You are thorough and miss nothing.

WHEN YOU RECEIVE A MESSAGE asking you to analyze a document, produce a structured breakdown. Extract: all parties, financial terms, key clauses with section/page references where available, commitments, deadlines, and anything a reviewer should examine closely.

WHICH DOCUMENT TO ANALYZE:
- If the user's message contains a document (for example, text between "DOCUMENT START" and "DOCUMENT END" markers, or any substantial contract / agreement text), analyze THAT document. Work only from the text provided — quote real clauses and do not invent sections or page numbers that are not present.
- If the user's message is only a short trigger with no document attached, analyze the reference contract below instead.

REFERENCE CONTRACT (use only when no document is provided in the message):
{CONTRACT_DATA}

OUTPUT FORMAT: Use clear headers and bullet points. Include exact section numbers and page references for every clause. End your analysis by stating: "Forwarding to @sentinelops-devils-advocate and @sentinelops-precedent for parallel review."

CRITICAL RULES:
- Extract EVERY section — do not skip any clause
- Always cite the exact page number and section number
- Flag any terms that seem one-sided or unusual (but do not evaluate them — just note them)
- Be complete — the other agents depend on your thoroughness
- Keep your output focused and structured, not narrative"""

FALLBACK_RESPONSE = """STRUCTURED CONTRACT BREAKDOWN

Document: GlobalTech Solutions Partnership Agreement (74 pages)
Parties: Meridian Ventures Ltd ↔ GlobalTech Solutions Inc
Value: $1,800,000 over 3 years | Annual minimum: $600,000

Key Clauses Extracted:
• Section 1.2 (p.8): 35% revenue share on all EMEA/APAC distribution
• Section 2.1 (p.12): "Best efforts" commitment — undefined, no KPIs
• Section 3.4 (p.19): $600K annual minimum purchase, penalties in Schedule C
• Section 4.1 (p.27): All IP improvements transfer to GlobalTech automatically
• Section 5.2 (p.34): Exclusive EMEA distribution rights
• Section 6.3 (p.41): GlobalTech exits in 90 days; Meridian needs 180-day cure
• Section 7.1 (p.52): $500K liability cap on $1.8M deal
• Section 8.2 (p.58): Irrevocable customer data access to GlobalTech
• Section 9.4 (p.67): 24-month post-termination non-compete
• Section 10.1 (p.71): Binding arbitration in Delaware, class action waiver

Key Financial Terms:
• Total deal value: $1,800,000
• Annual minimum commitment: $600,000
• Revenue share: 35% to GlobalTech
• Liability cap: $500,000 (27.8% of deal value)
• Penalty schedule: Referenced in Schedule C but NOT provided

Flagged for Review:
• "Best efforts" (Section 2.1) is undefined — no KPIs, no benchmarks
• IP auto-transfer (Section 4.1) — one-sided, no compensation
• Termination asymmetry (Section 6.3) — GlobalTech 90 days vs Meridian 180 days
• Liability cap (Section 7.1) — significantly below deal value
• Non-compete survives termination by 24 months (Section 9.4)

Analysis complete. Forwarding to @sentinelops-devils-advocate and @sentinelops-precedent for parallel review."""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("analyst")
    logger.info("Analyst Agent starting up...")

    adapter = ResilientAdapter(
        agent_name="analyst",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=2500,
        respond_to=["User"],
        trigger_phrase="flag anything unusual",
        mention_targets=[
            handle("devils_advocate"),
            handle("precedent"),
        ],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Analyst Agent connected to Band. Waiting for trigger...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

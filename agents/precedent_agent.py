"""
SentinelOps - Precedent Agent (Agent 3)
Role: The Historian

Activates in parallel with Devil's Advocate when Analyst posts.
Searches company institutional memory and surfaces relevant history.
Uses OpenAI SDK adapter for LLM reasoning.

Run with: python agents/precedent_agent.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config

from openai_adapter import OpenAIAdapter
from scenario_loader import load_company_history, format_history_for_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.precedent")

# Load company history from JSON at startup - all entries, regardless of scenario
history = load_company_history()
history_text = format_history_for_prompt(history)

SYSTEM_PROMPT = f"""You are the Precedent Agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Historian. You hold the company's institutional memory. When a decision is being evaluated - whether it is a partnership contract, a vendor selection, or any strategic choice - you search the company's past and surface what the current team has forgotten or never knew. Previous contracts, board resolutions, vendor relationships, deals that went wrong, deals that went right.

YOUR VOICE: Like a senior executive who has been at Meridian Ventures for 15 years and remembers everything. Calm, authoritative, narrative. You speak in specifics - dates, dollar amounts, names. You connect past events to present decisions. You say things like "I remember when we tried this before" and "the board addressed this exact issue in 2023."

MERIDIAN VENTURES COMPANY HISTORY (your institutional memory):
{history_text}

WHEN YOU RECEIVE THE ANALYST'S BREAKDOWN: Search the company history above for any entries relevant to the document, proposal, or vendor evaluation being reviewed. Look for:
1. DIRECT HISTORY with the vendor, partner, or provider in question
2. PAST CONTRACTS or vendor relationships with similar terms, clauses, or patterns that went well or badly
3. BOARD RESOLUTIONS or directives that may be violated or supported by the current proposal
4. BENCHMARK DEALS that show what good terms look like

OUTPUT FORMAT:
Use these section headers in ALL CAPS, each on its own line with a blank line before and after: DIRECT HISTORY, RELEVANT PRECEDENTS, BOARD RESOLUTIONS AT RISK, BENCHMARK COMPARISON

Under each header, begin each entry with the date in [YYYY-MM-DD] format. Cite specific amounts and outcomes.

After each entry, add a line prefixed with "Connection:" that draws the explicit link between that past event and the current decision.

End by stating: "Forwarding institutional memory to @sentinelops-risk for risk scoring."

FORMATTING RULES (CRITICAL):
Do NOT use markdown syntax of any kind.
Do NOT use **bold**, *italic*, ### headers, or --- dividers.
Do NOT use bullet points with - or * characters.
Use CAPS for section headers instead (e.g. DIRECT HISTORY, RELEVANT PRECEDENTS).
Use numbered lists (1. 2. 3.) for sequential items.
Use > for emphasis on key findings (e.g. > Board resolution violated).
Use plain dashes for visual separation: ────────────────────
Dollar amounts and percentages should stand alone on their own line.
Keep paragraphs short - 2-3 sentences maximum.
The output must be readable as plain text in a chat window.

CRITICAL RULES:
Be specific - cite dates, dollar amounts, and names from the history.
Draw EXPLICIT connections between past events and current contract or proposal terms.
If a board resolution or directive would be violated, flag it prominently.
If the company has been burned by similar language or vendor patterns before, say so clearly."""

FALLBACK_RESPONSE = """INSTITUTIONAL MEMORY REPORT

DIRECT HISTORY WITH THIS VENDOR:
March 2023: GlobalTech filed a payment dispute against our portfolio company TechBridge Ltd for $142K. Settled for $89K. TechBridge CEO noted "aggressive billing practices." TechBridge no longer works with GlobalTech.

April 2025 - 12 months ago - Meridian evaluated a GlobalTech partnership and abandoned it at the LOI stage. Due diligence file documents a pattern of surprise penalty clauses in Schedule C. We chose not to proceed. Those reasons are on file.

RELEVANT CONTRACT PRECEDENTS:
1. [2022-11-08] DataStream Inc: Identical "best efforts" language. Clause unenforceable. Lost $340,000 with no remedy.
Connection: The current contract uses the same undefined "best efforts" language that cost us $340K.

2. [2021-06-12] NovaCorp: 3-year exclusivity, no change-of-control. Acquired at month 14. Locked out for 20 months. Lost ~$780,000.
Connection: The proposed exclusivity clause has no change-of-control protection - same trap.

BOARD RESOLUTIONS AT RISK:
[2023-09-20] BRD-2023-47: Prohibits IP transfer without board approval. Section 4.1 violates this resolution directly.
> Board resolution violated.

BENCHMARK COMPARISON:
[2024-01-30] Vertex Systems ($2.1M): Liability cap 100%, 90-day mutual exit, IP retained by Meridian. This is what a good deal looks like. The current proposal falls short on every benchmark metric.

History says: we avoided this vendor once, were burned by the same language twice, and are about to violate a board resolution.

Forwarding institutional memory to @sentinelops-risk for risk scoring."""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("precedent")
    logger.info("Precedent Agent starting up (OpenAI SDK adapter)...")

    adapter = OpenAIAdapter(
        agent_name="precedent",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=2500,
        respond_to=["sentinelops-analyst"],
        mention_targets=["karabomatsepane16/sentinelops-risk"],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Precedent Agent connected. Waiting for Analyst's output...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())

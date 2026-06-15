#!/usr/bin/env python3
"""
SentinelOps - Dashboard Server

Serves the live dashboard and collects real-time events from agents.
Agents POST events to /api/event as they process messages through Band.
Dashboard polls /api/events to display live agent activity.

Can also trigger analysis via /api/trigger (sends message to Band room).

Usage: python server.py
Then open http://localhost:8080
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.server")

events: list[dict] = []
events_lock = threading.Lock()

ROOM_ID = "5d859933-e447-49ea-9f6e-d643b1c0b9a9"

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


TRIGGER_MESSAGES = {
    "a": "@sentinelops-analyst Analyze the GlobalTech Solutions Partnership Agreement (Scenario A). Extract all key clauses, financial terms, and flag anything unusual.",
    "b": "@sentinelops-analyst Analyze the Cloud Infrastructure Vendor proposals (Scenario B - vendor selection). Parse all three vendor proposals, extract pricing, SLAs, exit terms, and flag anything unusual.",
}


def trigger_analysis(scenario="a"):
    """Send a trigger message to the Band room via REST API."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
        from band.client.rest import AsyncRestClient, ChatMessageRequest, ChatMessageRequestMentionsItem
        from band.config import load_agent_config

        analyst_id, _ = load_agent_config("analyst")
        _, briefing_key = load_agent_config("briefing")
        rest_url = os.getenv("THENVOI_REST_URL", "https://app.band.ai/")
        content = TRIGGER_MESSAGES.get(scenario, TRIGGER_MESSAGES["a"])

        async def send():
            client = AsyncRestClient(api_key=briefing_key, base_url=rest_url)
            await client.agent_api_messages.create_agent_chat_message(
                chat_id=ROOM_ID,
                message=ChatMessageRequest(
                    content=content,
                    mentions=[ChatMessageRequestMentionsItem(id=analyst_id)],
                ),
            )
            logger.info("Trigger message sent to Band room (scenario %s)", scenario.upper())

        loop = asyncio.new_event_loop()
        loop.run_until_complete(send())
        loop.close()
        return True
    except Exception as e:
        logger.error("Failed to trigger analysis: %s", e)
        return False


def send_followup(question):
    """Send a human follow-up question to the Band room via the analyst agent."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
        from band.client.rest import AsyncRestClient, ChatMessageRequest, ChatMessageRequestMentionsItem
        from band.config import load_agent_config

        briefing_id, _ = load_agent_config("briefing")
        _, analyst_key = load_agent_config("analyst")
        rest_url = os.getenv("THENVOI_REST_URL", "https://app.band.ai/")

        async def send():
            client = AsyncRestClient(api_key=analyst_key, base_url=rest_url)
            await client.agent_api_messages.create_agent_chat_message(
                chat_id=ROOM_ID,
                message=ChatMessageRequest(
                    content=f"@sentinelops-briefing {question}",
                    mentions=[ChatMessageRequestMentionsItem(id=briefing_id)],
                ),
            )
            logger.info("Follow-up question sent to Band room")

        loop = asyncio.new_event_loop()
        loop.run_until_complete(send())
        loop.close()
        return True
    except Exception as e:
        logger.error("Failed to send follow-up: %s", e)
        return False


def _send_api_headers(handler):
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    for k, v in NO_CACHE_HEADERS.items():
        handler.send_header(k, v)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_path = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
            with open(html_path, "rb") as f:
                self.wfile.write(f.read())
            return

        if parsed.path == "/api/status":
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            with events_lock:
                agent_statuses = {}
                for e in events:
                    if e.get("type") == "status":
                        agent_statuses[e["agent"]] = e["status"]
                    elif e.get("type") == "message":
                        agent_statuses[e["agent"]] = "complete"
            self.wfile.write(json.dumps({
                "status": "ok",
                "event_count": len(events),
                "agents": agent_statuses,
            }).encode())
            return

        if parsed.path == "/api/events":
            qs = parse_qs(parsed.query)
            after = int(qs.get("after", ["0"])[0])
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            with events_lock:
                data = events[after:]
            self.wfile.write(json.dumps(data).encode())
            return

        if parsed.path == "/api/reset":
            with events_lock:
                events.clear()
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/event":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                event = json.loads(body)
                event.setdefault("timestamp", time.time())
                with events_lock:
                    events.append(event)
                    if event.get("agent") == "briefing" and event.get("type") == "message":
                        events.append({
                            "type": "pipeline_complete",
                            "agent": "system",
                            "content": event.get("content", ""),
                            "timestamp": time.time(),
                        })
                logger.info("Event received: agent=%s type=%s", event.get("agent", "?"), event.get("type", "?"))
            except json.JSONDecodeError:
                logger.warning("Malformed event body: %s", body[:200])
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        if self.path == "/api/trigger":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(body) if body.strip() else {}
            except json.JSONDecodeError:
                payload = {}
            scenario = payload.get("scenario", "a")
            with events_lock:
                events.clear()
            success = trigger_analysis(scenario)
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({"triggered": success, "scenario": scenario}).encode())
            return

        if self.path == "/api/followup":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                question = payload.get("question", "")
            except json.JSONDecodeError:
                question = ""
            if question:
                with events_lock:
                    events.append({
                        "type": "followup_question",
                        "agent": "human",
                        "content": question,
                        "timestamp": time.time(),
                    })
                success = send_followup(question)
            else:
                success = False
            self.send_response(200)
            _send_api_headers(self)
            self.end_headers()
            self.wfile.write(json.dumps({"sent": success}).encode())
            return

        self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        if args and ('/api/event' in str(args[0]) or '/api/trigger' in str(args[0])):
            logger.info(format, *args)


def main():
    port = int(os.getenv("DASHBOARD_PORT", "8080"))
    server = ThreadedHTTPServer(("0.0.0.0", port), DashboardHandler)

    print(f"""
\033[1m╔══════════════════════════════════════════════════╗
║       SentinelOps - Dashboard Server             ║
╚══════════════════════════════════════════════════╝\033[0m

  Dashboard:  http://localhost:{port}
  API:        http://localhost:{port}/api/status
  Events:     http://localhost:{port}/api/events

\033[2mAgents will POST events to /api/event as they work.
Dashboard polls /api/events for live visualization.\033[0m
""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()

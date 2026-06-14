#!/usr/bin/env python3
"""
SentinelOps — Demo Runner
Launches the dashboard server and all 5 agents.

Usage: python run_demo.py
       python run_demo.py --clean   (clean output for demo recording)
Then open http://localhost:8080 and click "Analyze Contract"
"""

import argparse
import re
import subprocess
import sys
import os
import signal
import time
import threading
from datetime import datetime

AGENTS = [
    ("Analyst",          "agents/analyst_agent.py",          "\033[34m"),  # Blue
    ("Devil's Advocate", "agents/devils_advocate_agent.py",  "\033[31m"),  # Red
    ("Precedent",        "agents/precedent_agent.py",        "\033[35m"),  # Purple
    ("Risk",             "agents/risk_agent.py",             "\033[33m"),  # Yellow
    ("Briefing",         "agents/briefing_agent.py",         "\033[32m"),  # Green
]

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

DISPLAY_NAMES = {
    "Analyst": "Analyst",
    "Devil's Advocate": "Devil's Advocate",
    "Precedent": "Precedent",
    "Risk": "Risk Scorer",
    "Briefing": "Briefing Agent",
}

processes = []
clean_mode = False

_agents_connected = 0
_agents_lock = threading.Lock()
_parallel_announced = False
_parallel_lock = threading.Lock()
_exited = set()
_exited_lock = threading.Lock()


def _ts():
    return datetime.now().strftime("%H:%M:%S")


def _clean_log(symbol, msg):
    print(f"  [{_ts()}]  {symbol} {msg}", flush=True)


def stream_output(pipe, color, name):
    for line in iter(pipe.readline, ''):
        print(f"  {color}[{name}]{RESET} {line}", end='', flush=True)


def stream_output_clean(pipe, name):
    global _agents_connected, _parallel_announced
    display = DISPLAY_NAMES.get(name, name)

    for line in iter(pipe.readline, ''):
        text = line.strip()
        if not text:
            continue

        if "Resilient adapter started" in text:
            with _agents_lock:
                _agents_connected += 1
                if _agents_connected == 5:
                    _clean_log("✓", "All 5 agents connected")
            continue

        if "Trying AI/ML API" in text:
            if name in ("Devil's Advocate", "Precedent"):
                with _parallel_lock:
                    if not _parallel_announced:
                        _parallel_announced = True
                        _clean_log("→", "Devil's Advocate + Precedent working (parallel)...")
            else:
                _clean_log("→", f"{display} working...")
            continue

        if ("succeeded" in text) and ("chars" in text):
            m = re.search(r"\((\d+) chars\)", text)
            chars = m.group(1) if m else "?"
            if name == "Briefing":
                _clean_log("✓", "Pipeline complete — Executive brief generated")
            else:
                _clean_log("✓", f"{display} complete — {chars} chars")
            continue

        if "AI/ML API failed" in text:
            _clean_log("⚠", f"{display}: AI/ML API failed, trying fallback...")
            continue

        if "Featherless" in text and "failed" in text:
            _clean_log("⚠", f"{display}: Featherless failed, trying fallback...")
            continue

        if "All providers failed" in text:
            _clean_log("⚠", f"{display} — all providers failed, using hardcoded response")
            continue

        if name == "Server" and "Event received" in text and "type=message" in text:
            m = re.search(r"agent=(\S+)", text)
            if m:
                agent_label = m.group(1).replace("sentinelops-", "").replace("_", " ").title()
                _clean_log("↓", f"Dashboard received {agent_label} report")
            continue


def cleanup(signum=None, frame=None):
    if clean_mode:
        print(f"\n  [{_ts()}]  ■ Shutting down...", flush=True)
    else:
        print(f"\n{BOLD}Shutting down all processes...{RESET}")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    if not clean_mode:
        print(f"{DIM}All processes stopped.{RESET}")
    sys.exit(0)


def main():
    global clean_mode

    parser = argparse.ArgumentParser(description="SentinelOps Demo Runner")
    parser.add_argument("--clean", action="store_true",
                        help="Clean output for demo video recording")
    args = parser.parse_args()
    clean_mode = args.clean

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    python = sys.executable
    cwd = os.path.dirname(os.path.abspath(__file__))

    base_env = {**os.environ}
    if clean_mode:
        base_env["SENTINELOPS_CLEAN"] = "1"

    print(f"""
{BOLD}╔══════════════════════════════════════════════════╗
║          SentinelOps — Demo Runner               ║
║     Multi-Agent Decision Intelligence            ║
╚══════════════════════════════════════════════════╝{RESET}
""")

    # Start dashboard server first
    if not clean_mode:
        print(f"  \033[36m●{RESET} Starting {BOLD}Dashboard Server{RESET} on http://localhost:8080 ...")
    server_proc = subprocess.Popen(
        [python, "server.py"],
        cwd=cwd,
        env=base_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(server_proc)
    if clean_mode:
        t = threading.Thread(target=stream_output_clean, args=(server_proc.stdout, "Server"), daemon=True)
    else:
        t = threading.Thread(target=stream_output, args=(server_proc.stdout, "\033[36m", "Server"), daemon=True)
    t.start()
    time.sleep(1)

    # Start all agents
    for name, script, color in AGENTS:
        if not clean_mode:
            print(f"  {color}●{RESET} Starting {BOLD}{name}{RESET} agent...")
        proc = subprocess.Popen(
            [python, script],
            cwd=cwd,
            env={**base_env, "PYTHONPATH": os.path.join(cwd, "agents")},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(proc)
        if clean_mode:
            t = threading.Thread(target=stream_output_clean, args=(proc.stdout, name), daemon=True)
        else:
            t = threading.Thread(target=stream_output, args=(proc.stdout, color, name), daemon=True)
        t.start()
        time.sleep(0.5)

    if clean_mode:
        print(f"  {DIM}Dashboard: http://localhost:8080{RESET}")
        print(f"  {DIM}Waiting for agents to connect...{RESET}")
        print()
    else:
        print(f"""
{BOLD}Dashboard + 5 agents are running.{RESET}

  {BOLD}Dashboard:{RESET}  http://localhost:8080
  Click "Analyze Contract" to trigger the full pipeline.

  {DIM}The dashboard will:{RESET}
    1. Send a trigger message to Band
    2. Agents coordinate through Band in real time
    3. Live results appear on the dashboard

  {DIM}If APIs have no funds, demo mode activates automatically.{RESET}

{DIM}Press Ctrl+C to stop everything.{RESET}
""")

    try:
        while True:
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    with _exited_lock:
                        if i in _exited:
                            continue
                        _exited.add(i)
                    if i == 0:
                        if clean_mode:
                            _clean_log("✗", f"Dashboard server exited (code {proc.returncode})")
                        else:
                            print(f"  \033[36m✗{RESET} Dashboard server exited with code {proc.returncode}")
                    else:
                        name, script, color = AGENTS[i - 1]
                        if clean_mode:
                            _clean_log("✗", f"{DISPLAY_NAMES.get(name, name)} exited (code {proc.returncode})")
                        else:
                            print(f"  {color}✗{RESET} {name} agent exited with code {proc.returncode}")
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()

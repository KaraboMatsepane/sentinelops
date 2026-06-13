#!/usr/bin/env python3
"""
SentinelOps — Demo Runner
Launches the dashboard server and all 5 agents.

Usage: python run_demo.py
Then open http://localhost:8080 and click "Analyze Contract"
"""

import subprocess
import sys
import os
import signal
import time
import threading

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

processes = []


def stream_output(pipe, color, name):
    for line in iter(pipe.readline, ''):
        print(f"  {color}[{name}]{RESET} {line}", end='', flush=True)


def cleanup(signum=None, frame=None):
    print(f"\n{BOLD}Shutting down all processes...{RESET}")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"{DIM}All processes stopped.{RESET}")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    python = sys.executable
    cwd = os.path.dirname(os.path.abspath(__file__))

    print(f"""
{BOLD}╔══════════════════════════════════════════════════╗
║          SentinelOps — Demo Runner               ║
║     Multi-Agent Decision Intelligence            ║
╚══════════════════════════════════════════════════╝{RESET}
""")

    # Start dashboard server first
    print(f"  \033[36m●{RESET} Starting {BOLD}Dashboard Server{RESET} on http://localhost:8080 ...")
    server_proc = subprocess.Popen(
        [python, "server.py"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(server_proc)
    t = threading.Thread(target=stream_output, args=(server_proc.stdout, "\033[36m", "Server"), daemon=True)
    t.start()
    time.sleep(1)

    # Start all agents
    for name, script, color in AGENTS:
        print(f"  {color}●{RESET} Starting {BOLD}{name}{RESET} agent...")
        proc = subprocess.Popen(
            [python, script],
            cwd=cwd,
            env={**os.environ, "PYTHONPATH": os.path.join(cwd, "agents")},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(proc)
        t = threading.Thread(target=stream_output, args=(proc.stdout, color, name), daemon=True)
        t.start()
        time.sleep(0.5)

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
                    if i == 0:
                        print(f"  \033[36m✗{RESET} Dashboard server exited with code {proc.returncode}")
                    else:
                        name, script, color = AGENTS[i - 1]
                        print(f"  {color}✗{RESET} {name} agent exited with code {proc.returncode}")
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
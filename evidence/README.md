# SentinelOps — Live Run Evidence

This folder contains evidence from the live SentinelOps demonstration run showing all five agents coordinating through Band in real time.

## Contents

| File | Description | Status |
|------|-------------|--------|
| `band_room_screenshot.png` | Screenshot of the Band room showing all five agents connected and active | To be captured before submission |
| `live_run_transcript.md` | Full transcript of the live analysis session (Scenario A) | To be captured before submission |

> **Note:** The GitHub Pages dashboard (`docs/index.html`) runs in demo mode, replaying the exact outputs produced during live testing. To capture fresh evidence, run `python run_demo.py --clean` with the dashboard server active and record the terminal output.

## What the Live Run Demonstrates

1. **All five agents connected to Band** — visible in a single Band room
2. **Parallel activation** — Devil's Advocate and Precedent Agent fire simultaneously after Analyst posts
3. **Featherless AI usage** — Precedent Agent calls Featherless AI as its primary provider
4. **AI/ML API usage** — Analyst, Devil's Advocate, Risk, and Briefing use AI/ML API
5. **Complete pipeline** — Document to executive brief in minutes, not days
6. **Zero autonomous decisions** — the system recommends, the human decides

## Notes

- API credentials are stored in `.env` (gitignored) and never committed to the repository
- The GitHub Pages dashboard (`docs/index.html`) runs in verified demo mode — it replays a pre-computed analysis using the exact same outputs produced during the live run
- The live-run server (`server.py`) connects to Band and streams real agent events to the dashboard in real time

## Adding Evidence Before Submission

To capture the Band room screenshot:
1. Open [app.band.ai](https://app.band.ai) and navigate to the SentinelOps room
2. Start all five agents (`python agents/<agent>.py` in separate terminals)
3. Screenshot the room showing all agents listed as connected participants

To capture the live transcript:
1. Run `python run_demo.py --clean` with the dashboard server active
2. Copy the full terminal output into `live_run_transcript.md`
3. Include timestamps and provider annotations from the logs
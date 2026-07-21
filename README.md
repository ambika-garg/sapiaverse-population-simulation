# SF Population Simulation

A generative-agent simulation of San Francisco residents that predicts how the
population would vote on a ballot measure, benchmarked against real-world results.

## Status
Phase 3 — guided build. Step 0: project foundation complete.

## Setup
1. `uv sync`
2. `cp .env.example .env` and add your `ANTHROPIC_API_KEY`
3. `uv run pre-commit install`
4. `uv run pytest`

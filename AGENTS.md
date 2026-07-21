AGENTS.md — SF Population Simulation

Project rules for Google Antigravity (also read by Claude Code / Cursor). Antigravity runs a Plan → Execute → Verify loop. Obey the working agreement below: plan the current step, implement only that step, verify against its checkpoint, then stop and wait for me.

1. Mission

Build a production-shaped generative-agent simulation of San Francisco residents that predicts how a real population would vote on a ballot measure, then benchmarks the prediction against reality.

Pipeline in one line: **Census microdata → 30 synthetic SF residents (demographics

OCEAN) → run a behavioral scenario (a Prop-X vote) → aggregate → benchmark against the real result → reflect → run a second scenario and measure the delta.**

Conceptual basis: Park et al. 2023, Generative Agents: Interactive Simulacra of Human Behavior. We reuse the reflection idea (agents write a short reflection that updates a behavioral parameter). We are NOT building document RAG — there are no documents, no OCR, no chunking, no vector store in the core.

Ground-truth benchmark: the real SF Proposition F (2021) capped third-party delivery fees at 15% and passed with 60.8% Yes. Our simulated "Prop X" mirrors it. Closing the gap to 60.8% — and explaining the gap — is the highest-value deliverable.

2. Working agreement (read this every step)
One step at a time. Implement only the current roadmap step (Section 6). Do not scaffold future steps "to save time." Finish, verify, stop.
Plan before code. State the plan for the step, the files you'll touch, and the checkpoint you'll verify, then implement.
Verify against the checkpoint before declaring a step done. If you can't meet it, say so — don't paper over it.
Never touch the human-owned zones (Section 9) without explicit sign-off. For those, propose an approach and wait; do not silently generate the logic.
Ask when the spec is ambiguous. A wrong assumption compounds. One good question beats ten wrong lines.
Small, reviewable diffs. Prefer a working vertical slice over a broad half-built layer.
3. Tech stack (do not substitute without asking)
Language: Python 3.11+ (backend/sim), TypeScript (UI).
Dependency manager: uv. All Python deps go through uv add; never pip install into the system env.
API layer: FastAPI + Pydantic v2 (every I/O boundary is a Pydantic model).
Async: httpx + asyncio for LLM fan-out.
LLM: Anthropic (or OpenAI) SDK. Structured output via tool/JSON mode — never regex-parse a model response.
Persistence: SQLite via SQLAlchemy, written Postgres-ready (no SQLite-only SQL). Census raw pulls cached as parquet.
UI: React + TypeScript (Vite). Results dashboard only — not a product SPA.
Observability: structlog + a small per-run token/cost accountant.
Tests: pytest (+ pytest-asyncio), Vitest for UI.
Packaging/CI: Docker + docker-compose (api + ui), GitHub Actions (lint + test).

Deliberately excluded (do not add): Kafka, Kubernetes, Redis, Celery, auth server, vector DB, OCR, document chunking. At n=30 these are complexity smells. If you think one is needed, flag it — don't add it.

4. Architecture — components & contracts

Each component is a module with a single responsibility and a typed boundary. Keep them decoupled; nothing downstream should know how upstream fetched its data.

Component	Input	Output	Rule
Census client	PUMA codes + variable list	raw microdata rows	Only place that knows the Census API exists. Cache to parquet.
Persona synthesis	cached PUMS rows	30 Persona objects	Sample real rows to preserve joint distributions. OCEAN is synthetic + clearly labeled.
Persona store	Persona objects	agent records	SQLite behind a repository interface. Generate once, simulate many.
Scenario registry	—	Scenario spec	Declarative. Prop-X and the $5-credit scenario are config entries, not code forks.
Orchestrator	personas + scenario	raw responses	Owns async fan-out, retries, rate-limit, cache. Keeps the runtime stateless.
Agent runtime	one persona + scenario (+ prior reflection)	validated {vote, reason}	Prompt-build → LLM → Pydantic parse. Smallest testable unit.
Reflection	vote + persona	1-sentence reflection + mutated behavioral param	Persist the param change; it must carry into the next scenario.
Vote aggregator	raw responses	split, top-3 reasons/side, standout agent	Cluster reasons thematically, not by string match.
Benchmark comparator	simulated split	delta vs 60.8% + analysis hooks	First-class output, not a print statement.
Variance harness	scenario config	mean ± spread over seeds	n=30 swings; report the spread.
Config/secrets	env	typed settings	No hardcoded keys, ever.
LLM cache	(persona, scenario, prompt-hash)	cached response	Makes re-runs free + deterministic.

Data flow: Census client → parquet cache → synthesis → persona store → orchestrator → agent runtime → aggregator → benchmark, with reflection writing back to the persona store between scenarios, and config / cache / observability cross-cutting.

5. Repository structure (target)
sf-population-sim/
├── AGENTS.md                  # this file
├── README.md                  # architecture + Part 3 gap analysis (graded)
├── pyproject.toml             # uv-managed
├── .env.example               # documented; real .env is gitignored
├── docker-compose.yml
├── .github/workflows/ci.yml
├── src/
│   ├── config/                # settings, secrets loader
│   ├── census/                # client + parquet cache
│   ├── personas/              # synthesis, OCEAN, models, store
│   ├── scenarios/             # registry + scenario specs
│   ├── simulation/            # orchestrator, agent runtime, reflection
│   ├── analytics/             # aggregator, benchmark, variance
│   ├── observability/         # structlog config, cost accountant
│   └── api/                   # FastAPI app + routers + response models
├── ui/                        # Vite + React + TS dashboard
├── data/                      # parquet cache, sqlite db (gitignored)
├── tests/                     # mirrors src/
└── notebooks/                 # optional exploration only, not the deliverable

Rule: one feature per module. No main.py god-file. New capability → new module under the right package.

6. Implementation roadmap (execute in order, one at a time)

Each step ends at a checkpoint. Do not start step N+1 until I confirm step N.

Foundation — repo, uv, config/secrets, pre-commit, .gitignore, README stub. Checkpoint: repo pushes; secrets load from .env; hello-world import runs.
Census client — pull PUMS for chosen SF PUMAs, cache to parquet. Checkpoint: parquet of microdata + a sanity table that looks SF-like.
Persona synthesis + store — sample 30 rows, map to ~8–10 neighborhoods, add names + labeled OCEAN, persist. Checkpoint: 30 coherent agents in DB; distribution table realistic.
Agent runtime — prompt builder + LLM client + Pydantic-validated {vote, reason} for one agent. Checkpoint: one clean vote; unit test passes with a mocked LLM.
Scenario registry + orchestrator — define BOTH scenarios; async fan-out; retries; rate-limit; response cache. Checkpoint: full Prop-X run → 30 cached responses; cost logged.
Aggregation + benchmark + variance — split, top-3 reasons/side, standout, delta vs 60.8%, multi-seed spread. Checkpoint: Part 2 + Part 3 numbers reproduce.
Reflection (Part 4a) — post-vote reflection mutates one persisted behavioral param. Checkpoint: each agent has a reflection + a saved, changed param.
Second scenario + delta (Part 4b) — run $5-credit scenario carrying reflection state; compute per-agent vote deltas. Checkpoint: behavioral-delta table A→B.
FastAPI — /population, /simulate, /results with Pydantic responses. Checkpoint: uvicorn up; endpoints return clean JSON.
UI dashboard — population table, vote split, reason breakdown, benchmark delta, A/B comparison, reflection viewer. Checkpoint: renders end-to-end against the API.
Observability + tests + hardening — structlog, cost accounting, coverage on the spine, error handling. Checkpoint: green suite + run emits cost/log summary.
Docker + CI — Dockerfile(s), compose, GitHub Actions (lint+test). Checkpoint: docker compose up runs the stack; CI green.
Deploy + README — deploy target + README with diagram, decisions, "what I'd add for scale," and the Part 3 gap analysis. Checkpoint: live URL; README complete.
7. Coding standards

Python: PEP 8, full type hints, Pydantic v2 models at every boundary, Google-style docstrings on public functions, ruff for lint+format, no magic numbers (named constants), no bare except. Pure functions where possible; side effects (DB, network, LLM) isolated behind interfaces.

TypeScript: strict mode on, no any, typed API client, components small and presentational, data-fetching separated from rendering.

General: meaningful names over comments; comment the why, not the what. No dead code, no commented-out blocks committed.

8. Domain rules (get these right — they carry the grade)
Population size is 30 agents. Not 25, not 100.
Personas must be coherent. Never sample demographic marginals independently (that yields 82-year-old software engineers). Sample joint rows from PUMS.
OCEAN is synthetic. Generate Big Five scores with light, clearly-labeled demographic priors. Never present them as Census-derived.
Every vote must reason from the agent's specific context — demographics + neighborhood + OCEAN. A generic reason that ignores the persona is a bug.
Benchmark constant: 60.8% Yes. Do not hardcode elsewhere; keep it in one named constant.
Expect to undershoot 60.8%. The likely cause is that Census gives residents but the measure was decided by voters (older, higher-income, higher-turnout). Do not "tune" prompts to fake the number — the honest gap analysis is the deliverable.
Scenario 2 ("DoorDash offers you $5 to vote No") must reuse scenario-1 reflection state so the delta reflects both the incentive and the reflection.
9. Human-owned zones (DO NOT auto-generate — propose, then wait)

These three carry the interview signal and I must be able to defend them. For each, write a short plan and pause for my sign-off before generating logic:

Persona-synthesis sampling logic (how PUMS rows → agents, OCEAN priors).
Prompt / OCEAN construction (how persona context is injected into the vote prompt).
The Part 3 gap analysis (the written reasoning — I write this; you may only assemble the numbers it cites).

Everything else — scaffolding, Docker, CI, UI components, test harness, boilerplate — you may drive.

10. LLM discipline
Structured output only. Enforce a strict schema (tool use / JSON mode) → parse with Pydantic. If a response fails validation, retry with a repair prompt; never regex.
Force the binary. The vote is Yes/No — the model must not hedge or refuse.
Cache every call keyed on (persona_id, scenario_id, prompt_hash).
Account for cost. Log tokens + estimated $ per run; surface a run summary.
Determinism where it matters. Fix seeds/temperature in the variance harness so spread is measured, not accidental.
11. Security & safety
Secrets come from env only; .env is gitignored; commit .env.example.
Never print or log API keys or full secrets.
Command execution: run in Antigravity's Auto (not Turbo) mode for this project. Allow-list: uv, pytest, ruff, git, docker, npm/vite. Deny: anything destructive (rm -rf, force-push to main, DB drops) without my confirmation.
No network calls in tests — mock the Census API and the LLM.
12. Definition of done (every step)

A step is done only when: it meets its checkpoint; code is typed + linted; new logic has a test (mocked externals); no secret is committed; and you've written one line on how this component fits the architecture. Then stop and wait.

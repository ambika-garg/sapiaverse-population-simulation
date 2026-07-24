"""Run the full experiment: baseline vote, arm B, reflection, arm C.

uv run python -m scripts.run_simulation
AGENT_LIMIT=3 uv run python -m scripts.run_simulation   # smoke test
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from analytics.aggregate import (
    cluster_reasons,
    most_interesting,
    segment_split,
    summarise,
)
from analytics.benchmark import behavioural_delta, benchmark
from census.cache import load_or_fetch
from census.client import CensusClient
from config.settings import get_settings
from llm.client import LLMClient
from personas.builder import build_personas
from personas.decode import decode_frame
from personas.models import clamp_stance
from personas.sampling import stratified_sample
from scenarios.registry import PROP_X, PROP_X_CREDIT
from simulation.orchestrator import run_reflections, run_scenario

RESULTS_PATH = Path("data/results.json")
logger = logging.getLogger(__name__)


def build_client(settings) -> LLMClient:
    """Construct the LLM client from settings."""
    return LLMClient(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        max_concurrency=settings.llm_max_concurrency,
    )


def load_personas(settings):
    """Rebuild the same 30 residents deterministically from the cached pull."""
    census = CensusClient(api_key=settings.census_api_key)
    pumas = census.discover_sf_pumas()
    frame = load_or_fetch(lambda: census.fetch_pums(pumas["PUMA"].tolist()))
    decoded = decode_frame(frame, census.fetch_all_labels())
    return build_personas(stratified_sample(decoded), pumas)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    client = build_client(settings)

    personas = load_personas(settings)
    limit = int(os.getenv("AGENT_LIMIT", "0"))
    if limit:
        personas = personas[:limit]
    print(f"Loaded {len(personas)} residents\n")

    # --- baseline: this is the Part 2 / Part 3 number ------------------------
    baseline_votes = await run_scenario(client, personas, PROP_X)
    baseline = summarise(baseline_votes)

    # --- arm B: incentive only, no reflection -------------------------------
    arm_b_votes = await run_scenario(client, personas, PROP_X_CREDIT)
    arm_b = summarise(arm_b_votes)

    # --- arm C: reflect on baseline, then face the incentive ----------------
    reflections = await run_reflections(client, personas, baseline_votes)
    stances = {r.agent_id: clamp_stance(r.stance_delta) for r in reflections}
    reflection_text = {r.agent_id: r.text for r in reflections}

    arm_c_votes = await run_scenario(
        client,
        personas,
        PROP_X_CREDIT,
        stances=stances,
        reflections=reflection_text,
    )
    arm_c = summarise(arm_c_votes)

    # --- analysis ------------------------------------------------------------
    mark = benchmark(baseline.yes_pct)
    baseline.themes_yes = await cluster_reasons(client, baseline.yes_reasons)
    baseline.themes_no = await cluster_reasons(client, baseline.no_reasons)
    standout = most_interesting(baseline_votes, personas)
    by_id = {p.agent_id: p for p in personas}

    print("\n" + "=" * 72)
    print(f"BASELINE (Prop X)     {baseline.yes} Yes / {baseline.no} No  = {baseline.yes_pct}% Yes")
    print(
        f"ARM B  (+$5)          {arm_b.yes} Yes / {arm_b.no} No  "
        f"= {arm_b.yes_pct}% Yes   "
        f"({behavioural_delta(baseline.yes_pct, arm_b.yes_pct):+.1f} pts)"
    )
    print(
        f"ARM C  (reflect +$5)  {arm_c.yes} Yes / {arm_c.no} No  "
        f"= {arm_c.yes_pct}% Yes   "
        f"({behavioural_delta(baseline.yes_pct, arm_c.yes_pct):+.1f} pts)"
    )
    print("-" * 72)
    print(mark.describe())
    print(
        f"Reflection effect: {behavioural_delta(arm_b.yes_pct, arm_c.yes_pct):+.1f} "
        "points vs incentive alone"
    )
    print("-" * 72)
    print("Top Yes themes:", baseline.themes_yes)
    print("Top No themes: ", baseline.themes_no)

    if standout:
        person = by_id[standout.agent_id]
        print(
            f"\nMost interesting: {person.name}, {person.age}, "
            f"{person.occupation}, household ${person.household_income:,}"
        )
        print(f"  voted {standout.vote} - {standout.reason}")

    print("-" * 72)
    print("By neighbourhood (n shown - small cells are noisy):")
    for name, stats in segment_split(baseline_votes, personas, "neighborhood").items():
        print(f"  {name:<44} {stats['yes']}/{stats['n']} Yes ({stats['yes_pct']}%)")

    print("-" * 72)
    print("Usage:", client.usage.summary())
    print("=" * 72)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(
            {
                "population_size": len(personas),
                "model": settings.llm_model,
                "baseline": {
                    "yes": baseline.yes,
                    "no": baseline.no,
                    "yes_pct": baseline.yes_pct,
                    "themes_yes": baseline.themes_yes,
                    "themes_no": baseline.themes_no,
                },
                "arm_b": {"yes": arm_b.yes, "no": arm_b.no, "yes_pct": arm_b.yes_pct},
                "arm_c": {"yes": arm_c.yes, "no": arm_c.no, "yes_pct": arm_c.yes_pct},
                "benchmark": {
                    "simulated": mark.simulated_yes_pct,
                    "actual": mark.actual_yes_pct,
                    "delta": mark.delta_pct_points,
                },
                "by_neighborhood": segment_split(baseline_votes, personas, "neighborhood"),
                "agents": [
                    {
                        "agent_id": p.agent_id,
                        "name": p.name,
                        "age": p.age,
                        "neighborhood": p.neighborhood,
                        "occupation": p.occupation,
                        "household_income": p.household_income,
                        "baseline_vote": next(
                            v.vote for v in baseline_votes if v.agent_id == p.agent_id
                        ),
                        "baseline_reason": next(
                            v.reason for v in baseline_votes if v.agent_id == p.agent_id
                        ),
                        "arm_b_vote": next(v.vote for v in arm_b_votes if v.agent_id == p.agent_id),
                        "arm_c_vote": next(v.vote for v in arm_c_votes if v.agent_id == p.agent_id),
                        "reflection": reflection_text.get(p.agent_id, ""),
                        "stance": stances.get(p.agent_id, 0.0),
                    }
                    for p in personas
                ],
            },
            indent=2,
        )
    )
    print(f"Wrote {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())

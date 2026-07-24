"""Generate the markdown agent table for the README from data/results.json.

uv run python -m scripts.make_agent_table
"""

import json
from pathlib import Path

RESULTS_PATH = Path("data/results.json")


def main() -> None:
    data = json.loads(RESULTS_PATH.read_text())
    agents = data.get("agents", [])

    print(
        "| # | Name | Age | Neighbourhood | Occupation | HH income "
        "| Baseline | Arm B | Arm C | Stance |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")

    for index, agent in enumerate(agents, start=1):
        print(
            f"| {index} "
            f"| {agent['name']} "
            f"| {agent['age']} "
            f"| {agent['neighborhood']} "
            f"| {agent['occupation']} "
            f"| ${agent['household_income']:,} "
            f"| {agent['baseline_vote']} "
            f"| {agent['arm_b_vote']} "
            f"| {agent['arm_c_vote']} "
            f"| {agent['stance']:+.2f} |"
        )

    flipped_b = sum(1 for a in agents if a["baseline_vote"] != a["arm_b_vote"])
    flipped_c = sum(1 for a in agents if a["baseline_vote"] != a["arm_c_vote"])
    print(
        f"\n*{len(agents)} agents. {flipped_b} changed vote under the incentive "
        f"alone; {flipped_c} changed after reflecting first.*"
    )

    print("\n\n### Neighbourhood split\n")
    print("| Neighbourhood | Yes / n | % |")
    print("|---|---|---|")
    for name, stats in data.get("by_neighborhood", {}).items():
        print(f"| {name} | {stats['yes']}/{stats['n']} | {stats['yes_pct']} |")

    print("\n\n### Sample reflections\n")
    for agent in agents[:3]:
        print(
            f"- **{agent['name']}** (voted {agent['baseline_vote']}, "
            f'stance {agent["stance"]:+.2f}): "{agent["reflection"]}"'
        )


if __name__ == "__main__":
    main()

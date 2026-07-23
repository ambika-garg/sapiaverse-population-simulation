"""Read the stored population back — no network, no Census, database only."""

from src.personas.repository import PersonaRepository


def main() -> None:
    personas = PersonaRepository().list_all()
    print(f"Loaded {len(personas)} personas from the database\n")

    for person in personas[:5]:
        print(
            f"[{person.agent_id}] {person.name}, {person.age} — {person.neighborhood}"
            f" | {person.occupation} | consc {person.ocean.conscientiousness}"
        )


if __name__ == "__main__":
    main()

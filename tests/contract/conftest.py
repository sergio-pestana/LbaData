import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def tournament_payload() -> dict:
    return load_fixture("tournament.json")


@pytest.fixture
def games_phase_payload() -> dict:
    return load_fixture("games_phase.json")


@pytest.fixture
def player_stats_logs_payload() -> dict:
    return load_fixture("player_stats_logs_game1.json")


@pytest.fixture
def team_stats_logs_payload() -> dict:
    return load_fixture("team_stats_logs_game1.json")


@pytest.fixture
def phase_standings_payload() -> dict:
    return load_fixture("phase_standings.json")


# IDs reais correspondentes às fixtures capturadas (ver contracts/go-champs-api-dependency.md)
KNOWN_PHASE_ID = "ede46bb2-21ac-411b-b07f-b93269bebd37"
KNOWN_GAME_ID = "1eb4007b-dc78-42aa-a5a0-70bfe476d4e2"


@pytest.fixture
def known_phase_id() -> str:
    return KNOWN_PHASE_ID


@pytest.fixture
def known_game_id() -> str:
    return KNOWN_GAME_ID

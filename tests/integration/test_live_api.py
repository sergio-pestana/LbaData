"""Teste de integração MANUAL contra a API real do go-champs.

Não roda em CI automática (ver Polish/T049 — pytest.ini exclui este diretório
por padrão). Rodar sob demanda com:

    pytest tests/integration/test_live_api.py -v

Objetivo (Princípio II): detectar, o quanto antes, se a fonte pública e não
documentada oficialmente mudou de estrutura — antes que isso corrompa
silenciosamente uma coleta real.
"""

import os

import pytest

from collector.client import GoChampsClient
from collector.parsers import (
    parse_games,
    parse_phase_standings,
    parse_player_stats_logs,
    parse_team_stats_logs,
    parse_tournament,
)

TOURNAMENT_ID = os.environ.get("LBA_TOURNAMENT_ID", "5bf23f0b-6768-46ec-bcc1-4cd698105413")
PHASE_ID = os.environ.get("LBA_PHASE_ID", "ede46bb2-21ac-411b-b07f-b93269bebd37")


@pytest.fixture(scope="module")
def client() -> GoChampsClient:
    return GoChampsClient(min_interval_seconds=1.5)


def test_tournament_endpoint_still_matches_assumed_shape(client):
    payload = client.get(f"/v1/tournaments/{TOURNAMENT_ID}")
    result = parse_tournament(payload)

    assert result["has_aggregated_player_stats"] is True
    assert len(result["teams"]) > 0
    assert len(result["players"]) > 0


def test_games_endpoint_still_matches_assumed_shape(client):
    payload = client.get("/v1/games", params={"where[phase_id]": PHASE_ID})
    games = parse_games(payload, expected_phase_id=PHASE_ID)

    assert len(games) > 0


def test_player_and_team_stats_logs_still_match_assumed_shape(client):
    games_payload = client.get("/v1/games", params={"where[phase_id]": PHASE_ID})
    games = parse_games(games_payload, expected_phase_id=PHASE_ID)
    finished_games = [g for g in games if g["is_finished_raw"]]
    assert finished_games, "esperava ao menos um jogo finalizado para validar as súmulas"

    game_id = finished_games[0]["id"]

    player_payload = client.get("/v1/player-stats-logs", params={"where[game_id]": game_id})
    player_rows = parse_player_stats_logs(player_payload, expected_game_id=game_id)
    assert len(player_rows) > 0

    team_payload = client.get("/v1/team-stats-logs", params={"where[game_id]": game_id})
    team_rows = parse_team_stats_logs(team_payload, expected_game_id=game_id)
    assert len(team_rows) == 2


def test_phase_standings_endpoint_still_matches_assumed_shape(client):
    payload = client.get(f"/v1/phases/{PHASE_ID}")
    rows = parse_phase_standings(payload)

    assert len(rows) > 0
    assert rows == sorted(rows, key=lambda r: r["posicao"])

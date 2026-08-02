"""Isolamento por torneio/fase em storage.reads (feature 002 — múltiplos
torneios). Roda contra o Supabase real, como test_upserts.py — mesmo padrão
de ids de teste fixos e limpeza ao final."""

from __future__ import annotations

import pytest

from storage.reads import get_games, get_player_game_stats, get_players, get_team_game_stats, get_teams
from storage.supabase_client import get_connection
from storage.upserts import upsert_game, upsert_player, upsert_player_game_stat, upsert_team, upsert_team_game_stat

TOURNAMENT_A = "00000000-0000-0000-0000-0000000000a1"
TOURNAMENT_B = "00000000-0000-0000-0000-0000000000a2"

TEAM_A = "00000000-0000-0000-0000-0000000000a3"
TEAM_B = "00000000-0000-0000-0000-0000000000a4"
PLAYER_A = "00000000-0000-0000-0000-0000000000a5"
PLAYER_B = "00000000-0000-0000-0000-0000000000a6"

PHASE_A = "00000000-0000-0000-0000-0000000000a7"
PHASE_B = "00000000-0000-0000-0000-0000000000a8"
GAME_A = "00000000-0000-0000-0000-0000000000a9"
GAME_B = "00000000-0000-0000-0000-0000000000aa"
PLAYER_STAT_A = "00000000-0000-0000-0000-0000000000ab"
PLAYER_STAT_B = "00000000-0000-0000-0000-0000000000ac"
TEAM_STAT_A = "00000000-0000-0000-0000-0000000000ad"
TEAM_STAT_B = "00000000-0000-0000-0000-0000000000ae"


@pytest.fixture
def two_tournaments():
    """Um time/jogador/jogo/estatística em cada um de dois torneios distintos
    — usados para provar que as leituras nunca misturam torneios diferentes."""
    upsert_team({"id": TEAM_A, "nome": "TESTE Torneio A", "tri_code": "TA1", "cor": None}, TOURNAMENT_A)
    upsert_team({"id": TEAM_B, "nome": "TESTE Torneio B", "tri_code": "TB1", "cor": None}, TOURNAMENT_B)
    upsert_player(
        {"id": PLAYER_A, "nome": "Jogador A", "team_id": TEAM_A, "numero_camisa": "1"}, TOURNAMENT_A
    )
    upsert_player(
        {"id": PLAYER_B, "nome": "Jogador B", "team_id": TEAM_B, "numero_camisa": "2"}, TOURNAMENT_B
    )

    game_a = {
        "id": GAME_A, "phase_id": PHASE_A, "rodada_data": "2026-01-01",
        "time_casa_id": TEAM_A, "time_visitante_id": TEAM_A,
        "placar_casa": 10, "placar_visitante": 5, "status": "processada", "is_finished_raw": True,
    }
    game_b = {**game_a, "id": GAME_B, "phase_id": PHASE_B, "time_casa_id": TEAM_B, "time_visitante_id": TEAM_B}
    upsert_game(game_a)
    upsert_game(game_b)

    stat_common = {
        "jogou": True, "minutos_jogados": 10.0, "pontos": 10, "rebotes_ofensivos": 1,
        "rebotes_defensivos": 1, "assistencias": 1, "roubos": 0, "tocos": 0,
        "faltas_pessoais": 0, "faltas_tecnicas": 0, "faltas_antidesportivas": 0,
        "faltas_desqualificantes": 0, "faltas_desqualificantes_briga": 0, "faltas_flagrantes": 0,
        "faltas_desqualificantes_jogo": 0, "arremessos_2pt_tentados": 1, "arremessos_2pt_convertidos": 1,
        "arremessos_3pt_tentados": 0, "arremessos_3pt_convertidos": 0, "lances_livres_tentados": 0,
        "lances_livres_convertidos": 0, "turnovers": 0, "eficiencia": 5.0, "plus_minus": 1,
    }
    upsert_player_game_stat({"id": PLAYER_STAT_A, "game_id": GAME_A, "player_id": PLAYER_A, "time_id_na_partida": TEAM_A, **stat_common})
    upsert_player_game_stat({"id": PLAYER_STAT_B, "game_id": GAME_B, "player_id": PLAYER_B, "time_id_na_partida": TEAM_B, **stat_common})

    team_stat_common = {
        "vitoria": True, "saldo_pontos": 5, "fiba_group_points": None, "pontos": 10, "pontos_sofridos": 5,
        "arremessos_2pt_tentados": 1, "arremessos_2pt_convertidos": 1, "arremessos_3pt_tentados": 0,
        "arremessos_3pt_convertidos": 0, "lances_livres_tentados": 0, "lances_livres_convertidos": 0,
        "rebotes_ofensivos": 1, "rebotes_defensivos": 1, "assistencias": 1, "roubos": 0, "tocos": 0,
        "turnovers": 0, "faltas": 0, "eficiencia": 5.0, "plus_minus": 1,
    }
    upsert_team_game_stat({"id": TEAM_STAT_A, "game_id": GAME_A, "team_id": TEAM_A, **team_stat_common})
    upsert_team_game_stat({"id": TEAM_STAT_B, "game_id": GAME_B, "team_id": TEAM_B, **team_stat_common})

    yield

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM team_game_stats WHERE id IN (%s, %s)", (TEAM_STAT_A, TEAM_STAT_B))
            cur.execute("DELETE FROM player_game_stats WHERE id IN (%s, %s)", (PLAYER_STAT_A, PLAYER_STAT_B))
            cur.execute("DELETE FROM games WHERE id IN (%s, %s)", (GAME_A, GAME_B))
            cur.execute("DELETE FROM players WHERE id IN (%s, %s)", (PLAYER_A, PLAYER_B))
            cur.execute("DELETE FROM teams WHERE id IN (%s, %s)", (TEAM_A, TEAM_B))
        conn.commit()
    finally:
        conn.close()


def test_get_teams_only_returns_the_requested_tournament(two_tournaments):
    teams_a = get_teams(TOURNAMENT_A)
    assert {str(t["id"]) for t in teams_a} & {TEAM_A, TEAM_B} == {TEAM_A}

    teams_b = get_teams(TOURNAMENT_B)
    assert {str(t["id"]) for t in teams_b} & {TEAM_A, TEAM_B} == {TEAM_B}


def test_get_players_only_returns_the_requested_tournament(two_tournaments):
    players_a = get_players(TOURNAMENT_A)
    assert {str(p["id"]) for p in players_a} & {PLAYER_A, PLAYER_B} == {PLAYER_A}

    players_b = get_players(TOURNAMENT_B)
    assert {str(p["id"]) for p in players_b} & {PLAYER_A, PLAYER_B} == {PLAYER_B}


def test_get_games_accepts_a_list_of_phase_ids(two_tournaments):
    games = get_games([PHASE_A])
    assert {str(g["id"]) for g in games} & {GAME_A, GAME_B} == {GAME_A}

    games_both = get_games([PHASE_A, PHASE_B])
    assert {str(g["id"]) for g in games_both} & {GAME_A, GAME_B} == {GAME_A, GAME_B}


def test_get_player_game_stats_filters_by_phase_ids(two_tournaments):
    """Achado de research.md #3: antes desta feature, get_player_game_stats()
    sem team_id retornava a tabela inteira, sem filtro nenhum de fase."""
    stats_a = get_player_game_stats([PHASE_A])
    assert {str(s["id"]) for s in stats_a} & {PLAYER_STAT_A, PLAYER_STAT_B} == {PLAYER_STAT_A}


def test_get_team_game_stats_filters_by_phase_ids(two_tournaments):
    stats_a = get_team_game_stats([PHASE_A])
    assert {str(s["id"]) for s in stats_a} & {TEAM_STAT_A, TEAM_STAT_B} == {TEAM_STAT_A}

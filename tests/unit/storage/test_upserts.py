"""Testes de idempotência/correção/cancelamento do storage.upserts (Princípio I).

Rodam contra o Supabase real configurado em SUPABASE_DB_* (não há como testar
`ON CONFLICT` de forma fiel sem um Postgres de verdade) — usam ids de teste
fixos e claramente distintos de qualquer dado real, e removem tudo ao final.
"""

from __future__ import annotations

import pytest

from storage.supabase_client import get_connection
from storage.upserts import upsert_game, upsert_player, upsert_player_game_stat, upsert_team

TEST_TEAM_HOME = "00000000-0000-0000-0000-000000000001"
TEST_TEAM_AWAY = "00000000-0000-0000-0000-000000000002"
TEST_PLAYER = "00000000-0000-0000-0000-000000000003"
TEST_GAME = "00000000-0000-0000-0000-000000000004"
TEST_PLAYER_STAT = "00000000-0000-0000-0000-000000000005"
TEST_TOURNAMENT = "00000000-0000-0000-0000-0000000000aa"


def _fetch_one(sql: str, params: tuple):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def _count(table: str, id_value: str) -> int:
    row = _fetch_one(f"SELECT COUNT(*) FROM {table} WHERE id = %s", (id_value,))
    return row[0]


@pytest.fixture
def base_teams_and_player():
    upsert_team({"id": TEST_TEAM_HOME, "nome": "TESTE Home", "tri_code": "TSH", "cor": None}, TEST_TOURNAMENT)
    upsert_team({"id": TEST_TEAM_AWAY, "nome": "TESTE Away", "tri_code": "TSA", "cor": None}, TEST_TOURNAMENT)
    upsert_player(
        {"id": TEST_PLAYER, "nome": "Jogador Teste", "team_id": TEST_TEAM_HOME, "numero_camisa": "99"},
        TEST_TOURNAMENT,
    )
    yield
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM player_game_stats WHERE id = %s", (TEST_PLAYER_STAT,))
            cur.execute("DELETE FROM games WHERE id = %s", (TEST_GAME,))
            cur.execute("DELETE FROM players WHERE id = %s", (TEST_PLAYER,))
            cur.execute("DELETE FROM teams WHERE id IN (%s, %s)", (TEST_TEAM_HOME, TEST_TEAM_AWAY))
        conn.commit()
    finally:
        conn.close()


def _base_game(**overrides) -> dict:
    game = {
        "id": TEST_GAME,
        "phase_id": "00000000-0000-0000-0000-0000000000ff",
        "rodada_data": "2026-08-01",
        "time_casa_id": TEST_TEAM_HOME,
        "time_visitante_id": TEST_TEAM_AWAY,
        "placar_casa": 10,
        "placar_visitante": 5,
        "status": "processada",
        "is_finished_raw": True,
    }
    game.update(overrides)
    return game


def test_upsert_game_twice_with_same_data_does_not_touch_corrigido_em(base_teams_and_player):
    upsert_game(_base_game())
    upsert_game(_base_game())  # idêntico

    assert _count("games", TEST_GAME) == 1
    row = _fetch_one("SELECT corrigido_em FROM games WHERE id = %s", (TEST_GAME,))
    assert row[0] is None


def test_upsert_game_with_changed_score_updates_in_place_not_duplicate(base_teams_and_player):
    upsert_game(_base_game(placar_casa=10))
    upsert_game(_base_game(placar_casa=99))  # súmula corrigida

    assert _count("games", TEST_GAME) == 1
    row = _fetch_one(
        "SELECT placar_casa, criado_em, corrigido_em FROM games WHERE id = %s", (TEST_GAME,)
    )
    placar_casa, criado_em, corrigido_em = row
    assert placar_casa == 99
    assert criado_em is not None
    assert corrigido_em is not None


def test_cancelled_game_is_preserved_not_deleted(base_teams_and_player):
    upsert_game(_base_game(status="processada"))
    upsert_game(_base_game(status="cancelada"))

    assert _count("games", TEST_GAME) == 1
    row = _fetch_one("SELECT status FROM games WHERE id = %s", (TEST_GAME,))
    assert row[0] == "cancelada"


def _base_player_stat(**overrides) -> dict:
    stat = {
        "id": TEST_PLAYER_STAT,
        "game_id": TEST_GAME,
        "player_id": TEST_PLAYER,
        "time_id_na_partida": TEST_TEAM_HOME,
        "jogou": True,
        "minutos_jogados": 20.5,
        "pontos": 10,
        "rebotes_ofensivos": 1,
        "rebotes_defensivos": 2,
        "assistencias": 3,
        "roubos": 0,
        "tocos": 0,
        "faltas_pessoais": 1,
        "faltas_tecnicas": 0,
        "faltas_antidesportivas": 0,
        "faltas_desqualificantes": 0,
        "faltas_desqualificantes_briga": 0,
        "faltas_flagrantes": 0,
        "faltas_desqualificantes_jogo": 0,
        "arremessos_2pt_tentados": 5,
        "arremessos_2pt_convertidos": 3,
        "arremessos_3pt_tentados": 2,
        "arremessos_3pt_convertidos": 1,
        "lances_livres_tentados": 2,
        "lances_livres_convertidos": 1,
        "turnovers": 1,
        "eficiencia": 10.0,
        "plus_minus": 5,
    }
    stat.update(overrides)
    return stat


def test_upsert_player_game_stat_idempotent_and_corrects_in_place(base_teams_and_player):
    upsert_game(_base_game())

    upsert_player_game_stat(_base_player_stat(pontos=10))
    upsert_player_game_stat(_base_player_stat(pontos=10))  # idêntico
    assert _count("player_game_stats", TEST_PLAYER_STAT) == 1
    row = _fetch_one(
        "SELECT corrigido_em FROM player_game_stats WHERE id = %s", (TEST_PLAYER_STAT,)
    )
    assert row[0] is None

    upsert_player_game_stat(_base_player_stat(pontos=15))  # correção real
    assert _count("player_game_stats", TEST_PLAYER_STAT) == 1
    row = _fetch_one(
        "SELECT pontos, corrigido_em FROM player_game_stats WHERE id = %s", (TEST_PLAYER_STAT,)
    )
    pontos, corrigido_em = row
    assert pontos == 15


def test_upsert_team_and_player_store_tournament_id(base_teams_and_player):
    row = _fetch_one("SELECT tournament_id FROM teams WHERE id = %s", (TEST_TEAM_HOME,))
    assert str(row[0]) == TEST_TOURNAMENT

    row = _fetch_one("SELECT tournament_id FROM players WHERE id = %s", (TEST_PLAYER,))
    assert str(row[0]) == TEST_TOURNAMENT


def test_upsert_team_preserves_tournament_id_across_repeated_calls(base_teams_and_player):
    upsert_team({"id": TEST_TEAM_HOME, "nome": "TESTE Home Renomeado", "tri_code": "TSH", "cor": "#fff"}, TEST_TOURNAMENT)

    assert _count("teams", TEST_TEAM_HOME) == 1
    row = _fetch_one("SELECT nome, tournament_id FROM teams WHERE id = %s", (TEST_TEAM_HOME,))
    nome, tournament_id = row
    assert nome == "TESTE Home Renomeado"
    assert str(tournament_id) == TEST_TOURNAMENT

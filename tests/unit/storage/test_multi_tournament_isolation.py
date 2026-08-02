"""User Story 4 de specs/002-add-series-2025-2026: um time/jogador com o
MESMO NOME em dois torneios diferentes (ex.: o mesmo clube jogando Ouro 2025
e Ouro 2026) precisa ser tratado como dois registros completamente
independentes — nenhuma estatística soma ou se confunde entre os dois,
mesmo quando o nome é idêntico e só o `id`/`tournament_id` diferem.

Prova o caso mais adversarial possível para o isolamento por torneio: nomes
iguais são o cenário em que um bug de filtro ausente passaria despercebido
com mais facilidade (comparado a nomes diferentes, já coberto em
test_reads.py)."""

from __future__ import annotations

import pytest

from storage.reads import get_player_game_stats, get_players, get_team_game_stats, get_teams
from storage.supabase_client import get_connection
from storage.upserts import upsert_game, upsert_player, upsert_player_game_stat, upsert_team, upsert_team_game_stat

TOURNAMENT_2025 = "00000000-0000-0000-0000-0000000000f1"
TOURNAMENT_2026 = "00000000-0000-0000-0000-0000000000f2"

TEAM_2025 = "00000000-0000-0000-0000-0000000000f3"
TEAM_2026 = "00000000-0000-0000-0000-0000000000f4"
PLAYER_2025 = "00000000-0000-0000-0000-0000000000f5"
PLAYER_2026 = "00000000-0000-0000-0000-0000000000f6"
PHASE_2025 = "00000000-0000-0000-0000-0000000000f7"
PHASE_2026 = "00000000-0000-0000-0000-0000000000f8"
GAME_2025 = "00000000-0000-0000-0000-0000000000f9"
GAME_2026 = "00000000-0000-0000-0000-0000000000fa"
PLAYER_STAT_2025 = "00000000-0000-0000-0000-0000000000fb"
PLAYER_STAT_2026 = "00000000-0000-0000-0000-0000000000fc"
TEAM_STAT_2025 = "00000000-0000-0000-0000-0000000000fd"
TEAM_STAT_2026 = "00000000-0000-0000-0000-0000000000fe"

NOME_TIME = "TESTE Mesmo Nome FC"
NOME_JOGADOR = "Jogador Homônimo"


@pytest.fixture
def mesmo_time_em_dois_torneios():
    """O mesmo nome de time/jogador aparece nos dois torneios, com ids e
    tournament_id diferentes — exatamente o cenário descrito em spec.md,
    User Story 4, Acceptance Scenario 1."""
    upsert_team({"id": TEAM_2025, "nome": NOME_TIME, "tri_code": "TMN", "cor": None}, TOURNAMENT_2025)
    upsert_team({"id": TEAM_2026, "nome": NOME_TIME, "tri_code": "TMN", "cor": None}, TOURNAMENT_2026)
    upsert_player(
        {"id": PLAYER_2025, "nome": NOME_JOGADOR, "team_id": TEAM_2025, "numero_camisa": "10"}, TOURNAMENT_2025
    )
    upsert_player(
        {"id": PLAYER_2026, "nome": NOME_JOGADOR, "team_id": TEAM_2026, "numero_camisa": "10"}, TOURNAMENT_2026
    )

    game_2025 = {
        "id": GAME_2025, "phase_id": PHASE_2025, "rodada_data": "2025-06-01",
        "time_casa_id": TEAM_2025, "time_visitante_id": TEAM_2025,
        "placar_casa": 50, "placar_visitante": 40, "status": "processada", "is_finished_raw": True,
    }
    game_2026 = {**game_2025, "id": GAME_2026, "phase_id": PHASE_2026, "time_casa_id": TEAM_2026, "time_visitante_id": TEAM_2026}
    upsert_game(game_2025)
    upsert_game(game_2026)

    stat_common = {
        "jogou": True, "minutos_jogados": 20.0, "rebotes_ofensivos": 2, "rebotes_defensivos": 2,
        "assistencias": 3, "roubos": 1, "tocos": 0, "faltas_pessoais": 1, "faltas_tecnicas": 0,
        "faltas_antidesportivas": 0, "faltas_desqualificantes": 0, "faltas_desqualificantes_briga": 0,
        "faltas_flagrantes": 0, "faltas_desqualificantes_jogo": 0, "arremessos_3pt_tentados": 2,
        "arremessos_3pt_convertidos": 1, "lances_livres_tentados": 2, "lances_livres_convertidos": 2,
        "turnovers": 1, "eficiencia": 15.0, "plus_minus": 5,
    }
    # Estatísticas DIFERENTES entre os dois torneios (10 vs. 99 pontos) — se algum filtro
    # de fase/torneio vazar, uma consulta escopada a um torneio traria o valor do outro.
    upsert_player_game_stat({
        "id": PLAYER_STAT_2025, "game_id": GAME_2025, "player_id": PLAYER_2025, "time_id_na_partida": TEAM_2025,
        "pontos": 10, "arremessos_2pt_tentados": 4, "arremessos_2pt_convertidos": 3, **stat_common,
    })
    upsert_player_game_stat({
        "id": PLAYER_STAT_2026, "game_id": GAME_2026, "player_id": PLAYER_2026, "time_id_na_partida": TEAM_2026,
        "pontos": 99, "arremessos_2pt_tentados": 40, "arremessos_2pt_convertidos": 30, **stat_common,
    })

    team_stat_common = {
        "vitoria": True, "arremessos_2pt_tentados": 4, "arremessos_2pt_convertidos": 3,
        "arremessos_3pt_tentados": 2, "arremessos_3pt_convertidos": 1, "lances_livres_tentados": 2,
        "lances_livres_convertidos": 2, "rebotes_ofensivos": 2, "rebotes_defensivos": 2, "assistencias": 3,
        "roubos": 1, "tocos": 0, "turnovers": 1, "faltas": 1, "eficiencia": 15.0, "plus_minus": 5,
        "fiba_group_points": None,
    }
    upsert_team_game_stat({
        "id": TEAM_STAT_2025, "game_id": GAME_2025, "team_id": TEAM_2025,
        "saldo_pontos": 10, "pontos": 50, "pontos_sofridos": 40, **team_stat_common,
    })
    upsert_team_game_stat({
        "id": TEAM_STAT_2026, "game_id": GAME_2026, "team_id": TEAM_2026,
        "saldo_pontos": 999, "pontos": 999, "pontos_sofridos": 1, **team_stat_common,
    })

    yield

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM team_game_stats WHERE id IN (%s, %s)", (TEAM_STAT_2025, TEAM_STAT_2026))
            cur.execute("DELETE FROM player_game_stats WHERE id IN (%s, %s)", (PLAYER_STAT_2025, PLAYER_STAT_2026))
            cur.execute("DELETE FROM games WHERE id IN (%s, %s)", (GAME_2025, GAME_2026))
            cur.execute("DELETE FROM players WHERE id IN (%s, %s)", (PLAYER_2025, PLAYER_2026))
            cur.execute("DELETE FROM teams WHERE id IN (%s, %s)", (TEAM_2025, TEAM_2026))
        conn.commit()
    finally:
        conn.close()


def test_same_named_teams_are_not_mixed_between_tournaments(mesmo_time_em_dois_torneios):
    times_2025 = get_teams(TOURNAMENT_2025)
    times_2026 = get_teams(TOURNAMENT_2026)

    ids_2025 = {str(t["id"]) for t in times_2025 if t["nome"] == NOME_TIME}
    ids_2026 = {str(t["id"]) for t in times_2026 if t["nome"] == NOME_TIME}

    assert ids_2025 == {TEAM_2025}
    assert ids_2026 == {TEAM_2026}


def test_same_named_players_are_not_mixed_between_tournaments(mesmo_time_em_dois_torneios):
    jogadores_2025 = get_players(TOURNAMENT_2025)
    jogadores_2026 = get_players(TOURNAMENT_2026)

    ids_2025 = {str(p["id"]) for p in jogadores_2025 if p["nome"] == NOME_JOGADOR}
    ids_2026 = {str(p["id"]) for p in jogadores_2026 if p["nome"] == NOME_JOGADOR}

    assert ids_2025 == {PLAYER_2025}
    assert ids_2026 == {PLAYER_2026}


def test_player_stats_do_not_leak_across_tournaments_despite_same_name(mesmo_time_em_dois_torneios):
    stats_2025 = get_player_game_stats([PHASE_2025])
    stats_2026 = get_player_game_stats([PHASE_2026])

    pontos_2025 = {s["pontos"] for s in stats_2025 if str(s["player_id"]) == PLAYER_2025}
    pontos_2026 = {s["pontos"] for s in stats_2026 if str(s["player_id"]) == PLAYER_2026}

    assert pontos_2025 == {10}
    assert pontos_2026 == {99}
    # Nenhum valor do outro torneio aparece na consulta escopada a este.
    assert 99 not in {s["pontos"] for s in stats_2025}
    assert 10 not in {s["pontos"] for s in stats_2026}


def test_team_stats_do_not_leak_across_tournaments_despite_same_name(mesmo_time_em_dois_torneios):
    stats_2025 = get_team_game_stats([PHASE_2025])
    stats_2026 = get_team_game_stats([PHASE_2026])

    saldo_2025 = {s["saldo_pontos"] for s in stats_2025 if str(s["team_id"]) == TEAM_2025}
    saldo_2026 = {s["saldo_pontos"] for s in stats_2026 if str(s["team_id"]) == TEAM_2026}

    assert saldo_2025 == {10}
    assert saldo_2026 == {999}

"""Modo --modo recorrente: processa todos os torneios ativos numa execução
só, e uma falha total num torneio não impede o processamento do outro
(FR-008 de specs/002-add-series-2025-2026, User Story 2)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from collector.run import collect_recorrentes
from collector.tournaments import Fase, Torneio
from storage.reads import get_games
from storage.supabase_client import get_connection

TOURNAMENT_OK = "00000000-0000-0000-0000-0000000000d1"
PHASE_OK = "00000000-0000-0000-0000-0000000000d2"
TEAM_OK = "00000000-0000-0000-0000-0000000000d3"
GAME_OK = "00000000-0000-0000-0000-0000000000d4"

TOURNAMENT_QUEBRADO = "00000000-0000-0000-0000-0000000000d5"
PHASE_QUEBRADA = "00000000-0000-0000-0000-0000000000d6"


class FakeClient:
    """`/v1/tournaments/{TOURNAMENT_QUEBRADO}` levanta erro (simula o torneio
    inteiro fora do ar); o torneio OK responde normalmente."""

    def get(self, path: str, params: dict | None = None):
        if path == f"/v1/tournaments/{TOURNAMENT_QUEBRADO}":
            raise RuntimeError("Falha simulada: torneio fora do ar")
        if path == f"/v1/tournaments/{TOURNAMENT_OK}":
            return {
                "data": {
                    "has_aggregated_player_stats": True,
                    "teams": [{"id": TEAM_OK, "name": "TESTE Recorrente", "tri_code": "TRC", "primary_color": None}],
                    "players": [],
                }
            }
        if path == "/v1/games":
            phase_id = (params or {}).get("where[phase_id]")
            if phase_id == PHASE_OK:
                return {
                    "data": [
                        {
                            "id": GAME_OK, "phase_id": PHASE_OK, "datetime": "2026-08-01",
                            "home_team": {"id": TEAM_OK}, "away_team": {"id": TEAM_OK},
                            "home_score": 1, "away_score": 0, "is_finished": False,
                        }
                    ]
                }
            return {"data": []}
        raise AssertionError(f"Path não esperado: {path}")


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM games WHERE id = %s", (GAME_OK,))
            cur.execute("DELETE FROM teams WHERE id = %s", (TEAM_OK,))
        conn.commit()
    finally:
        conn.close()


def test_recorrente_mode_processes_all_active_tournaments_and_isolates_failure():
    torneio_ok = Torneio(
        tournament_id=TOURNAMENT_OK, slug="teste-ok", nome="Teste OK", modo="recorrente",
        fases=(Fase(phase_id=PHASE_OK, nome="Temporada Regular", gera_classificacao=False),),
    )
    torneio_quebrado = Torneio(
        tournament_id=TOURNAMENT_QUEBRADO, slug="teste-quebrado", nome="Teste Quebrado", modo="recorrente",
        fases=(Fase(phase_id=PHASE_QUEBRADA, nome="Temporada Regular", gera_classificacao=False),),
    )

    with patch("collector.run.torneios_por_modo", return_value=(torneio_quebrado, torneio_ok)):
        collect_recorrentes(FakeClient())  # não deve levantar, mesmo com o 1o torneio quebrado

    games = get_games([PHASE_OK])
    assert len(games) == 1
    assert str(games[0]["id"]) == GAME_OK

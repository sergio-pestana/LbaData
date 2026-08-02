"""Idempotência da carga histórica (FR-009 de specs/002-add-series-2025-2026):
reexecutar collect_round para o mesmo torneio/fase não duplica jogos. Usa um
FakeClient (sem rede real ao go-champs) contra o Supabase real (mesmo padrão
de tests/unit/storage/*), com ids de teste reservados e limpeza ao final.
"""

from __future__ import annotations

import pytest

from collector.run import collect_round
from storage.reads import get_games
from storage.supabase_client import get_connection

TOURNAMENT_ID = "00000000-0000-0000-0000-0000000000e1"
PHASE_ID = "00000000-0000-0000-0000-0000000000e2"
TEAM_HOME = "00000000-0000-0000-0000-0000000000e3"
TEAM_AWAY = "00000000-0000-0000-0000-0000000000e4"
GAME_ID = "00000000-0000-0000-0000-0000000000e5"


class FakeClient:
    def __init__(self, responses: dict[str, dict]):
        self._responses = responses

    def get(self, path: str, params: dict | None = None):
        return self._responses[path]


def _client() -> FakeClient:
    return FakeClient(
        {
            f"/v1/tournaments/{TOURNAMENT_ID}": {
                "data": {
                    "has_aggregated_player_stats": True,
                    "teams": [
                        {"id": TEAM_HOME, "name": "TESTE Backfill Home", "tri_code": "TBH", "primary_color": None},
                        {"id": TEAM_AWAY, "name": "TESTE Backfill Away", "tri_code": "TBA", "primary_color": None},
                    ],
                    "players": [],
                }
            },
            "/v1/games": {
                "data": [
                    {
                        "id": GAME_ID,
                        "phase_id": PHASE_ID,
                        "datetime": "2025-06-01",
                        "home_team": {"id": TEAM_HOME},
                        "away_team": {"id": TEAM_AWAY},
                        "home_score": 20,
                        "away_score": 15,
                        "is_finished": False,  # evita precisar de fixtures de súmula
                    }
                ]
            },
        }
    )


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM games WHERE id = %s", (GAME_ID,))
            cur.execute("DELETE FROM players WHERE tournament_id = %s", (TOURNAMENT_ID,))
            cur.execute("DELETE FROM teams WHERE id IN (%s, %s)", (TEAM_HOME, TEAM_AWAY))
        conn.commit()
    finally:
        conn.close()


def test_running_collect_round_twice_does_not_duplicate_game():
    collect_round(PHASE_ID, TOURNAMENT_ID, client=_client(), gera_classificacao=False)
    collect_round(PHASE_ID, TOURNAMENT_ID, client=_client(), gera_classificacao=False)

    games = get_games([PHASE_ID])
    assert len(games) == 1
    assert str(games[0]["id"]) == GAME_ID


PHASE_B_ID = "00000000-0000-0000-0000-0000000000e6"


class FailingPhaseClient:
    """Levanta erro só para a fase `phase_id_que_falha` — usado para provar
    que uma fase falhando dentro de collect_tournament não impede as demais
    (T016, FR-008)."""

    def __init__(self, tournament_payload: dict, phase_id_que_falha: str):
        self._tournament_payload = tournament_payload
        self._phase_id_que_falha = phase_id_que_falha

    def get(self, path: str, params: dict | None = None):
        if path == f"/v1/tournaments/{TOURNAMENT_ID}":
            return self._tournament_payload
        if path == "/v1/games":
            phase_id = (params or {}).get("where[phase_id]")
            if phase_id == self._phase_id_que_falha:
                raise RuntimeError(f"Falha simulada de rede para a fase {phase_id}")
            return {"data": []}
        raise AssertionError(f"Path não esperado: {path}")


def test_one_failing_phase_does_not_block_the_others_in_the_same_tournament():
    from collector.run import collect_tournament
    from collector.tournaments import Fase, Torneio

    torneio = Torneio(
        tournament_id=TOURNAMENT_ID,
        slug="teste-duas-fases",
        nome="Teste Duas Fases",
        modo="historico",
        fases=(
            Fase(phase_id=PHASE_ID, nome="Classificação", gera_classificacao=True),
            Fase(phase_id=PHASE_B_ID, nome="Playoffs", gera_classificacao=False),
        ),
    )
    tournament_payload = {"data": {"has_aggregated_player_stats": True, "teams": [], "players": []}}
    client = FailingPhaseClient(tournament_payload, phase_id_que_falha=PHASE_ID)

    # A asserção principal é não levantar: a falha simulada na 1a fase (Classificação)
    # é capturada e logada dentro de collect_tournament, e a 2a fase (Playoffs) ainda
    # é processada na mesma chamada — nenhuma exceção escapa para o chamador.
    collect_tournament(torneio, client)

    assert get_games([PHASE_ID]) == []  # fase que falhou: nada foi gravado
    assert get_games([PHASE_B_ID]) == []  # fase sem falha: processada normalmente (sem jogos na fixture)

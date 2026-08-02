"""Fase tipo chaveamento/bracket (ex.: Playoffs) não tem `eliminations`
preenchido na fonte — confirmado contra payload real em
`tests/fixtures/phase_playoffs_bracket.json` (research.md #4 de
specs/002-add-series-2025-2026). `collect_round(..., gera_classificacao=False)`
deve pular a etapa de classificação por completo — nunca chamar
`GET /v1/phases/{phase_id}` nem tentar parsear a resposta — em vez de buscar e
descartar um `UnexpectedPayloadShape` esperado.
"""

from __future__ import annotations

from collector.run import collect_round


class FakeClient:
    """Duplo de teste: só responde pelos paths explicitamente registrados.
    Qualquer path não registrado levanta AssertionError — usado para provar
    que `/v1/phases/{phase_id}` nunca é chamado quando gera_classificacao=False."""

    def __init__(self, responses: dict[str, dict]):
        self._responses = responses
        self.called_paths: list[str] = []

    def get(self, path: str, params: dict | None = None):
        self.called_paths.append(path)
        if path not in self._responses:
            raise AssertionError(f"Path não esperado chamado pelo coletor: {path}")
        return self._responses[path]


TOURNAMENT_ID = "00000000-0000-0000-0000-0000000000f1"
PHASE_ID = "00000000-0000-0000-0000-0000000000f2"


def _empty_client() -> FakeClient:
    return FakeClient(
        {
            f"/v1/tournaments/{TOURNAMENT_ID}": {
                "data": {"has_aggregated_player_stats": True, "teams": [], "players": []}
            },
            "/v1/games": {"data": []},
        }
    )


def test_playoffs_phase_never_calls_standings_endpoint():
    client = _empty_client()

    collect_round(PHASE_ID, TOURNAMENT_ID, client=client, gera_classificacao=False)

    assert f"/v1/phases/{PHASE_ID}" not in client.called_paths


def test_classificacao_phase_does_call_standings_endpoint():
    """Contraste: quando gera_classificacao=True (comportamento padrão), a
    fase de standings É chamada — se a fonte não a tiver, o erro já esperado
    (UnexpectedPayloadShape) é capturado e logado, não propagado."""
    client = _empty_client()
    client._responses[f"/v1/phases/{PHASE_ID}"] = {
        "data": {"eliminations": [], "elimination_stats": [], "draws": []}
    }

    collect_round(PHASE_ID, TOURNAMENT_ID, client=client, gera_classificacao=True)

    assert f"/v1/phases/{PHASE_ID}" in client.called_paths

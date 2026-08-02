"""resolver_torneio (lógica pura por trás do seletor de torneio do dashboard,
User Story 3 de specs/002-add-series-2025-2026)."""

from __future__ import annotations

from collector.tournaments import TORNEIOS
from dashboard.theme import resolver_slug_inicial, resolver_torneio


def test_resolver_torneio_returns_correct_ids_for_every_registered_tournament():
    for torneio in TORNEIOS:
        resultado = resolver_torneio(torneio.nome)

        assert resultado["tournament_id"] == torneio.tournament_id
        assert resultado["phase_ids"] == [f.phase_id for f in torneio.fases]


def test_resolver_torneio_finds_classificacao_phase_for_2025_series():
    for nome in ("Ouro 2025", "Prata 2025", "Bronze 2025"):
        resultado = resolver_torneio(nome)
        torneio = next(t for t in TORNEIOS if t.nome == nome)
        fase_classificacao = next(f for f in torneio.fases if f.gera_classificacao)

        assert resultado["phase_id_classificacao"] == fase_classificacao.phase_id


def test_resolver_torneio_single_phase_tournaments_use_that_phase_as_classificacao():
    for nome in ("Ouro 2026", "Prata/Bronze 2026"):
        resultado = resolver_torneio(nome)
        torneio = next(t for t in TORNEIOS if t.nome == nome)

        assert resultado["phase_id_classificacao"] == torneio.fases[0].phase_id


def test_resolver_slug_inicial_uses_url_slug_when_valid():
    assert resolver_slug_inicial("bronze2025") == "bronze2025"


def test_resolver_slug_inicial_falls_back_to_first_tournament_when_missing_or_invalid():
    assert resolver_slug_inicial(None) == TORNEIOS[0].slug
    assert resolver_slug_inicial("slug-que-nao-existe") == TORNEIOS[0].slug

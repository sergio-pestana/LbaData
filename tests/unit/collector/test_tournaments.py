"""Sanidade do registro estático de torneios (research.md #6, contracts/tournament-registry.md)."""

from __future__ import annotations

from collector.tournaments import TORNEIOS, fase_de_classificacao, get_torneio_by_slug, torneios_por_modo


def test_tournament_ids_are_unique():
    ids = [t.tournament_id for t in TORNEIOS]
    assert len(ids) == len(set(ids))


def test_slugs_are_unique():
    slugs = [t.slug for t in TORNEIOS]
    assert len(slugs) == len(set(slugs))


def test_every_tournament_has_at_least_one_phase():
    for torneio in TORNEIOS:
        assert len(torneio.fases) >= 1, f"{torneio.slug} sem nenhuma fase"


def test_phase_ids_are_unique_across_all_tournaments():
    phase_ids = [fase.phase_id for t in TORNEIOS for fase in t.fases]
    assert len(phase_ids) == len(set(phase_ids))


def test_modo_is_always_recorrente_or_historico():
    for torneio in TORNEIOS:
        assert torneio.modo in ("recorrente", "historico"), f"{torneio.slug} tem modo inválido: {torneio.modo}"


def test_get_torneio_by_slug_returns_expected_tournament():
    torneio = get_torneio_by_slug("ouro2025")
    assert torneio.tournament_id == "9fa9ecef-c361-4d82-9fd5-ae8f3919b011"


def test_get_torneio_by_slug_raises_for_unknown_slug():
    try:
        get_torneio_by_slug("inexistente")
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass


def test_torneios_por_modo_recorrente_returns_only_active_tournaments():
    recorrentes = torneios_por_modo("recorrente")
    assert {t.slug for t in recorrentes} == {"ouro2026", "bronze2026"}


def test_torneios_por_modo_historico_returns_only_2025_series():
    historicos = torneios_por_modo("historico")
    assert {t.slug for t in historicos} == {"ouro2025", "prata2025", "bronze2025"}


def test_fase_de_classificacao_returns_none_when_no_phase_generates_standings():
    from collector.tournaments import Fase, Torneio

    torneio_sem_classificacao = Torneio(
        tournament_id="x", slug="x", nome="x", modo="historico",
        fases=(Fase(phase_id="y", nome="Playoffs", gera_classificacao=False),),
    )
    assert fase_de_classificacao(torneio_sem_classificacao) is None


def test_fase_de_classificacao_finds_the_right_phase_for_2025_tournaments():
    for slug in ("ouro2025", "prata2025", "bronze2025"):
        torneio = get_torneio_by_slug(slug)
        fase = fase_de_classificacao(torneio)
        assert fase is not None
        assert fase.nome == "Classificação"

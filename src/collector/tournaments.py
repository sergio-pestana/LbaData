"""Registro estático dos torneios suportados — fonte de verdade em
`specs/002-add-series-2025-2026/contracts/tournament-registry.md`.

Módulo Python simples (não YAML/JSON externo) por serem só 5 registros fixos,
versionados junto com o código — introduzir um parser de configuração novo
para isso não se justifica (Princípio VI, research.md #6).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fase:
    phase_id: str
    nome: str
    gera_classificacao: bool


@dataclass(frozen=True)
class Torneio:
    tournament_id: str
    slug: str
    nome: str
    modo: str  # "recorrente" | "historico"
    fases: tuple[Fase, ...]


TORNEIOS: tuple[Torneio, ...] = (
    Torneio(
        tournament_id="5bf23f0b-6768-46ec-bcc1-4cd698105413",
        slug="ouro2026",
        nome="Ouro 2026",
        modo="recorrente",
        fases=(
            Fase(phase_id="ede46bb2-21ac-411b-b07f-b93269bebd37", nome="Temporada Regular", gera_classificacao=True),
        ),
    ),
    Torneio(
        tournament_id="4cc1dacb-2619-48b8-8331-caa7103eefab",
        slug="bronze2026",
        nome="Prata/Bronze 2026",
        modo="recorrente",
        fases=(
            Fase(phase_id="3cf0e777-d532-46e5-9b00-eefb59e9075a", nome="Temporada Regular", gera_classificacao=True),
        ),
    ),
    Torneio(
        tournament_id="9fa9ecef-c361-4d82-9fd5-ae8f3919b011",
        slug="ouro2025",
        nome="Ouro 2025",
        modo="historico",
        fases=(
            Fase(phase_id="7fc86b0f-36d6-4f8d-bb40-9e00a688b47e", nome="Classificação", gera_classificacao=True),
            Fase(phase_id="51de7c2b-0be8-4a50-bdee-0ed3f5bacd94", nome="Playoffs", gera_classificacao=False),
        ),
    ),
    Torneio(
        tournament_id="e72d3f2f-d55e-48b1-b4df-6d0305588b96",
        slug="prata2025",
        nome="Prata 2025",
        modo="historico",
        fases=(
            Fase(phase_id="c2740a29-a81a-4eea-b962-c5d14921a36f", nome="Classificação", gera_classificacao=True),
            Fase(phase_id="c5b71c3b-23be-4ef3-9a26-573ed634f16c", nome="Playoffs", gera_classificacao=False),
        ),
    ),
    Torneio(
        tournament_id="354be508-1cc8-4deb-a42c-57abd2377fcd",
        slug="bronze2025",
        nome="Bronze 2025",
        modo="historico",
        fases=(
            Fase(phase_id="c70b7fdd-96cd-4a8a-adcc-f94c439213f8", nome="Classificação", gera_classificacao=True),
            Fase(phase_id="08dd0f20-d69e-49cf-b77e-9c17fc985563", nome="Playoffs", gera_classificacao=False),
        ),
    ),
)


def get_torneio_by_slug(slug: str) -> Torneio:
    for torneio in TORNEIOS:
        if torneio.slug == slug:
            return torneio
    raise ValueError(f"Torneio com slug '{slug}' não encontrado no registro. Slugs válidos: "
                      f"{', '.join(t.slug for t in TORNEIOS)}")


def torneios_por_modo(modo: str) -> tuple[Torneio, ...]:
    return tuple(t for t in TORNEIOS if t.modo == modo)


def fase_de_classificacao(torneio: Torneio) -> Fase | None:
    """A única fase (se houver) que produz tabela de classificação — usada
    pelo dashboard para saber de qual fase ler standings_snapshot."""
    for fase in torneio.fases:
        if fase.gera_classificacao:
            return fase
    return None

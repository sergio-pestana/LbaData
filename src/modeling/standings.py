"""Panorama da temporada e classificação (FR-007, FR-008).

Funções puras: recebem linhas já lidas de `storage.reads` e não sabem nada
sobre SQL/Supabase (Princípio III).
"""

from __future__ import annotations


def season_overview(games: list[dict]) -> dict:
    """Quantos jogos já ocorreram e quantos ainda restam (FR-007).

    Jogos `cancelada` são excluídos das duas contagens (FR-018) — não
    aconteceram nem estão por acontecer, são um caso à parte.
    """
    ativos = [g for g in games if g.get("status") != "cancelada"]
    realizados = [g for g in ativos if g.get("is_finished_raw")]
    restantes = [g for g in ativos if not g.get("is_finished_raw")]
    return {
        "jogos_realizados": len(realizados),
        "jogos_restantes": len(restantes),
    }


def current_standings(snapshot_rows: list[dict]) -> list[dict]:
    """Classificação atual: a última linha de `standings_snapshot` por time,
    ordenada pela posição já computada pela fonte (FR-008)."""
    return sorted(snapshot_rows, key=lambda r: r["posicao"])

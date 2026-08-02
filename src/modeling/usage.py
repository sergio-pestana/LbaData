"""Concentração de utilização/posse ofensiva por jogador (FR-011).

Fórmula decidida no /speckit-clarify e confirmada em data-model.md: (arremessos
de 2 + arremessos de 3 tentados + lances livres tentados + turnovers) /
minutos jogados — sem estimar posses do time inteiro (Princípio VI).
"""

from __future__ import annotations

from collections import defaultdict

from modeling.sample_size import LIMIAR_PADRAO, flag_low_confidence


def usage_index(player_game_stats: list[dict], limiar: int = LIMIAR_PADRAO) -> list[dict]:
    """`player_game_stats` já filtrado por time pela camada de armazenamento.

    Cada item: {"player_id", "valor", "num_jogos", "baixa_confianca"}, ordenado
    do maior para o menor índice de utilização.
    """
    por_jogador: dict[str, dict] = defaultdict(lambda: {"envolvimento": 0.0, "minutos": 0.0, "jogos": 0})

    for row in player_game_stats:
        if not row.get("jogou"):
            continue
        entry = por_jogador[row["player_id"]]
        entry["envolvimento"] += (
            row["arremessos_2pt_tentados"]
            + row["arremessos_3pt_tentados"]
            + row["lances_livres_tentados"]
            + row["turnovers"]
        )
        entry["minutos"] += row["minutos_jogados"] or 0
        entry["jogos"] += 1

    ranking = []
    for player_id, dados in por_jogador.items():
        valor = (dados["envolvimento"] / dados["minutos"]) if dados["minutos"] else 0.0
        ranking.append({"player_id": player_id, **flag_low_confidence(valor, dados["jogos"], limiar)})

    ranking.sort(key=lambda r: r["valor"], reverse=True)
    return ranking

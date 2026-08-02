"""Concentração de contribuição defensiva por jogador.

Espelha `modeling/usage.py` (mesmo Princípio VI — índice simples, sem
estimar métricas que a fonte não expõe diretamente, como posses
defensivas): (rebotes defensivos + roubos de bola + tocos) / minutos
jogados. As três categorias já são coletadas em `player_game_stats` e são,
juntas, o proxy mais direto de "envolvimento defensivo" disponível na
súmula (não há posse defensiva nem defensive rating por jogador na fonte).
"""

from __future__ import annotations

from collections import defaultdict

from modeling.sample_size import LIMIAR_PADRAO, flag_low_confidence


def defense_index(player_game_stats: list[dict], limiar: int = LIMIAR_PADRAO) -> list[dict]:
    """`player_game_stats` já filtrado por time pela camada de armazenamento.

    Cada item: {"player_id", "valor", "num_jogos", "baixa_confianca"}, ordenado
    do maior para o menor índice de defesa.
    """
    por_jogador: dict[str, dict] = defaultdict(lambda: {"acoes_defensivas": 0.0, "minutos": 0.0, "jogos": 0})

    for row in player_game_stats:
        if not row.get("jogou"):
            continue
        entry = por_jogador[row["player_id"]]
        entry["acoes_defensivas"] += (
            row["rebotes_defensivos"] + row["roubos"] + row["tocos"]
        )
        entry["minutos"] += row["minutos_jogados"] or 0
        entry["jogos"] += 1

    ranking = []
    for player_id, dados in por_jogador.items():
        valor = (dados["acoes_defensivas"] / dados["minutos"]) if dados["minutos"] else 0.0
        ranking.append({"player_id": player_id, **flag_low_confidence(valor, dados["jogos"], limiar)})

    ranking.sort(key=lambda r: r["valor"], reverse=True)
    return ranking

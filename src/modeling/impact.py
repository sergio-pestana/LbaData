"""Impacto no resultado das partidas (FR-012).

Decisão do /speckit-clarify + research.md #5: combinar Eficiência e Plus/Minus
(médias por jogo de cada jogador) via z-score dentro do grupo analisado, soma
com peso igual — evita que a escala maior da Eficiência domine o índice.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from modeling.sample_size import LIMIAR_PADRAO, flag_low_confidence


def _z_scores(valores: dict[str, float]) -> dict[str, float]:
    numeros = list(valores.values())
    if len(numeros) < 2:
        return {chave: 0.0 for chave in valores}
    media = statistics.mean(numeros)
    desvio = statistics.stdev(numeros)
    if desvio == 0:
        return {chave: 0.0 for chave in valores}
    return {chave: (valor - media) / desvio for chave, valor in valores.items()}


def impact_index(player_game_stats: list[dict], limiar: int = LIMIAR_PADRAO) -> list[dict]:
    """`player_game_stats` do grupo a comparar (ex.: liga inteira num período).

    Cada item: {"player_id", "valor", "num_jogos", "baixa_confianca"}, ordenado
    do maior para o menor impacto.
    """
    por_jogador: dict[str, dict] = defaultdict(lambda: {"eficiencia": 0.0, "plus_minus": 0.0, "jogos": 0})

    for row in player_game_stats:
        if not row.get("jogou"):
            continue
        entry = por_jogador[row["player_id"]]
        entry["eficiencia"] += row["eficiencia"]
        entry["plus_minus"] += row["plus_minus"]
        entry["jogos"] += 1

    jogadores_com_jogo = {pid: d for pid, d in por_jogador.items() if d["jogos"] > 0}
    media_eficiencia = {pid: d["eficiencia"] / d["jogos"] for pid, d in jogadores_com_jogo.items()}
    media_plus_minus = {pid: d["plus_minus"] / d["jogos"] for pid, d in jogadores_com_jogo.items()}

    z_eficiencia = _z_scores(media_eficiencia)
    z_plus_minus = _z_scores(media_plus_minus)

    ranking = []
    for player_id, dados in jogadores_com_jogo.items():
        valor = z_eficiencia[player_id] + z_plus_minus[player_id]
        ranking.append({"player_id": player_id, **flag_low_confidence(valor, dados["jogos"], limiar)})

    ranking.sort(key=lambda r: r["valor"], reverse=True)
    return ranking

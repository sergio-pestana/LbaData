"""Evolução de times e jogadores ao longo da temporada — rodada a rodada, não
apenas o acumulado (FR-010). Cada ponto da série carrega a contagem de jogos
que o sustenta e a marca de baixa confiança (Princípio VII, FR-013).
"""

from __future__ import annotations

from modeling.sample_size import LIMIAR_PADRAO, flag_low_confidence


def player_trend(series: list[dict], metrica: str, limiar: int = LIMIAR_PADRAO) -> list[dict]:
    """`series`: linhas de `player_game_stats` de UM jogador, já ordenadas por
    `rodada_data` (ver `storage.reads.get_player_game_stats_series`).

    Cada ponto: {"rodada_data", "valor", "num_jogos", "baixa_confianca"} — o
    valor é o desempenho daquela rodada específica; `num_jogos` é quantas
    partidas o jogador já disputou até e incluindo essa rodada (a tendência é
    ponto a ponto, mas a confiança cresce com o histórico acumulado).
    """
    jogados = [row for row in series if row.get("jogou")]
    pontos = []
    for indice, row in enumerate(jogados, start=1):
        ponto = {"rodada_data": row["rodada_data"]}
        ponto.update(flag_low_confidence(row[metrica], indice, limiar))
        pontos.append(ponto)
    return pontos


def team_trend(series: list[dict], metrica: str, limiar: int = LIMIAR_PADRAO) -> list[dict]:
    """`series`: linhas de `team_game_stats` de UM time, já ordenadas por
    `rodada_data` (junção feita pelo chamador via `storage.reads`)."""
    pontos = []
    for indice, row in enumerate(series, start=1):
        ponto = {"rodada_data": row["rodada_data"]}
        ponto.update(flag_low_confidence(row[metrica], indice, limiar))
        pontos.append(ponto)
    return pontos


def standings_trend(snapshot_rows: list[dict]) -> list[dict]:
    """Evolução da classificação de um time — leitura direta do histórico de
    `standings_snapshot` (já filtrado por time e ordenado por `coletado_em`
    via `storage.reads.get_standings_history`)."""
    return [
        {
            "coletado_em": row["coletado_em"],
            "posicao": row["posicao"],
            "jogos": row["jogos"],
            "vitorias": row["vitorias"],
            "derrotas": row["derrotas"],
            "saldo_pontos": row["saldo_pontos"],
            "pontos_fiba": row["pontos_fiba"],
        }
        for row in snapshot_rows
    ]

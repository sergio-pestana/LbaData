"""Melhores jogadores e times por critério (FR-009).

`player_game_stats`/`team_game_stats` já vêm filtrados por time (ou não) pela
camada de armazenamento; estas funções não sabem nada sobre SQL/filtros
(Princípio III).
"""

from __future__ import annotations

from collections import defaultdict

from modeling.sample_size import LIMIAR_PADRAO, flag_low_confidence

# Métricas brutas exibidas na tabela completa de jogadores e nos seletores de
# ranking — nome de coluna em player_game_stats -> rótulo amigável.
PLAYER_METRIC_LABELS: dict[str, str] = {
    "pontos": "Pontos",
    "eficiencia": "Eficiência",
    "assistencias": "Assistências",
    "rebotes_ofensivos": "Rebotes ofensivos",
    "rebotes_defensivos": "Rebotes defensivos",
    "roubos": "Roubos de bola",
    "tocos": "Tocos",
    "turnovers": "Turnovers",
    "faltas_pessoais": "Faltas",
    "arremessos_2pt_tentados": "2PT tentados",
    "arremessos_2pt_convertidos": "2PT convertidos",
    "arremessos_3pt_tentados": "3PT tentados",
    "arremessos_3pt_convertidos": "3PT convertidos",
    "lances_livres_tentados": "LL tentados",
    "lances_livres_convertidos": "LL convertidos",
    "plus_minus": "Plus/Minus",
    "minutos_jogados": "Minutos jogados",
}

# Métricas de time equivalentes, em team_game_stats.
TEAM_METRIC_LABELS: dict[str, str] = {
    "pontos": "Pontos",
    "eficiencia": "Eficiência",
    "assistencias": "Assistências",
    "rebotes_ofensivos": "Rebotes ofensivos",
    "rebotes_defensivos": "Rebotes defensivos",
    "roubos": "Roubos de bola",
    "tocos": "Tocos",
    "turnovers": "Turnovers",
    "saldo_pontos": "Saldo de pontos",
    "plus_minus": "Plus/Minus",
}


def rank_players(
    player_game_stats: list[dict], criterio: str, limiar: int = LIMIAR_PADRAO
) -> list[dict]:
    """Ranking de jogadores por `criterio`, somado pelos jogos em que o
    jogador efetivamente jogou.

    Cada item: {"player_id", "valor", "num_jogos", "baixa_confianca"}.
    """
    por_jogador: dict[str, dict] = defaultdict(lambda: {"soma": 0, "jogos": 0})

    for row in player_game_stats:
        if not row.get("jogou"):
            continue
        entry = por_jogador[row["player_id"]]
        entry["soma"] += row[criterio]
        entry["jogos"] += 1

    ranking = [
        {"player_id": player_id, **flag_low_confidence(dados["soma"], dados["jogos"], limiar)}
        for player_id, dados in por_jogador.items()
    ]
    ranking.sort(key=lambda r: r["valor"], reverse=True)
    return ranking


def team_metric_ranking(
    team_game_stats: list[dict], criterio: str, limiar: int = LIMIAR_PADRAO
) -> dict[str, dict]:
    """Total e média por time para `criterio` (nome de coluna de
    `team_game_stats`).

    Retorna {team_id: {"total", "media", "num_jogos", "baixa_confianca_total",
    "baixa_confianca_media"}} — total e média usam o mesmo limiar de jogos.
    """
    por_time: dict[str, dict] = defaultdict(lambda: {"soma": 0.0, "jogos": 0})
    for row in team_game_stats:
        entry = por_time[row["team_id"]]
        entry["soma"] += row[criterio]
        entry["jogos"] += 1

    resultado = {}
    for team_id, dados in por_time.items():
        jogos = dados["jogos"]
        total = dados["soma"]
        media = (total / jogos) if jogos else 0.0
        resultado[team_id] = {
            "total": total,
            "media": media,
            "num_jogos": jogos,
            "baixa_confianca": jogos < limiar,
        }
    return resultado


def player_stats_table(player_game_stats: list[dict]) -> list[dict]:
    """Uma linha por jogador com total E média de cada métrica bruta, mais
    percentuais/razões avançadas calculados a partir dos totais da temporada
    (nunca como média das porcentagens/razões por jogo — isso distorceria
    jogadores com poucas tentativas, ver research.md #10 sobre o mesmo
    cuidado com FG%).

    O chamador decide, coluna a coluna, se mostra `<metrica>_total` ou
    `<metrica>_media`; percentuais/razões (`fg2_pct`, `fg3_pct`, `ft_pct`,
    `ts_pct`, `ast_to_ratio`) não têm variante total/média — `ast_to_ratio` é
    `None` quando o jogador não tem nenhum turnover na amostra (divisão por
    zero não vira um número inventado).
    """
    somas: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    jogos_por_jogador: dict[str, int] = defaultdict(int)

    metricas = [m for m in PLAYER_METRIC_LABELS if m != "jogos"]

    for row in player_game_stats:
        if not row.get("jogou"):
            continue
        pid = row["player_id"]
        jogos_por_jogador[pid] += 1
        for campo in metricas:
            somas[pid][campo] += row.get(campo) or 0

    linhas = []
    for pid, jogos in jogos_por_jogador.items():
        linha: dict = {"player_id": pid, "jogos": jogos}
        for campo in metricas:
            total = somas[pid][campo]
            linha[f"{campo}_total"] = total
            linha[f"{campo}_media"] = (total / jogos) if jogos else 0.0

        fg2_tentados = somas[pid]["arremessos_2pt_tentados"]
        fg3_tentados = somas[pid]["arremessos_3pt_tentados"]
        ft_tentados = somas[pid]["lances_livres_tentados"]
        linha["fg2_pct"] = (somas[pid]["arremessos_2pt_convertidos"] / fg2_tentados * 100) if fg2_tentados else 0.0
        linha["fg3_pct"] = (somas[pid]["arremessos_3pt_convertidos"] / fg3_tentados * 100) if fg3_tentados else 0.0
        linha["ft_pct"] = (somas[pid]["lances_livres_convertidos"] / ft_tentados * 100) if ft_tentados else 0.0

        # True Shooting % — eficiência de arremesso considerando o valor extra
        # do arremesso de 3 e o custo baixo do lance livre (padrão NBA).
        tentativas_efetivas = 2 * (fg2_tentados + fg3_tentados + 0.44 * ft_tentados)
        linha["ts_pct"] = (somas[pid]["pontos"] / tentativas_efetivas * 100) if tentativas_efetivas else 0.0

        # Volume de arremessos por jogo (2PT + 3PT + LL tentados) — usado para
        # separar "muito volume" de "pouco volume" ao lado do TS%.
        linha["tentativas_media"] = ((fg2_tentados + fg3_tentados + ft_tentados) / jogos) if jogos else 0.0

        # Assistências por turnover — quanto maior, melhor o time de bola sem
        # gerar perdas; None (não 0 ou infinito) quando não há turnover na
        # amostra, para não fabricar um número.
        turnovers_total = somas[pid]["turnovers"]
        linha["ast_to_ratio"] = (somas[pid]["assistencias"] / turnovers_total) if turnovers_total else None

        linhas.append(linha)
    return linhas

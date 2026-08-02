"""Relações entre métricas que uma tabela não mostra bem — estilo dos
gráficos de análise avançada de basquete (usage vs. efficiency, shot profile,
off/def rating). Substituiu o "top 5 por métrica" (que duplicava a tabela
ordenável de Estatísticas de Jogadores — decisão do usuário ao revisar o
dashboard). Os índices de Utilização (FR-011) e Impacto/z-score (FR-012)
continuam implementados e testados em `modeling/usage.py` e
`modeling/impact.py`, só não ficam mais em destaque nesta tela.

Cor de cada ponto = cor real do time (mesma da tabela de classificação), não
mais uma cor genérica de confiança — e nenhum jogador é filtrado ou destacado
por quantidade de jogos: quem jogou aparece, com o número de jogos sempre
visível no hover (decisão do usuário ao revisar o dashboard).
"""

import streamlit as st

from dashboard.theme import apply_theme, player_lookup, scatter_with_medians, section_label, team_lookup
from modeling.leaderboards import player_stats_table, team_metric_ranking
from modeling.usage import usage_index
from storage.reads import get_player_game_stats, get_players, get_team_game_stats, get_teams

apply_theme("Impacto e utilização")

teams = get_teams()
teams_by_id = team_lookup(teams)
players_by_id = player_lookup(get_players())

nomes_times = [t["nome"] for t in teams]
times_escolhidos = st.multiselect("Times (para os gráficos por jogador)", nomes_times, default=nomes_times)
ids_escolhidos = {str(t["id"]) for t in teams if t["nome"] in times_escolhidos}

stats = [row for row in get_player_game_stats() if str(row["time_id_na_partida"]) in ids_escolhidos]
usage_ranking = {row["player_id"]: row for row in usage_index(stats)}
tabela = {row["player_id"]: row for row in player_stats_table(stats)}


def _base_pontos() -> list[dict]:
    """Um dict por jogador com nome/time/cor já resolvidos — todo jogador com
    ao menos uma partida jogada entra, sem piso de minutos nem distinção
    visual por quantidade de jogos (decisão do usuário)."""
    resultado = []
    for player_id, linha in tabela.items():
        player = players_by_id.get(str(player_id))
        time = teams_by_id.get(str(player["team_id"])) if player else None
        resultado.append(
            {
                "player_id": player_id,
                "nome": player["nome"] if player else "?",
                "grupo": time["nome"] if time else "?",
                "cor": (time.get("cor") if time else None) or "#888888",
                "jogos": linha["jogos"],
                "linha": linha,
            }
        )
    return resultado


# ---------------------------------------------------------------------------
# 1. Eficiência × Utilização
# ---------------------------------------------------------------------------
section_label("Eficiência × Utilização")
st.caption(
    "Eixo X: índice de utilização — (arremessos + lances livres tentados + turnovers) / "
    "minutos jogados. Eixo Y: Eficiência média por jogo. Cor = time."
)

pontos = []
for base in _base_pontos():
    usage_row = usage_ranking.get(base["player_id"])
    if usage_row is None:
        continue
    pontos.append(
        {
            **base,
            "utilizacao": usage_row["valor"],
            "eficiencia": base["linha"]["eficiencia_media"],
            "hover": (
                f"{base['nome']} ({base['grupo']})<br>Utilização: {usage_row['valor']:.2f}/min"
                f"<br>Eficiência média: {base['linha']['eficiencia_media']:.1f}<br>{base['jogos']} jogo(s)"
            ),
        }
    )

fig = scatter_with_medians(pontos, "utilizacao", "eficiencia", "Índice de utilização (por minuto)", "Eficiência média por jogo")
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Quadrante superior direito: concentra bastante a bola E converte isso em produção eficiente.")

# ---------------------------------------------------------------------------
# 2. Eficiência × Plus/Minus
# ---------------------------------------------------------------------------
section_label("Eficiência × Plus/Minus")
st.caption(
    "Eixo X: Plus/Minus médio (saldo de pontos do time com o jogador em quadra). "
    "Eixo Y: Eficiência média por jogo. Cor = time."
)

pontos = [
    {
        **base,
        "plus_minus": base["linha"]["plus_minus_media"],
        "eficiencia": base["linha"]["eficiencia_media"],
        "hover": (
            f"{base['nome']} ({base['grupo']})<br>Plus/Minus médio: {base['linha']['plus_minus_media']:.1f}"
            f"<br>Eficiência média: {base['linha']['eficiencia_media']:.1f}<br>{base['jogos']} jogo(s)"
        ),
    }
    for base in _base_pontos()
]

fig = scatter_with_medians(pontos, "plus_minus", "eficiencia", "Plus/Minus médio", "Eficiência média por jogo")
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Quadrante superior direito: produz muito E o time vai bem com ele em quadra — "
        "os dois lados do que costuma se chamar de \"impacto\"."
    )

# ---------------------------------------------------------------------------
# 3. TS% × Volume de arremessos
# ---------------------------------------------------------------------------
section_label("Eficiência de arremesso (TS%) × Volume")
st.caption(
    "Eixo X: tentativas de arremesso por jogo (2PT + 3PT + lances livres). "
    "Eixo Y: True Shooting % (pesa o valor extra do arremesso de 3 e o custo baixo do "
    "lance livre). Cor = time."
)

pontos = [
    {
        **base,
        "tentativas": base["linha"]["tentativas_media"],
        "ts_pct": base["linha"]["ts_pct"],
        "hover": (
            f"{base['nome']} ({base['grupo']})<br>Tentativas/jogo: {base['linha']['tentativas_media']:.1f}"
            f"<br>TS%: {base['linha']['ts_pct']:.1f}<br>{base['jogos']} jogo(s)"
        ),
    }
    for base in _base_pontos()
]

fig = scatter_with_medians(pontos, "tentativas", "ts_pct", "Tentativas de arremesso por jogo", "TS%")
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Quadrante superior esquerdo: poucas tentativas, mas muito eficientes. "
        "Quadrante superior direito: muito volume SEM perder eficiência — os melhores arremessadores da liga."
    )

# ---------------------------------------------------------------------------
# 4. Ataque × Defesa por time
# ---------------------------------------------------------------------------
section_label("Ataque × Defesa por time")
st.caption(
    "Eixo X: pontos marcados por jogo. Eixo Y: pontos sofridos por jogo (invertido — "
    "para cima é MENOS pontos sofridos, ou seja, defesa melhor). Times no quadrante "
    "superior direito atacam bem e defendem bem. (Sempre mostra todos os times.)"
)

team_stats = get_team_game_stats()
pontos_feitos = team_metric_ranking(team_stats, "pontos")
pontos_sofridos = team_metric_ranking(team_stats, "pontos_sofridos")

pontos_times = []
for tid, ataque in pontos_feitos.items():
    defesa = pontos_sofridos.get(tid)
    if defesa is None:
        continue
    time = teams_by_id.get(str(tid), {})
    nome = time.get("nome", "?")
    pontos_times.append(
        {
            "ataque": ataque["media"],
            "defesa": defesa["media"],
            "grupo": nome,
            "cor": time.get("cor") or "#888888",
            "hover": (
                f"{nome}<br>Pontos marcados/jogo: {ataque['media']:.1f}"
                f"<br>Pontos sofridos/jogo: {defesa['media']:.1f}<br>{ataque['num_jogos']} jogo(s)"
            ),
        }
    )

fig = scatter_with_medians(
    pontos_times, "ataque", "defesa", "Pontos marcados por jogo", "Pontos sofridos por jogo", y_reversed=True
)
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)

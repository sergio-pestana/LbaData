"""Relações entre métricas que uma tabela não mostra bem — estilo dos
gráficos de análise avançada de basquete (usage vs. efficiency, shot profile,
off/def rating). Substituiu o "top 5 por métrica" (que duplicava a tabela
ordenável de Estatísticas — decisão do usuário ao revisar o dashboard). Os
índices de Utilização (FR-011), Impacto/z-score (FR-012) e Defesa continuam
implementados e testados em `modeling/usage.py`, `modeling/impact.py` e
`modeling/defense.py`, só não ficam todos em destaque nesta tela.

Cor de cada ponto = cor real do time (mesma da tabela de classificação),
resolvida com fallback determinístico (`cor_time`) para times sem cor
cadastrada ou com cor branca demais para o fundo claro do dashboard. Nenhum
jogador é filtrado ou destacado por quantidade de jogos: quem jogou aparece,
com o número de jogos sempre visível no hover (decisão do usuário ao revisar
o dashboard). Os gráficos por jogador mostram o nome ao lado de cada ponto
(mesmo com sobreposição visual) para que dê para identificar cada jogador
depois de filtrar por time (decisão do usuário).
"""

import streamlit as st

from dashboard.theme import (
    apply_theme,
    cor_time,
    get_torneio_selecionado,
    page_description,
    player_lookup,
    scatter_with_medians,
    section_label,
    team_lookup,
)
from modeling.defense import defense_index
from modeling.leaderboards import player_stats_table, team_metric_ranking
from modeling.usage import usage_index
from storage.reads import get_player_game_stats, get_players, get_team_game_stats, get_teams

apply_theme("Análises avançadas")

torneio = get_torneio_selecionado()

page_description(
    "Gráficos que cruzam duas estatísticas ao mesmo tempo, para ver relações que uma "
    "tabela não mostra fácil — por exemplo, quem arremessa muito E converte bem, ao "
    "mesmo tempo. Cada explicação abaixo do gráfico diz como ler os quadrantes."
)

teams = get_teams(torneio["tournament_id"])
teams_by_id = team_lookup(teams)
players_by_id = player_lookup(get_players(torneio["tournament_id"]))

nomes_times = [t["nome"] for t in teams]
times_escolhidos = st.multiselect("Times (para os gráficos por jogador)", nomes_times, default=nomes_times)
ids_escolhidos = {str(t["id"]) for t in teams if t["nome"] in times_escolhidos}

stats = [row for row in get_player_game_stats(torneio["phase_ids"]) if str(row["time_id_na_partida"]) in ids_escolhidos]
usage_ranking = {row["player_id"]: row for row in usage_index(stats)}
defense_ranking = {row["player_id"]: row for row in defense_index(stats)}
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
                "cor": cor_time(time),
                "rotulo": player["nome"] if player else "?",
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
    "🤓 Como ler: cada bolinha é um jogador. Quanto mais **pra direita**, mais aquele "
    "jogador \"pega a bola\" no ataque do time (arremessa ou sofre falta com frequência). "
    "Quanto mais **pra cima**, mais ele produz por minuto em quadra (Eficiência). "
    "Bolinha no canto de cima à direita = pega bastante bola E aproveita bem."
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

fig = scatter_with_medians(
    pontos, "utilizacao", "eficiencia", "Índice de utilização (por minuto)", "Eficiência média por jogo",
    mostrar_rotulos=True,
)
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Eficiência × Plus/Minus
# ---------------------------------------------------------------------------
section_label("Eficiência × Plus/Minus")
st.caption(
    "🤓 Como ler: cada bolinha é um jogador. **De baixo pra cima**: o quanto ele produz "
    "(Eficiência). **Da esquerda pra direita**: o quanto o placar do time melhora com ele "
    "em quadra (Plus/Minus). Bolinha no canto de cima à direita = joga bem E o time vai "
    "bem com ele dentro — os dois lados do que se costuma chamar de \"impacto\"."
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

fig = scatter_with_medians(
    pontos, "plus_minus", "eficiencia", "Plus/Minus médio", "Eficiência média por jogo",
    mostrar_rotulos=True,
)
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. TS% × Volume de arremessos
# ---------------------------------------------------------------------------
section_label("Eficiência de arremesso (TS%) × Volume")
st.caption(
    "🤓 Como ler: cada bolinha é um jogador. **Da esquerda pra direita**: quantos "
    "arremessos ele tenta por jogo (o quanto ele \"atira\"). **De baixo pra cima**: o quão "
    "bem ele converte esses arremessos (TS% já dá peso extra pra cesta de 3 e desconta o "
    "lance livre, que é mais fácil). Bolinha no canto de cima à direita = arremessa "
    "bastante E converte bem — os cestinhas mais completos do time."
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

fig = scatter_with_medians(
    pontos, "tentativas", "ts_pct", "Tentativas de arremesso por jogo", "TS%",
    mostrar_rotulos=True,
)
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 4. Eficiência × Defesa
# ---------------------------------------------------------------------------
section_label("Eficiência × Defesa")
st.caption(
    "🤓 Como ler: cada bolinha é um jogador. **Da esquerda pra direita**: o quanto ele "
    "contribui na defesa por minuto (rebote defensivo + roubo de bola + toco — a fonte "
    "não tem uma estatística de \"posses defensivas\" pronta, então somamos essas três). "
    "**De baixo pra cima**: o quanto ele produz no geral (Eficiência, que já soma ataque e "
    "defesa). Bolinha no canto de cima à direita = forte na defesa E com boa produção geral."
)

pontos = []
for base in _base_pontos():
    defesa_row = defense_ranking.get(base["player_id"])
    if defesa_row is None:
        continue
    pontos.append(
        {
            **base,
            "defesa": defesa_row["valor"],
            "eficiencia": base["linha"]["eficiencia_media"],
            "hover": (
                f"{base['nome']} ({base['grupo']})<br>Defesa: {defesa_row['valor']:.2f}/min"
                f"<br>Eficiência média: {base['linha']['eficiencia_media']:.1f}<br>{base['jogos']} jogo(s)"
            ),
        }
    )

fig = scatter_with_medians(
    pontos, "defesa", "eficiencia", "Índice de defesa (por minuto)", "Eficiência média por jogo",
    mostrar_rotulos=True,
)
if fig is None:
    st.info("Sem jogos suficientes para montar o gráfico ainda.")
else:
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 5. Ataque × Defesa por time
# ---------------------------------------------------------------------------
section_label("Ataque × Defesa por time")
st.caption(
    "🤓 Como ler: aqui cada bolinha é um TIME, não um jogador. **Da esquerda pra "
    "direita**: quantos pontos o time faz por jogo. **De baixo pra cima**: quanto MENOS "
    "pontos o time toma por jogo (o eixo é invertido de propósito — pra cima é defesa "
    "melhor). Bolinha no canto de cima à direita = ataca bem E defende bem. (Sempre "
    "mostra todos os times, sem filtro.)"
)

team_stats = get_team_game_stats(torneio["phase_ids"])
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
            "cor": cor_time(time),
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

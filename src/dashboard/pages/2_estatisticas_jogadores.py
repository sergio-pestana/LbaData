"""Estatísticas de jogadores e times por critério (FR-009, User Story 3).

Duas seções: ranking de TIMES (total e média) por uma métrica escolhida, e a
tabela completa de jogadores com todas as métricas — ordenável clicando nos
cabeçalhos (nativo do `st.dataframe`), com filtro de time e alternância
Total/Média.
"""

import pandas as pd
import streamlit as st

from dashboard.theme import (
    apply_theme,
    confidence_badge,
    get_torneio_selecionado,
    page_description,
    player_lookup,
    section_title,
    team_lookup,
)
from modeling.leaderboards import (
    PLAYER_METRIC_LABELS,
    TEAM_METRIC_LABELS,
    player_stats_table,
    team_metric_ranking,
)
from storage.reads import get_player_game_stats, get_players, get_team_game_stats, get_teams

apply_theme("Estatísticas")

torneio = get_torneio_selecionado()

page_description(
    "Números de times e jogadores da temporada: ranking de times por qualquer "
    "métrica, e a tabela completa com todas as estatísticas de cada jogador. "
    "Não sabe o que alguma sigla ou termo significa?"
)
st.page_link("pages/4_glossario.py", label="Ver o glossário de termos", icon="📖")

teams = get_teams(torneio["tournament_id"])
teams_by_id = team_lookup(teams)
players_by_id = player_lookup(get_players(torneio["tournament_id"]))

# ---------------------------------------------------------------------------
# Ranking de times
# ---------------------------------------------------------------------------
section_title("Estatísticas dos times")

metrica_time_label = st.selectbox("Métrica", list(TEAM_METRIC_LABELS.values()), key="metrica_time")
metrica_time = next(k for k, v in TEAM_METRIC_LABELS.items() if v == metrica_time_label)

ranking_times = team_metric_ranking(get_team_game_stats(torneio["phase_ids"]), metrica_time)

col_total, col_media = st.columns(2)
for col, chave, titulo in ((col_total, "total", "Total"), (col_media, "media", "Média por jogo")):
    with col:
        st.markdown(f"**{titulo}**")
        ordenado = sorted(ranking_times.items(), key=lambda kv: kv[1][chave], reverse=True)
        for posicao, (team_id, dados) in enumerate(ordenado, start=1):
            nome = teams_by_id.get(str(team_id), {}).get("nome", "?")
            valor = dados[chave]
            valor_fmt = f"{valor:.1f}" if chave == "media" else f"{valor:.0f}"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;padding:6px 4px;"
                f"border-bottom:1px solid var(--lba-hairline);'>"
                f"<span><strong>{posicao}.</strong> {nome}</span>"
                f"<span style='font-variant-numeric:tabular-nums;'><strong>{valor_fmt}</strong> "
                f"<span style='color:var(--lba-ink-muted);font-size:12px;'>{dados['num_jogos']} jogo(s)</span>"
                f"{confidence_badge(dados['baixa_confianca'])}</span></div>",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Tabela completa de jogadores
# ---------------------------------------------------------------------------
section_title("Estatísticas dos jogadores")

col_time, col_modo = st.columns([2, 1])
with col_time:
    opcoes_time = ["Liga inteira"] + [t["nome"] for t in teams]
    time_escolhido = st.selectbox("Time", opcoes_time, key="time_estatisticas")
with col_modo:
    modo = st.radio("Mostrar", ["Total", "Média"], horizontal=True, key="modo_estatisticas")

team_id = None
if time_escolhido != "Liga inteira":
    team_id = next(t["id"] for t in teams if t["nome"] == time_escolhido)

stats = get_player_game_stats(torneio["phase_ids"], team_id=str(team_id) if team_id else None)
tabela = player_stats_table(stats)

if not tabela:
    st.info("Sem estatísticas suficientes para este filtro ainda.")
else:
    sufixo = "_total" if modo == "Total" else "_media"
    registros = []
    for linha in tabela:
        player = players_by_id.get(str(linha["player_id"]))
        registro = {
            "Jogador": player["nome"] if player else "?",
            "Time": teams_by_id.get(str(player["team_id"]), {}).get("nome", "") if player else "",
            "Jogos": linha["jogos"],
        }
        for campo, label in PLAYER_METRIC_LABELS.items():
            registro[label] = round(linha[f"{campo}{sufixo}"], 1)
        registro["FG2%"] = round(linha["fg2_pct"], 1)
        registro["FG3%"] = round(linha["fg3_pct"], 1)
        registro["FT%"] = round(linha["ft_pct"], 1)
        registro["TS%"] = round(linha["ts_pct"], 1)
        registro["AST/TO"] = round(linha["ast_to_ratio"], 2) if linha["ast_to_ratio"] is not None else None
        registros.append(registro)

    df = pd.DataFrame(registros).sort_values("Pontos", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True, height=560)
    st.caption(
        "Clique no cabeçalho de qualquer coluna para ordenar por ela. "
        "TS% (True Shooting) pesa arremessos de 3 e lances livres; AST/TO fica em branco "
        "quando o jogador não tem nenhum turnover na amostra."
    )

"""Visão Geral: quantos jogos já aconteceram/faltam + classificação atual
(FR-007, FR-008, User Story 2)."""

from datetime import datetime, timezone

import streamlit as st

from dashboard.theme import apply_theme, get_phase_id, render_table, team_lookup, team_cell
from modeling.standings import current_standings, season_overview
from storage.reads import get_games, get_latest_standings_snapshot, get_teams

apply_theme("Visão geral")

phase_id = get_phase_id()

games = get_games(phase_id)
overview = season_overview(games)

total_previsto = overview["jogos_realizados"] + overview["jogos_restantes"]

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"""<div class="lba-tile accent">
            <div class="lba-label">Jogos realizados</div>
            <div class="lba-value">{overview['jogos_realizados']}</div>
            <div class="lba-sub">de {total_previsto} na temporada regular</div>
        </div>""",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""<div class="lba-tile">
            <div class="lba-label">Jogos restantes</div>
            <div class="lba-value">{overview['jogos_restantes']}</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.markdown("<div class='lba-section-label'>Classificação</div>", unsafe_allow_html=True)

snapshot = get_latest_standings_snapshot(phase_id)
teams_by_id = team_lookup(get_teams())
standings = current_standings(snapshot)

if not standings:
    st.info("Ainda não há classificação coletada para esta fase.")
else:
    rows = []
    for row in standings:
        team = teams_by_id.get(str(row["team_id"]))
        saldo = row["saldo_pontos"]
        saldo_html = (
            f'<span class="lba-balance-pos">+{saldo}</span>'
            if saldo >= 0
            else f'<span class="lba-balance-neg">{saldo}</span>'
        )
        rows.append(
            [
                str(row["posicao"]),
                team_cell(team),
                str(row["jogos"]),
                str(row["vitorias"]),
                str(row["derrotas"]),
                saldo_html,
                f"<strong>{row['pontos_fiba']:.0f}</strong>",
            ]
        )
    row_classes = ["lba-leader" if row["posicao"] == 1 else "" for row in standings]
    render_table(
        ["", "Time", "J", "V", "D", "Saldo", "Pts FIBA"],
        rows,
        num_cols={2, 3, 4, 5, 6},
        row_classes=row_classes,
    )

    coletado_em = standings[0]["coletado_em"]
    if isinstance(coletado_em, datetime):
        atualizado = coletado_em.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    else:
        atualizado = str(coletado_em)
    st.markdown(
        f"<div class='lba-footnote'>Classificação já computada e ordenada pela fonte "
        f"(go-champs), com critérios de desempate oficiais aplicados. "
        f"Última coleta: {atualizado}.</div>",
        unsafe_allow_html=True,
    )

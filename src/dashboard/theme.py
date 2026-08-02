"""Shell visual compartilhado por todas as páginas do dashboard.

Cada página do Streamlit roda como um script independente, então o CSS
precisa ser (re)injetado em cada uma — por isso este módulo centraliza o
tema (chamado uma vez no topo de cada `pages/*.py`) em vez de duplicar a
folha de estilos em cada arquivo (Princípio VI).
"""

from __future__ import annotations

import hashlib
import statistics

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from collector.tournaments import TORNEIOS, fase_de_classificacao

load_dotenv()


def resolver_torneio(nome: str) -> dict:
    """Lógica pura (sem Streamlit) por trás do seletor — separada para ser
    testável sem precisar de um contexto de app rodando (Princípio III).

    Retorna `nome`, `tournament_id` (para `get_teams`/`get_players`),
    `phase_ids` (todas as fases do torneio, para `get_games`/
    `get_player_game_stats`/`get_team_game_stats`) e
    `phase_id_classificacao` (a fase que gera tabela de classificação, ou
    `None` se nenhuma gerar — ex.: um torneio só com fases de chaveamento)."""
    torneio = next(t for t in TORNEIOS if t.nome == nome)
    fase_classificacao = fase_de_classificacao(torneio)
    return {
        "nome": torneio.nome,
        "tournament_id": torneio.tournament_id,
        "phase_ids": [f.phase_id for f in torneio.fases],
        "phase_id_classificacao": fase_classificacao.phase_id if fase_classificacao else None,
    }


def resolver_slug_inicial(slug_da_url: str | None) -> str:
    """Slug a usar como seleção inicial do seletor: o da URL, se for
    conhecido; senão o primeiro torneio do registro. Separado para ser
    testável sem depender de `st.query_params`."""
    slugs_validos = {t.slug for t in TORNEIOS}
    if slug_da_url in slugs_validos:
        return slug_da_url
    return TORNEIOS[0].slug


def get_torneio_selecionado() -> dict:
    """Seletor de torneio na sidebar — troca o contexto inteiro do dashboard
    (User Story 3 de specs/002-add-series-2025-2026).

    Testado manualmente contra os links de navegação nativos do
    `st.navigation`: nem `st.session_state` isolado nem `st.query_params`
    isolado sobreviveram de forma confiável à troca de página (os links do
    menu lateral navegam para a URL "limpa" da página, sem preservar a
    query string, e o widget perdia a seleção anterior). Guardar a escolha
    nos dois ao mesmo tempo — e ler de qualquer um que ainda tiver o valor —
    cobre esse caso."""
    nomes = [t.nome for t in TORNEIOS]
    slug_atual = st.session_state.get("torneio_slug") or st.query_params.get("torneio")
    slug_inicial = resolver_slug_inicial(slug_atual)
    index_inicial = next(i for i, t in enumerate(TORNEIOS) if t.slug == slug_inicial)

    nome_escolhido = st.sidebar.selectbox("Torneio", nomes, index=index_inicial, key="torneio_nome_widget")
    torneio = next(t for t in TORNEIOS if t.nome == nome_escolhido)

    st.session_state["torneio_slug"] = torneio.slug
    st.query_params["torneio"] = torneio.slug

    return resolver_torneio(nome_escolhido)

_CSS = """
<style>
:root {
  --lba-surface: #ffffff;
  --lba-surface-2: #f4f4f5;
  --lba-ink-primary: #1a1a1a;
  --lba-ink-secondary: #55575c;
  --lba-ink-muted: #86888c;
  --lba-accent: #e8672c;
  --lba-hairline: #e2e3e6;
  --lba-good: #1f9d4a;
}

.lba-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.lba-tile {
  background: var(--lba-surface-2);
  border: 1px solid var(--lba-hairline);
  border-radius: 12px;
  padding: 16px 18px;
}
.lba-tile .lba-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--lba-ink-muted);
  margin-bottom: 8px;
}
.lba-tile .lba-value {
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  color: var(--lba-ink-primary);
}
.lba-tile.accent .lba-value { color: var(--lba-accent); }
.lba-tile .lba-sub {
  margin-top: 6px;
  font-size: 12px;
  color: var(--lba-ink-muted);
}

.lba-section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--lba-ink-muted);
  margin: 18px 0 10px 2px;
}

.lba-table-wrap {
  background: var(--lba-surface);
  border: 1px solid var(--lba-hairline);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  overflow-x: auto;
}
table.lba-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
table.lba-table th {
  text-align: left;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--lba-ink-muted);
  padding: 12px 10px;
  border-bottom: 1px solid var(--lba-hairline);
  white-space: nowrap;
}
table.lba-table td {
  padding: 10px 10px;
  border-bottom: 1px solid var(--lba-hairline);
  color: var(--lba-ink-primary);
}
table.lba-table tr:last-child td { border-bottom: none; }
table.lba-table th.num, table.lba-table td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
tr.lba-leader td:first-child { box-shadow: inset 3px 0 0 var(--lba-good); }

.lba-team-cell { display: flex; align-items: center; gap: 10px; }
.lba-swatch {
  width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 0 1px var(--lba-hairline);
}
.lba-team-name { font-weight: 600; }
.lba-team-code {
  color: var(--lba-ink-muted); font-size: 11.5px; font-weight: 600; letter-spacing: 0.04em;
}
.lba-badge-low {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--lba-ink-muted);
  border: 1px solid var(--lba-hairline);
  border-radius: 5px;
  padding: 1px 6px;
  margin-left: 6px;
}
.lba-balance-pos { color: var(--lba-good); }
.lba-balance-neg { color: var(--lba-ink-secondary); }
.lba-footnote {
  margin-top: 12px;
  font-size: 11.5px;
  color: var(--lba-ink-muted);
  line-height: 1.5;
}
.lba-intro {
  background: var(--lba-surface-2);
  border: 1px solid var(--lba-hairline);
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--lba-ink-secondary);
  line-height: 1.6;
}
.lba-page-desc {
  font-size: 14px;
  color: var(--lba-ink-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
}
.lba-section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--lba-ink-primary);
  margin: 22px 0 10px 2px;
}
</style>
"""


def apply_theme(page_title: str) -> None:
    """Injeta o CSS compartilhado e o título da página.

    `st.set_page_config` é chamado uma única vez em `app.py` (via
    `st.navigation`) — chamá-lo de novo aqui quebraria o roteamento, por isso
    esta função cuida só do CSS e do título visível.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    st.title(page_title)


def render_tiles(tiles: list[dict]) -> None:
    """`tiles`: lista de {"label", "value", "sub"="", "accent"=False}."""
    html = ['<div class="lba-tiles">']
    for t in tiles:
        classes = "lba-tile accent" if t.get("accent") else "lba-tile"
        sub = f'<div class="lba-sub">{t["sub"]}</div>' if t.get("sub") else ""
        html.append(
            f'<div class="{classes}"><div class="lba-label">{t["label"]}</div>'
            f'<div class="lba-value">{t["value"]}</div>{sub}</div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f'<div class="lba-section-label">{text}</div>', unsafe_allow_html=True)


def section_title(text: str) -> None:
    """Título de seção maior/mais destacado que `section_label` — usado para
    separar blocos grandes de conteúdo (ex.: "Times" vs. "Jogadores" na
    página de Estatísticas), não pequenos rótulos de gráfico."""
    st.markdown(f'<div class="lba-section-title">{text}</div>', unsafe_allow_html=True)


def page_description(text: str) -> None:
    """Parágrafo curto de contexto no topo de uma página (o que ela mostra),
    em texto simples — não é o disclaimer da Visão geral, é só a descrição
    da página."""
    st.markdown(f'<div class="lba-page-desc">{text}</div>', unsafe_allow_html=True)


def confidence_badge(baixa_confianca: bool) -> str:
    return '<span class="lba-badge-low">poucos jogos</span>' if baixa_confianca else ""


def team_lookup(teams: list[dict]) -> dict:
    return {str(t["id"]): t for t in teams}


def player_lookup(players: list[dict]) -> dict:
    return {str(p["id"]): p for p in players}


# Paleta de fallback para times sem `cor` na fonte, ou com uma cor branca/
# quase-branca demais para aparecer num fundo branco (ver research.md do
# fundo claro) — atribuída de forma determinística por hash do id do time,
# então o mesmo time sempre cai na mesma cor entre execuções, sem precisar
# gravar nada a mais no banco.
_PALETA_FALLBACK = (
    "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
    "#8c564b", "#17becf", "#e377c2", "#bcbd22", "#3182bd",
    "#843c39", "#5254a3", "#8c6d31", "#c49c94", "#7b4173",
)


def _cor_visivel_em_branco(cor: str | None) -> bool:
    """`False` para cor ausente ou clara demais (perto de branco) — não dá
    pra enxergar num fundo branco."""
    if not cor:
        return False
    hex_val = cor.lstrip("#")
    if len(hex_val) != 6:
        return False
    try:
        r, g, b = (int(hex_val[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    luminancia = 0.299 * r + 0.587 * g + 0.114 * b
    return luminancia < 235


def cor_time(team: dict | None) -> str:
    """Cor do time para swatches/gráficos: a da fonte, se for visível num
    fundo branco; senão uma cor estável da paleta de fallback, escolhida por
    hash do id do time (nunca cinza genérico igual pra todos, mesmo quando
    nenhum time do torneio tem `cor` cadastrada)."""
    if team is None:
        return "#888888"
    cor = team.get("cor")
    if _cor_visivel_em_branco(cor):
        return cor
    indice = int(hashlib.md5(str(team["id"]).encode()).hexdigest(), 16) % len(_PALETA_FALLBACK)
    return _PALETA_FALLBACK[indice]


def team_cell(team: dict | None) -> str:
    if team is None:
        return '<div class="lba-team-cell"><span class="lba-team-name">?</span></div>'
    cor = cor_time(team)
    return (
        f'<div class="lba-team-cell"><span class="lba-swatch" style="background:{cor}"></span>'
        f'<span class="lba-team-name">{team["nome"]}</span>'
        f'<span class="lba-team-code">{team["tri_code"]}</span></div>'
    )


def _default_zoom_range(values: list[float]) -> tuple[float, float] | None:
    """Faixa de zoom inicial "sensata" pelo método do intervalo interquartil
    (Q1/Q3 ± 1,5×IQR — a mesma regra clássica de outlier de boxplot), sem
    excluir nenhum ponto dos dados: é só o enquadramento inicial da câmera.
    O usuário sempre pode clicar em "reset axes" na barra do gráfico (ou dar
    zoom out) para ver o dado completo, outlier incluído.

    Retorna `None` quando não há pontos suficientes ou não há dispersão
    (nesse caso o autorange padrão do Plotly já cobre tudo direito).
    """
    if len(values) < 4:
        return None
    ordenados = sorted(values)
    q1, _, q3 = statistics.quantiles(ordenados, n=4)
    iqr = q3 - q1
    if iqr == 0:
        return None
    baixo = max(min(ordenados), q1 - 1.5 * iqr)
    alto = min(max(ordenados), q3 + 1.5 * iqr)
    if baixo >= alto:
        return None
    folga = (alto - baixo) * 0.1
    return (baixo - folga, alto + folga)


def scatter_with_medians(
    pontos: list[dict],
    x_key: str,
    y_key: str,
    x_title: str,
    y_title: str,
    height: int = 480,
    y_reversed: bool = False,
    mostrar_rotulos: bool = False,
) -> go.Figure | None:
    """Scatterplot padrão do dashboard: um ponto por item de `pontos`, com
    linhas pontilhadas na mediana de cada eixo (leitura por quadrante).

    Cada dict em `pontos` precisa de `x_key`, `y_key`, `grupo` (nome exibido
    na legenda — normalmente o time), `cor` (hex do grupo) e `hover` (texto
    pronto). Uma trace do Plotly por grupo/time — dá legenda nativa (clicável
    para esconder/mostrar) e cor consistente com o resto do dashboard.

    `mostrar_rotulos=True` escreve o nome ao lado de cada ponto (espera uma
    chave `"rotulo"` em cada item de `pontos`) — usado nos gráficos por
    jogador, onde vários pontos do mesmo time (mesma cor) só ficam
    distinguíveis com o nome visível, mesmo com a poluição visual que isso
    causa (decisão do usuário ao revisar o dashboard).

    Nenhum ponto é excluído dos dados, mas o zoom inicial é ajustado para não
    deixar um outlier estatístico esmagar a escala e tornar todo o resto do
    gráfico ilegível (ver `_default_zoom_range`) — o outlier continua lá, só
    não dita o enquadramento padrão.

    Retorna `None` se não houver pontos.
    """
    if not pontos:
        return None

    xs = [p[x_key] for p in pontos]
    ys = [p[y_key] for p in pontos]

    grupos: dict[str, dict] = {}
    for p in pontos:
        grupo = grupos.setdefault(
            p["grupo"], {"cor": p["cor"], "xs": [], "ys": [], "hover": [], "rotulos": []}
        )
        grupo["xs"].append(p[x_key])
        grupo["ys"].append(p[y_key])
        grupo["hover"].append(p["hover"])
        grupo["rotulos"].append(p.get("rotulo", ""))

    fig = go.Figure()

    if len(xs) >= 2:
        fig.add_vline(x=statistics.median(xs), line_width=1, line_dash="dot", line_color="#c2c4c9")
        fig.add_hline(y=statistics.median(ys), line_width=1, line_dash="dot", line_color="#c2c4c9")

    for nome_grupo, dados in grupos.items():
        fig.add_trace(
            go.Scatter(
                x=dados["xs"],
                y=dados["ys"],
                mode="markers+text" if mostrar_rotulos else "markers",
                name=nome_grupo,
                marker=dict(size=12, color=dados["cor"], line=dict(width=1, color="#ffffff")),
                text=dados["rotulos"] if mostrar_rotulos else None,
                textposition="top center",
                textfont=dict(size=9, color="#2a2b2e"),
                customdata=dados["hover"],
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )

    x_range = _default_zoom_range(xs)
    if x_range:
        fig.update_xaxes(range=x_range)

    y_range = _default_zoom_range(ys)
    if y_range:
        fig.update_yaxes(range=(y_range[1], y_range[0]) if y_reversed else y_range)
    elif y_reversed:
        fig.update_yaxes(autorange="reversed")

    return fig


def render_table(
    headers: list[str],
    rows_html: list[list[str]],
    num_cols: set[int] | None = None,
    row_classes: list[str] | None = None,
) -> None:
    """`rows_html`: cada linha já é uma lista de strings HTML prontas por
    célula. `num_cols`: índices de coluna alinhados à direita/tabular.
    `row_classes`: classe CSS extra por linha (ex.: "lba-leader"), na mesma
    ordem de `rows_html`."""
    num_cols = num_cols or set()
    row_classes = row_classes or [""] * len(rows_html)
    thead = "".join(
        f'<th class="num">{h}</th>' if i in num_cols else f"<th>{h}</th>"
        for i, h in enumerate(headers)
    )
    body = []
    for row, extra_class in zip(rows_html, row_classes):
        cells = "".join(
            f'<td class="num">{c}</td>' if i in num_cols else f"<td>{c}</td>"
            for i, c in enumerate(row)
        )
        body.append(f'<tr class="{extra_class}">{cells}</tr>')

    html = (
        '<div class="lba-table-wrap"><table class="lba-table">'
        f"<thead><tr>{thead}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)

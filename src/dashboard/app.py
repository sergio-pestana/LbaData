"""Entrypoint do dashboard Streamlit — LBA POA Ouro 2026.

Define a navegação multipágina explicitamente (título/ícone por página, em
vez dos nomes de arquivo crus que o roteamento automático do Streamlit
mostraria) — o conteúdo de cada camada de análise vive em `pages/*.py`.
"""

import streamlit as st

st.set_page_config(page_title="LBA POA Ouro 2026", page_icon="🏀", layout="wide")

pages = {
    "Análise": [
        st.Page("pages/1_visao_geral.py", title="Visão geral", icon="🏀", default=True),
        st.Page("pages/2_estatisticas_jogadores.py", title="Estatísticas de jogadores", icon="📊"),
        st.Page("pages/3_impacto_e_utilizacao.py", title="Impacto e utilização", icon="🎯"),
    ],
    "Ajuda": [
        st.Page("pages/4_glossario.py", title="Glossário", icon="📖"),
    ],
}

pg = st.navigation(pages)
pg.run()

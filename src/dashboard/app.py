"""Entrypoint do dashboard Streamlit — LBA POA Ouro 2026.

Define a navegação multipágina explicitamente (título/ícone por página, em
vez dos nomes de arquivo crus que o roteamento automático do Streamlit
mostraria) — o conteúdo de cada camada de análise vive em `pages/*.py`.
"""

import os
import sys

# Permite `import dashboard`, `import modeling`, `import storage` etc. mesmo
# quando quem roda o app não define PYTHONPATH=src manualmente (ex.: Streamlit
# Community Cloud, que só executa `streamlit run src/dashboard/app.py` a
# partir da raiz do repositório) — mesma ideia do conftest.py usado pelos
# testes, aplicada ao próprio app.
_SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import streamlit as st

st.set_page_config(page_title="LBA POA Ouro 2026", page_icon="🏀", layout="wide")

pages = {
    "Análise": [
        st.Page("pages/1_visao_geral.py", title="Visão geral", icon="🏀", default=True),
        st.Page("pages/2_estatisticas_jogadores.py", title="Estatísticas", icon="📊"),
        st.Page("pages/3_impacto_e_utilizacao.py", title="Análises avançadas", icon="🎯"),
    ],
    "Ajuda": [
        st.Page("pages/4_glossario.py", title="Glossário", icon="📖"),
    ],
}

pg = st.navigation(pages)
pg.run()

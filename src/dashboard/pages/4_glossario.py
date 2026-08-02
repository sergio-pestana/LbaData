"""Glossário — o que cada métrica/gráfico do dashboard significa."""

import streamlit as st

from dashboard.theme import apply_theme, section_label

apply_theme("Glossário")

st.caption("Referência rápida de todos os termos usados nas outras páginas.")

section_label("Classificação")
st.markdown(
    """
- **J / V / D** — Jogos, Vitórias, Derrotas.
- **Saldo** — soma de (pontos marcados − pontos sofridos) em todos os jogos da temporada.
- **Pts FIBA** — pontos de classificação no critério oficial da FIBA (2 por vitória, 1 por derrota); é o critério principal de ordenação da tabela.
- A ordem da classificação e os critérios de desempate (confronto direto, saldo, etc.) vêm prontos da própria fonte (go-champs) — o dashboard não recalcula desempates.
"""
)

section_label("Total vs. Média")
st.markdown(
    """
- **Total** — soma da métrica em todos os jogos que o jogador/time efetivamente disputou na temporada.
- **Média** — total dividido pelo número de jogos disputados (não pelo total de jogos da temporada, então quem entrou depois não é penalizado).
- Percentuais e razões (FG%, TS%, AST/TO) **não têm** versão Total — são sempre calculados a partir dos totais da temporada, nunca como média ingênua da porcentagem de cada jogo (um jogador de 1/1 num jogo e 0/3 no outro não tem "75% de média", tem 25% de aproveitamento real: 1 de 4).
"""
)

section_label("Estatísticas básicas (por jogador)")
st.markdown(
    """
- **Pontos** — pontos marcados.
- **Rebotes ofensivos / defensivos** — rebotes pegos no ataque ou na defesa do próprio time.
- **Assistências** — passes que resultaram diretamente em cesta.
- **Roubos de bola** — posses tomadas do adversário.
- **Tocos** — arremessos do adversário bloqueados.
- **Turnovers** — perdas de posse (passe errado, violação, etc.).
- **Faltas** — faltas pessoais cometidas.
- **2PT / 3PT tentados/convertidos** — arremessos de quadra tentados e convertidos, separados por valor (aqui "2PT" nunca inclui os de 3 — são categorias à parte na fonte).
- **LL tentados/convertidos** — lances livres.
- **Plus/Minus** — saldo de pontos do time enquanto o jogador está em quadra.
- **Eficiência** — estatística única já calculada pela fonte, combinando produção (pontos, rebotes, assistências, roubos, tocos) e custo (erros de arremesso, turnovers) num só número.
- **Minutos jogados** — tempo total em quadra.
"""
)

section_label("Estatísticas avançadas")
st.markdown(
    """
- **FG2% / FG3% / FT%** — percentual de acerto em arremessos de 2, de 3, e lances livres (convertidos ÷ tentados).
- **TS% (True Shooting %)** — eficiência geral de arremesso que dá o peso certo para cada tipo: um arremesso de 3 vale mais que um de 2, e um lance livre custa menos que um arremesso de quadra. Fórmula: `pontos ÷ (2 × (arremessos tentados + 0,44 × lances livres tentados)) × 100`. É o número mais completo para comparar "quem arremessa melhor", mais confiável que FG% sozinho.
- **AST/TO (Assistências por Turnover)** — assistências ÷ turnovers. Mede o quão bem um jogador cria jogadas sem perder a bola; fica em branco quando o jogador não tem nenhum turnover na amostra (dividir por zero não vira um número inventado).
- **Índice de utilização** — (arremessos de 2 + de 3 tentados + lances livres tentados + turnovers) ÷ minutos jogados. Aproxima "o quanto o jogador concentra a bola no ataque do time" sem precisar estimar as posses totais do time inteiro.
"""
)

section_label("Gráficos (página Impacto e utilização)")
st.markdown(
    """
- Cada ponto é um jogador (ou time, no gráfico de Ataque × Defesa); passe o mouse para ver o nome, o time e os valores exatos, incluindo o número de jogos.
- **Cor do ponto** é a cor real do time (a mesma da tabela de classificação) — clique num nome na legenda para esconder/mostrar só aquele time no gráfico.
- **Linhas pontilhadas** marcam a mediana de cada eixo, dividindo o gráfico em quadrantes — útil para ler "quem está acima da média nos dois eixos ao mesmo tempo".
- O filtro de time no topo da página aceita **múltiplos times** ao mesmo tempo, não só um.
- Todo jogador que disputou ao menos uma partida aparece nos gráficos — não há corte por número de jogos; o total de jogos de cada um fica sempre visível no hover.
- O **zoom inicial** de cada gráfico ignora outliers estatísticos extremos (ex.: um jogador com pouquíssimos minutos) para o resto dos pontos não ficar espremido — mas ninguém é removido dos dados. Clique no ícone de "reset axes" (canto superior direito do gráfico) para ver tudo, outlier incluído.
"""
)

section_label("Baixa confiança")
st.markdown(
    """
Sempre que um número for calculado sobre poucos jogos, o dashboard sinaliza isso
em vez de deixar parecer tão confiável quanto um número baseado em uma temporada
inteira — é um princípio central do projeto: **nenhuma métrica aparece sem deixar
claro o tamanho da amostra por trás dela.**
"""
)

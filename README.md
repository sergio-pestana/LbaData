# LBA POA — Plataforma de Acompanhamento e Análise

Projeto de torcedor (não afiliado à liga) que transforma os dados públicos
da LBA POA — liga amadora de basquete de Porto Alegre — num painel de
estatísticas avançadas, temporada a temporada.

A liga já publica a súmula completa de cada jogo. O que falta é comparação:
quem é realmente eficiente, quem está melhorando, o que cada time faz bem
ou mal. É isso que a plataforma calcula.

## Exemplo do tipo de pergunta que ela responde

- **"Esse jogador arremessa muito, mas converte bem?"**
  → TS% (*True Shooting*), que já pesa o valor extra da cesta de 3 e o
  custo baixo do lance livre — mais confiável que olhar só o aproveitamento
  bruto.

- **"Esse time melhorou ou piorou de uma temporada pra outra?"**
  → mesma métrica, duas temporadas lado a lado. Ex. real encontrado num dos
  relatórios: um time manteve o volume ofensivo intacto, mas passou a
  sofrer ~10 pontos a mais por jogo — o motivo real de estar na última
  colocação, não "falta de sorte".

- **"Quem mais contribui na defesa, já que a súmula não mostra isso
  direto?"**
  → um índice próprio (rebote defensivo + roubo de bola + toco, por
  minuto jogado).

## Métricas criadas (a fonte não tinha nenhuma delas)

A API da liga entrega só a súmula bruta — contagens por jogo (pontos,
rebotes, arremessos tentados/convertidos, Eficiência, Plus/Minus) e, na
maioria dos casos, a classificação corrente. Tudo abaixo é calculado por
cima disso:

| Métrica | Fórmula | O que responde |
|---|---|---|
| **TS%** (True Shooting) | `pontos / (2 × (FGA + 0.44 × FTA)) × 100` | Eficiência de arremesso de verdade — pesa o valor extra da cesta de 3 e o custo menor do lance livre, ao contrário do FG% simples. |
| **Índice de Utilização** | `(2PT + 3PT + LL tentados + turnovers) / minutos` | Quanto um jogador concentra a bola no ataque, sem precisar estimar as posses totais do time. |
| **Índice de Defesa** | `(rebotes defensivos + roubos + tocos) / minutos` | Proxy de envolvimento defensivo — a fonte não tem nada equivalente a um "defensive rating" por jogador. |
| **Índice de Impacto** | `z-score(Eficiência) + z-score(Plus/Minus)`, peso igual | Combina produção bruta com o efeito real no placar numa escala comparável (as duas métricas originais têm magnitudes muito diferentes). |
| **FG2% / FG3% / FT% de temporada** | convertidos ÷ tentados, sobre o total da temporada | Nunca é a média ingênua dos % de cada jogo — isso distorceria quem tem poucas tentativas (ver `research.md`). |
| **AST/TO** | assistências ÷ turnovers, `None` se turnovers = 0 | Qualidade de decisão com a bola, sem inventar um número quando a divisão não existe. |
| **Classificação histórica** | snapshot append-only a cada coleta | A fonte só expõe o estado *atual* da tabela — aqui cada coleta grava uma linha nova, então dá pra reconstruir a evolução rodada a rodada. |
| **Jogos / Pontos FIBA** (só quando a fonte não fornece) | `jogos = V + D`, `pts FIBA = 2×V + D` | Duas temporadas (2025) vêm sem esses campos na classificação — derivados a partir de vitórias/derrotas em vez de deixar a tabela incompleta. |

Toda métrica derivada acima expõe também o número de jogos que a sustenta —
uma média sobre 2 jogos nunca aparece com a mesma confiança visual que uma
sobre 15.

## Arquitetura

```
   Coleta         Armazenamento        Modelagem          Apresentação
 (API pública  →  (Postgres, com   →  (métricas         →  (dashboard em
  da liga)         histórico            derivadas)          Streamlit)
                   preservado)
```

Quatro camadas desacopladas, cada uma só falando com a vizinha por meio de
um contrato estável (schema do banco / retorno de função) — nunca acessando
estrutura interna da outra.

- **Coleta** (`src/collector`) — cliente HTTP sequencial, sem paralelismo,
  com intervalo mínimo entre requisições e checagem de `robots.txt`. Cada
  parser valida presença e tipo dos campos essenciais antes de aceitar um
  registro; campo ausente ou tipo inesperado levanta uma exceção específica
  e loga o `game_id` afetado — o resto da rodada continua processando. Roda
  sozinha toda semana via GitHub Actions (cron em UTC, convertido do
  horário de Porto Alegre).
- **Armazenamento** (`src/storage`) — Postgres via Supabase, acesso direto
  por `psycopg2` com `INSERT ... ON CONFLICT (id) DO UPDATE`, usando o id
  externo da própria fonte como chave — reprocessar um jogo corrige,
  nunca duplica. Tabelas de fato (jogos, estatísticas) só atualizam quando
  algo de fato mudou; a classificação é append-only por design.
- **Modelagem** (`src/modeling`) — funções puras que leem os fatos e
  devolvem valor + contagem de jogos, sem saber nada de SQL. É aqui que
  vivem as métricas da tabela acima.
- **Apresentação** (`src/dashboard`) — Streamlit + Plotly, com seletor de
  torneio trocando o contexto entre as 5 temporadas/séries suportadas
  (Ouro 2026, Prata/Bronze 2026, Ouro 2025, Prata 2025, Bronze 2025).

Testado com `pytest`: testes de contrato validam os parsers contra payloads
reais capturados da API (sem rede em CI); testes de unidade de
armazenamento rodam contra o Postgres de verdade, porque não dá pra testar
`ON CONFLICT` de forma fiel só com mock.

## Como foi construído

Construído com **Claude Code**, usando um fluxo de *Spec-Driven Development*
(spec → plano → tarefas → implementação) — as decisões de arquitetura e
escopo ficam documentadas em `specs/`, junto com o raciocínio por trás de
cada uma.

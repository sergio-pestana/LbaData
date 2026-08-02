---

description: "Task list for Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026"
---

# Tasks: Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026

**Input**: Design documents from `/specs/001-lba-poa-analytics/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes)

**Tests**: Incluídos — a constituição do projeto exige testes que simulem falha/formato inesperado sempre que o tratamento de erros ou o schema esperado da fonte mudar (Fluxo de Desenvolvimento e Qualidade), e `research.md` já define uma estratégia de testes baseada em fixtures.

**Organization**: Ao pedido explícito do usuário, as tarefas são agrupadas por
**camada arquitetural** (Coleta → Armazenamento → Modelagem → Dashboard — Princípio
III da constituição), não por user story. Cada camada só começa depois que a
anterior foi validada manualmente com dados reais (checkpoint no fim de cada
fase). A tag `[USx]` em cada tarefa preserva a rastreabilidade com as user stories
de `spec.md`, mesmo que várias stories tenham tarefas espalhadas por mais de uma
camada (ex.: US1 tem tarefas na Camada 1 e na Camada 2; US2-US6 têm tarefas na
Camada 2 — leitura —, Camada 3 e Camada 4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story esta tarefa pertence (US1..US6) — rastreabilidade, não agrupamento
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Projeto único em Python (ver `plan.md` → Project Structure): `src/collector/`,
`src/storage/`, `src/modeling/`, `src/dashboard/`, `tests/`, `.github/workflows/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Inicialização do projeto

- [X] T001 Criar o esqueleto de diretórios do projeto: `src/collector/`, `src/storage/migrations/`, `src/modeling/`, `src/dashboard/pages/`, `tests/fixtures/`, `tests/unit/collector/`, `tests/unit/storage/`, `tests/unit/modeling/`, `tests/contract/`, `tests/integration/`, `.github/workflows/` (conforme `plan.md`)
- [X] T002 [P] Criar `requirements.txt` na raiz com `requests`, `psycopg2-binary`, `streamlit`, `plotly`, `pandas`, `python-dotenv`, `pytest`
- [X] T003 [P] Criar `.env.example` na raiz documentando `SUPABASE_DB_URL`, `LBA_TOURNAMENT_ID`, `LBA_PHASE_ID`, `COLLECTOR_REQUEST_INTERVAL_SECONDS` (sem valores reais — Princípio V)

**Checkpoint**: `pip install -r requirements.txt` roda sem erro; estrutura de diretórios criada.

---

## Camada 1: Coleta (Priority: P1) 🎯 primeira entrega

**Goal**: Validar, contra a API real do go-champs, que o parsing do coletor extrai
corretamente placar, súmula por jogador e por time — **sem depender de banco de
dados nenhum**. Esta camada é intencionalmente testável isolada (Princípio III):
cliente HTTP + parsers + testes de contrato rodam só com fixtures/rede, nunca
tocam o Supabase.

**Independent Test / Checkpoint desta camada**: Rodar manualmente o cliente contra
os endpoints reais (torneio, jogos da fase, player-stats-logs e team-stats-logs de
pelo menos 1 jogo real, classificação da fase) e inspecionar os registros
parseados no console — **antes de escrever qualquer coisa em banco** — confirmando
que todos os campos essenciais descritos em `contracts/go-champs-api-dependency.md`
aparecem com o tipo esperado.

### Tests

> Escrever estes testes primeiro; devem falhar antes da implementação

- [X] T004 [P] [US1] Capturar payloads reais dos endpoints go-champs (tournament, games por phase, player-stats-logs, team-stats-logs, phase standings) e salvar em `tests/fixtures/*.json` (per `research.md` #8 e `contracts/go-champs-api-dependency.md`)
- [X] T005 [P] [US1] Teste de contrato: parsing do payload de torneio valida `has_aggregated_player_stats` e o catálogo de stats em `tests/contract/test_tournament_parser.py`
- [X] T006 [P] [US1] Teste de contrato: parsing da lista de jogos por fase revalida localmente que cada jogo pertence ao `phase_id` esperado (não confia no filtro `where[]`) em `tests/contract/test_games_parser.py`
- [X] T007 [P] [US1] Teste de contrato: parsing de `player-stats-logs` valida presença/tipo de todos os campos essenciais, incluindo linhas com `game_played=0`, em `tests/contract/test_player_stats_parser.py`
- [X] T008 [P] [US1] Teste de contrato: parsing de `team-stats-logs` em `tests/contract/test_team_stats_parser.py`
- [X] T009 [P] [US1] Teste de contrato: parsing da classificação da fase confirma que todos os times esperados estão presentes antes de aceitar o snapshot em `tests/contract/test_standings_parser.py`
- [X] T010 [P] [US1] Teste de contrato: payload com campo essencial ausente/tipo inesperado levanta `UnexpectedPayloadShape` e é logado, sem derrubar o processamento dos demais jogos, em `tests/contract/test_schema_change_failure.py`
- [X] T011 [US1] Teste de integração manual (não roda em CI) contra a API real do go-champs em `tests/integration/test_live_api.py`

### Implementation

- [X] T012 [P] [US1] Implementar `src/collector/client.py`: cliente HTTP sequencial com intervalo mínimo configurável entre requisições, checagem de `robots.txt` do host, e `User-Agent` identificável (Princípio II, `research.md` #2)
- [X] T013 [P] [US1] Implementar `src/collector/config.py`: carrega `tournament_id`, `phase_id`, intervalo de requisição a partir de variáveis de ambiente
- [X] T014 [US1] Implementar `src/collector/parsers.py`: parsers de torneio, jogos, player-stats-logs, team-stats-logs e classificação da fase, cada um validando campos essenciais e levantando `UnexpectedPayloadShape` em caso de ausência/tipo inesperado (depende de T004-T010 definirem o formato esperado)

**Checkpoint Camada 1**: `pytest tests/contract tests/unit/collector` passa 100% com fixtures; rodar `tests/integration/test_live_api.py` manualmente contra a API real confirma que o formato assumido pelos parsers ainda é válido hoje. **Não avançar para a Camada 2 sem essa confirmação.**

---

## Camada 2: Armazenamento (Priority: P1)

**Goal**: Criar o schema no Supabase e persistir, de forma idempotente, os dados
reais já validados na Camada 1 — e usar exatamente esse momento para confirmar que
o **schema modelado em `data-model.md` bate com o que a API realmente devolve**,
antes de qualquer modelagem ou dashboard serem construídos em cima.

**Independent Test / Checkpoint desta camada**: Com `SUPABASE_DB_HOST`/`_PORT`/`_NAME`/`_USER`/`_PASSWORD` já configuradas
(projeto Supabase existente), rodar `python -m collector.run --phase-id
"$LBA_PHASE_ID"` contra a API real uma vez, depois consultar diretamente as tabelas
(`teams`, `players`, `games`, `player_game_stats`, `team_game_stats`,
`standings_snapshot`) no Supabase e conferir campo a campo contra
`data-model.md`. Rodar a coleta uma segunda vez e confirmar zero duplicatas.

> **Achados já validados na Camada 1** (não precisam de nova validação, só
> aplicação correta no upsert): `minutos_jogados` vem em segundos e já é
> convertido pelo parser (research.md #4); `field_goals_*` é só 2 pontos, nunca
> inclui os de 3 (research.md #10); a classificação exige tradução de chaves
> opacas de `elimination_stats` (research.md #9, já implementada em
> `parse_phase_standings`); todo jogo do torneio real observado tinha
> `is_finished=true` — o caminho `false` continua não exercitado e deve ser
> tratado defensivamente mesmo assim.

### Schema e conexão

- [X] T015 [P] Migration SQL para `teams` e `players` em `src/storage/migrations/0001_teams_players.sql` (campos e chaves per `data-model.md`)
- [X] T016 [P] Migration SQL para `games`, `player_game_stats`, `team_game_stats` em `src/storage/migrations/0002_games_stats.sql`, com constraint de unicidade no id externo do go-champs de cada tabela (chave de conflito do upsert — Princípio I)
- [X] T017 [P] Migration SQL para `standings_snapshot` (append-only, sem constraint de unicidade) em `src/storage/migrations/0003_standings_snapshot.sql`
- [X] T018 Implementar `src/storage/migrations/apply.py`: aplica os arquivos `.sql` de `migrations/` em ordem contra a conexão definida por `SUPABASE_DB_HOST`/`_PORT`/`_NAME`/`_USER`/`_PASSWORD` (depende de T015-T017)
- [X] T019 [P] Implementar `src/storage/supabase_client.py`: helper genérico de conexão `psycopg2` e execução de query, lendo `SUPABASE_DB_HOST`/`_PORT`/`_NAME`/`_USER`/`_PASSWORD` de variáveis de ambiente separadas — nunca uma única URI, para evitar bugs de parsing quando a senha tem caracteres especiais (Princípio V — nenhuma credencial hardcoded)

### Leituras (usadas pela Camada 3)

- [X] T020 [US2] Implementar `src/storage/reads.py`: `get_games(phase_id)`, `get_latest_standings_snapshot(phase_id)`
- [X] T021 [US3] Estender `src/storage/reads.py` com `get_player_game_stats(team_id=None)` (agregável por critério)
- [X] T022 [US4] Estender `src/storage/reads.py` com `get_standings_history(phase_id, team_id)` e `get_player_game_stats_series(player_id)`

### Escrita e orquestração da coleta

- [X] T023 [US1] Implementar `src/storage/upserts.py`: `upsert_team`, `upsert_player`, `upsert_game` (com `corrigido_em` em updates), `upsert_player_game_stat`, `upsert_team_game_stat`, todos via `ON CONFLICT` no id externo, e `insert_standings_snapshot` (append-only) — depende de T019
- [X] T024 [US1] Teste unitário: `upsert_game`/`upsert_player_game_stat` chamados duas vezes com o mesmo id externo atualizam em vez de duplicar; um jogo marcado `cancelada` é preservado (não excluído) em `tests/unit/storage/test_upserts.py`
- [X] T025 [US1] Implementar `src/collector/run.py`: orquestra a coleta de uma rodada — busca jogos da fase, para cada jogo busca+valida+upsert das estatísticas, captura `UnexpectedPayloadShape` por jogo (loga e continua, FR-006), busca a classificação da fase e grava um `standings_snapshot` — depende de T012-T014, T023
- [X] T026 [US1] Tratar cancelamento/adiamento de partida (FR-018) em `src/collector/run.py`: quando um jogo já processado como realizado deixa de ser retornado como tal pela fonte, atualizar `status = 'cancelada'` sem excluir o registro — depende de T025
- [X] T027 [P] [US1] Criar `.github/workflows/collect.yml`: dois agendamentos cron (domingo à noite + segunda de manhã como salvaguarda, horários convertidos de Porto Alegre/UTC-3 para UTC — `research.md` #7), ambos chamando `python -m collector.run`, usando GitHub Actions Secrets para `SUPABASE_DB_HOST`/`_PORT`/`_NAME`/`_USER`/`_PASSWORD` (Princípio V)

**Checkpoint Camada 2 — validado em 2026-07-31**: 23 jogos reais da fase coletados
e persistidos no Supabase (via pooler — research.md #11), 659 linhas de
`player_game_stats`, 44 de `team_game_stats`, 2 snapshots de classificação
distintos (append-only confirmado). Segunda execução completa não duplicou
nenhuma linha (`tests/unit/storage/test_upserts.py` passando contra o banco
real). Um achado real de dados incompletos na súmula (campos de contagem
ausentes) foi tratado e documentado — ver research.md #12.

---

## Camada 3: Modelagem (Priority: P2)

**Goal**: Funções puras que leem os fatos já persistidos na Camada 2 e calculam
panorama, rankings, tendência, utilização e impacto — cada uma retornando também a
contagem de jogos que sustenta o valor (Princípio VII).

**Independent Test / Checkpoint desta camada**: Com os dados reais já no Supabase
(Camada 2), rodar cada função de modelagem manualmente (ex.: via REPL Python) contra
esses dados reais e conferir os números à mão contra o que se vê no site do
go-champs (classificação, pontuadores, etc.) — antes de construir qualquer página
de dashboard em cima.

- [X] T028 [US3] Implementar `src/modeling/sample_size.py`: `flag_low_confidence(valor, num_jogos, limiar=3)` (`research.md` #6) — reutilizado por US2, US4, US5 e US6
- [X] T029 [P] [US3] Teste unitário: métrica calculada com menos jogos que o limiar (default 3) é marcada como baixa confiança em `tests/unit/modeling/test_sample_size.py`
- [X] T030 [US2] Implementar `src/modeling/standings.py`: `season_overview(games)` (jogos realizados/restantes) e `current_standings(snapshot_rows)` — depende de T020
- [X] T031 [P] [US2] Teste unitário: contagem de jogos realizados/restantes a partir de linhas de `games` sintéticas em `tests/unit/modeling/test_season_overview.py`
- [X] T032 [P] [US2] Teste unitário: classificação atual reflete a linha mais recente de `standings_snapshot` por time em `tests/unit/modeling/test_standings.py`
- [X] T033 [US3] Implementar `src/modeling/leaderboards.py`: `rank_players(criterio, team_id=None)` usando `player_game_stats` + `sample_size` — depende de T021, T028
- [X] T034 [P] [US3] Teste unitário: ranking ordenado por um critério arbitrário retorna a ordem correta e a contagem de jogos por jogador em `tests/unit/modeling/test_leaderboards.py`
- [X] T035 [US4] Implementar `src/modeling/trends.py`: `player_trend(player_id, metrica)`, `team_trend(team_id, metrica)`, `standings_trend(team_id)` — cada ponto da série retorna também a contagem de jogos que o sustenta e aplica `modeling/sample_size.flag_low_confidence` (Princípio VII, FR-013) — depende de T022, T028
- [X] T036 [P] [US4] Teste unitário: série de tendência agrupada por rodada/data para uma métrica de jogador/time retorna também a contagem de jogos por ponto e aplica a marcação de baixa confiança em `tests/unit/modeling/test_trends.py`
- [X] T037 [P] [US4] Teste unitário: histórico de classificação retorna snapshots ordenados por `coletado_em` em `tests/unit/modeling/test_standings_history.py`
- [X] T038 [US5] Implementar `src/modeling/usage.py`: `usage_index(team_id)` per FR-011/`data-model.md` — depende de T021
- [X] T039 [P] [US5] Teste unitário: índice de utilização = (arremessos tentados + lances livres tentados + turnovers) / minutos jogados, com contagem de jogos, em `tests/unit/modeling/test_usage.py`
- [X] T040 [US6] Implementar `src/modeling/impact.py`: `impact_index(periodo)` — combinação normalizada por z-score, peso 50/50 (`research.md` #5) — depende de T021
- [X] T041 [P] [US6] Teste unitário: índice de impacto = z-score(eficiência) + z-score(plus/minus) com peso igual, com contagem de jogos, em `tests/unit/modeling/test_impact.py`

**Checkpoint Camada 3 — validado em 2026-07-31**: 23 testes unitários passando
(sample_size, standings, leaderboards, trends, usage, impact). Todas as funções
rodadas contra os dados reais da Camada 2 (23 jogos, 659 linhas de estatística):
panorama (22 realizados/1 restante), classificação (bate com o payload bruto já
inspecionado na Camada 1/2), ranking de pontuadores, utilização e impacto — todos
com contagem de jogos e marcação de baixa confiança funcionando (inclusive
sinalizando corretamente um outlier de poucos minutos jogados). Achado real:
colunas `numeric` do Postgres voltam como `Decimal`, corrigido na leitura
(research.md #13).

---

## Camada 4: Dashboard (Priority: P2/P3)

**Goal**: Streamlit lendo diretamente da camada de modelagem (nunca do banco
diretamente nem de detalhes do coletor), com Plotly para os gráficos.

**Independent Test / Checkpoint desta camada**: `streamlit run
src/dashboard/app.py` mostra, com os dados reais já coletados/modelados nas
camadas anteriores, todas as visões do critério de aceite do spec (classificação,
estatísticas de jogadores, tendências, impacto/utilização — todas com contagem de
jogos visível).

- [X] T042 [US2] Implementar `src/dashboard/app.py`: entrypoint Streamlit com navegação multipágina (shell compartilhado pelas demais páginas)
- [X] T043 [US2] Implementar `src/dashboard/pages/1_visao_geral.py`: exibe jogos realizados/restantes e a tabela de classificação atual, via `modeling/standings.py` — depende de T030, T042
- [X] T044 [US3] Implementar `src/dashboard/pages/2_estatisticas_jogadores.py`: filtro por time e critério, ranking com contagem de jogos e marca de baixa confiança — depende de T033
- [X] T045 [US4] Implementar `src/dashboard/pages/3_tendencias.py`: gráficos Plotly de séries temporais por jogador/time e evolução da classificação, sinalizando visualmente pontos calculados sobre baixa confiança (Princípio VII) — depende de T035
- [X] T046 [US5] Criar `src/dashboard/pages/4_impacto_e_utilizacao.py` com a seção de utilização (ranking por `usage_index`, por time, contagem de jogos visível) — depende de T038
- [X] T047 [US6] Estender `src/dashboard/pages/4_impacto_e_utilizacao.py` com a seção de impacto (ranking por `impact_index`, contagem de jogos visível) — depende de T040, T046

**Checkpoint Camada 4 — validado em 2026-07-31**: `streamlit run src/dashboard/app.py`
testado no navegador (navegação via `st.navigation` com títulos/ícones), com os
dados reais já coletados — panorama, classificação com tarja de líder, ranking de
estatísticas com filtro por time/critério, utilização e impacto com badge
"poucos jogos". Feature completa e navegável com dados reais.

> **Revisão pós-checkpoint (mesmo dia)**, depois de o usuário abrir o dashboard e
> apontar ajustes concretos vendo os dados reais: (1) página "Tendências" removida
> da UI (a funcionalidade de evolução rodada a rodada continua implementada e
> testada em `modeling/trends.py`, só não é mais exibida); (2) "Estatísticas de
> jogadores" ganhou ranking de times (total e média, ambos ranqueados) e a tabela
> de jogadores virou uma tabela completa com todas as métricas, ordenável clicando
> no cabeçalho (`st.dataframe` nativo), com alternância Total/Média; (3) "Impacto e
> utilização" foi refeita como top-5 por métrica escolhida (total ou média),
> substituindo os índices de Utilização (FR-011) e Impacto (FR-012) em destaque —
> as duas fórmulas continuam implementadas e testadas em `modeling/usage.py` e
> `modeling/impact.py`, só não ficam mais na tela principal. Novas funções:
> `modeling.leaderboards.team_metric_ranking`, `player_stats_table` — 8 novos
> testes unitários, todos passando (59/59 no total).
>
> **Segunda revisão (mesmo dia)**, pedindo métricas avançadas no estilo NBA
> analytics e uma revisão de duplicação: (4) tabela de jogadores ganhou TS%
> (True Shooting — pesa arremessos de 3 e lances livres) e AST/TO (razão
> assistência/turnover, `None` honesto quando não há turnover na amostra),
> ambos calculados a partir dos totais da temporada, nunca como média ingênua
> de percentuais por jogo; (5) "Impacto e utilização" trocou o "top 5 por
> métrica" — que duplicava a tabela ordenável de Estatísticas — por um
> scatterplot Eficiência × Utilização (estilo usage-vs-efficiency de análise
> avançada de basquete), com linhas de mediana marcando quadrantes, tamanho/cor
> do ponto refletindo confiança (Princípio VII), e um piso de minutos jogados
> (5min) para não deixar um outlier de segundos em quadra esmagar a escala do
> gráfico — achado real ao olhar o gráfico renderizado. `top_n_by_metric` foi
> removida (não tinha mais chamador). 62/62 testes passando.
>
> **Terceira revisão (mesmo dia)**, pedindo mais scatterplots com métricas
> estilo NBA analytics e uma página de glossário: (6) "Impacto e utilização"
> ganhou mais 3 gráficos — Eficiência × Plus/Minus (as duas metades do que se
> costuma chamar de "impacto"), TS% × Volume de arremessos (perfil de
> arremesso, eficiente vs. de alto volume) e Ataque × Defesa por time (pontos
> marcados vs. sofridos por jogo, eixo Y invertido); a lógica de scatterplot
> (mediana em quadrantes, tamanho/cor por confiança) foi extraída para
> `dashboard/theme.scatter_with_medians` para não duplicar em 4 gráficos;
> (7) nova página "Glossário" explicando cada métrica/gráfico do dashboard.
> Nova métrica: `modeling.leaderboards.player_stats_table` ganhou
> `tentativas_media` (volume de arremessos por jogo). 63/63 testes passando.
>
> **Quarta revisão (mesmo dia)**: usuário pediu cor do time em vez de cor por
> confiança nos 4 scatterplots, filtro de time com seleção múltipla (antes só
> 1 por vez), e a remoção completa de qualquer distinção visual/filtro por
> quantidade de jogos — o piso de 5 minutos introduzido na segunda revisão
> estava escondendo jogadores reais (2 do Jamallers com 1 jogo cada). `theme.
> scatter_with_medians` foi refeito para desenhar uma trace do Plotly por
> time (cor real + legenda nativa clicável) em vez de uma cor genérica; o
> número de jogos continua visível no hover de cada ponto (Princípio VII —
> a amostra continua exposta, só não filtra/destaca mais ninguém por ela).
>
> **Correção (mesmo dia)**: remover o piso de minutos reintroduziu o problema
> visual original — um outlier estatístico (poucos minutos) esmagando a
> escala dos outros pontos. Resolvido sem excluir ninguém: `theme.
> scatter_with_medians` agora aplica um zoom inicial pela regra clássica de
> outlier de boxplot (Q1/Q3 ± 1,5×IQR) em vez de deixar o Plotly auto-escalar
> pelo mínimo/máximo — o outlier continua nos dados e some só do enquadramento
> padrão; "reset axes" na barra do gráfico mostra tudo de novo. Ajuste também
> corrigiu o eixo Y invertido do gráfico Ataque×Defesa (`y_reversed=True`
> agora aplica o range explícito invertido, em vez de `autorange="reversed"`
> conflitar com a faixa calculada). 63/63 testes continuam passando.

---

## Phase Final: Polish & Cross-Cutting Concerns

- [ ] T048 [P] Escrever `README.md` com instruções de setup/execução referenciando os cenários de `quickstart.md`
- [ ] T049 [P] Configurar `pytest.ini` (ou marker) para excluir `tests/integration/` da execução padrão de `pytest` (só roda manualmente)
- [ ] T050 Rodar a validação completa de `quickstart.md` (Cenários 1-6) ponta a ponta e corrigir quaisquer lacunas encontradas
- [ ] T051 [P] Auditar as mensagens de log do coletor, confirmando que toda falha é explícita e não-silenciosa (Princípio II)

---

## Dependencies & Execution Order

### Ordem de camadas (sequencial, por pedido explícito do usuário)

1. **Setup** — sem dependências
2. **Camada 1 (Coleta)** — depende do Setup; **validável sozinha contra a API real, sem banco**
3. **Camada 2 (Armazenamento)** — depende da Camada 1 estar validada (client/config/parsers prontos); é aqui que o schema é confirmado contra dados reais
4. **Camada 3 (Modelagem)** — depende da Camada 2 ter dados reais persistidos
5. **Camada 4 (Dashboard)** — depende da Camada 3
6. **Polish** — depende de todas as camadas desejadas estarem completas

Diferente de uma organização por user story, aqui **nenhuma camada avança sem o
checkpoint de validação com dados reais da camada anterior** — essa é a
salvaguarda explícita pedida: confirmar que o schema modelado bate com a API real
antes de construir modelagem/dashboard em cima dele.

### Parallel Opportunities

- Setup: T002, T003
- Camada 1: T004-T010 (fixtures + contract tests) em paralelo entre si; T012, T013 (client, config) em paralelo
- Camada 2: T015, T016, T017, T019 em paralelo (T018 depende de T015-T017); T020-T022 são sequenciais (mesmo arquivo `reads.py`)
- Camada 3: T028, T030, T033, T035, T038, T040 podem ser feitos em paralelo entre si (arquivos diferentes) desde que suas dependências de `reads.py` (T020-T022) já existam; todos os testes unitários marcados `[P]` em paralelo
- Camada 4: T044, T045, T046 em paralelo (páginas diferentes); T047 depende de T046 (mesmo arquivo)

---

## Implementation Strategy

### Entrega sequencial por camada (não tudo de uma vez)

1. **Setup** → base pronta
2. **Camada 1 — Coleta**: implementar e validar contra a API real (sem banco). **Parar e confirmar** que os parsers batem com a resposta real antes de seguir.
3. **Camada 2 — Armazenamento**: criar schema, persistir uma rodada real, **parar e confirmar** que as tabelas batem com `data-model.md` e que rodar a coleta duas vezes não duplica nada.
4. **Camada 3 — Modelagem**: implementar as funções de análise sobre os dados reais já armazenados, **parar e confirmar** manualmente que os números fazem sentido.
5. **Camada 4 — Dashboard**: construir as páginas por cima da modelagem já validada.
6. **Polish**: documentação, config de testes, validação final ponta a ponta via `quickstart.md`.

Cada camada só começa depois que a anterior foi validada com dados reais — a
ordem de entrega é literalmente Coleta → Armazenamento → Modelagem → Dashboard,
como pedido.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência entre si
- `[Story]` mapeia a tarefa à user story correspondente em `spec.md` (rastreabilidade — não define a ordem de execução, que agora é por camada)
- Toda mudança em `src/collector/` que tocar tratamento de erro ou schema da fonte
  MUST vir com um teste de contrato correspondente (Fluxo de Desenvolvimento e
  Qualidade da constituição)
- Rodar `pytest tests/unit tests/contract` antes de cada commit; `tests/integration/`
  só roda manualmente
- Parar em cada um dos 4 checkpoints de camada para validar com dados reais antes de avançar

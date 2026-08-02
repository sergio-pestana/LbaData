---

description: "Task list for Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026"
---

# Tasks: Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026

**Input**: Design documents from `/specs/002-add-series-2025-2026/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tournament-registry.md, quickstart.md (todos presentes)

**Tests**: Incluídos — a constituição exige teste sempre que o tratamento de erros
ou o schema esperado da fonte mudar (Fluxo de Desenvolvimento e Qualidade), e esta
feature introduz um caso de schema novo e esperado (fase tipo `draw`/Playoffs sem
classificação) que precisa de teste de contrato dedicado.

**Organization**: Tarefas agrupadas por user story (spec.md), na ordem de
prioridade: Foundational (bloqueia todas) → US1 → US2 → US3 (as três P1) → US4
(P2) → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story esta tarefa pertence (US1..US4)
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Mesmo projeto Python único de 001: `src/collector/`, `src/storage/`,
`src/dashboard/`, `tests/`, `.github/workflows/`.

---

## Phase 1: Setup

- [X] T001 [P] Salvar fixture real do payload de `GET /v1/tournaments/9fa9ecef-c361-4d82-9fd5-ae8f3919b011` (Ouro 2025 — segundo torneio, usado para provar isolamento) em `tests/fixtures/tournament_ouro2025.json`
- [X] T002 [P] Salvar fixture real do payload de `GET /v1/phases/51de7c2b-0be8-4a50-bdee-0ed3f5bacd94` (fase Playoffs de Ouro 2025 — `type=draw`, `eliminations`/`elimination_stats` vazios, campo `draws`) em `tests/fixtures/phase_playoffs_bracket.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Objetivo**: registro de torneios + escopo de torneio no storage — pré-requisito
de toda user story desta feature.

- [X] T003 [P] Implementar `src/collector/tournaments.py`: dataclasses `Fase` (phase_id, nome, gera_classificacao) e `Torneio` (tournament_id, slug, nome, modo, fases), com a tupla `TORNEIOS` contendo os 5 torneios e 8 fases de `contracts/tournament-registry.md`
- [X] T004 [P] Teste unitário: todo `tournament_id`/`phase_id` em `TORNEIOS` é único, todo torneio tem pelo menos 1 fase, `modo` é sempre `"recorrente"` ou `"historico"`, em `tests/unit/collector/test_tournaments.py`
- [X] T005 Migration `src/storage/migrations/0004_tournament_scoping.sql`: `ALTER TABLE teams/players ADD COLUMN tournament_id uuid`, backfill das linhas existentes do Ouro 2026 (`tournament_id = '5bf23f0b-6768-46ec-bcc1-4cd698105413'`), depois `SET NOT NULL`, mais índices `idx_teams_tournament_id`/`idx_players_tournament_id` (data-model.md) — aplicada com sucesso contra o Supabase real
- [X] T006 Atualizar `src/storage/upserts.py`: `upsert_team(team, tournament_id)` e `upsert_player(player, tournament_id)` passam a gravar a coluna nova — depende de T005 (e `collector/run.py` atualizado para passar `tournament_id` nas chamadas existentes, senão a coleta recorrente já quebraria)
- [X] T007 [P] Teste unitário: `upsert_team`/`upsert_player` gravam e preservam `tournament_id` em updates subsequentes, em `tests/unit/storage/test_upserts.py` — depende de T006
- [X] T008 Atualizar `src/storage/reads.py`: `get_teams(tournament_id)` e `get_players(tournament_id)` passam a exigir o parâmetro (era opcional/inexistente) e filtrar `WHERE tournament_id = %s` — depende de T006
- [X] T009 [P] Teste unitário: com times/jogadores de dois `tournament_id` diferentes na base, `get_teams`/`get_players` só retornam os do torneio pedido, em `tests/unit/storage/test_reads.py` — depende de T008
- [X] T010 Estender `src/storage/reads.py`: `get_games(phase_ids: list[str])`, `get_player_game_stats(phase_ids: list[str], team_id=None)` e `get_team_game_stats(phase_ids: list[str], team_id=None)` — as duas últimas hoje não filtram por fase/torneio nenhum (research.md #3) e passam a fazer `JOIN games` filtrando `WHERE g.phase_id = ANY(%s::uuid[])` (cast explícito — psycopg2 manda lista Python como `text[]` por padrão, incompatível com a coluna `uuid`) — depende de T008
- [X] T011 [P] Teste unitário: com jogos/estatísticas de duas fases diferentes na base, `get_games`/`get_player_game_stats`/`get_team_game_stats` só retornam linhas cujo jogo pertence a um dos `phase_ids` informados, em `tests/unit/storage/test_reads.py` — depende de T010

**Checkpoint**: schema e leituras já isolam por torneio/fase; nenhuma user story abaixo depende de mais nada além disto.

---

## Phase 3: User Story 1 - Carga histórica das temporadas 2025 encerradas (Priority: P1) 🎯 MVP

**Goal**: coletar, de forma idempotente, todos os jogos/estatísticas de Ouro 2025, Prata 2025 e Bronze 2025 — incluindo a fase de Playoffs, sem exigir classificação pronta para ela.

**Independent Test**: rodar a carga de um torneio 2025 e conferir que ambas as fases (Classificação e Playoffs) têm jogos persistidos, que `standings_snapshot` só tem linhas da fase de Classificação, e que reexecutar não duplica nada (quickstart.md, passo 2).

### Tests

- [X] T012 [P] [US1] Teste de contrato: a fixture de fase `draw` (T002) — sem `eliminations`/`elimination_stats` — é reconhecida como "fase sem classificação" e o pipeline **não** chama o parser de standings para ela (em vez de chamá-lo e capturar `UnexpectedPayloadShape`), em `tests/contract/test_playoffs_phase_skipped.py` (via `FakeClient` que levanta erro se um path não esperado for chamado)
- [X] T013 [P] [US1] Teste unitário: reexecutar a carga histórica do mesmo torneio (mesmas fases) não duplica jogos nem estatísticas — idempotência (FR-009), em `tests/unit/collector/test_backfill.py`

### Implementation

- [X] T014 [US1] Estender `collect_round` em `src/collector/run.py` para receber `gera_classificacao: bool`; quando `False`, pula a etapa de buscar/parsear/gravar `standings_snapshot` para aquela fase, mas continua coletando jogos e estatísticas normalmente — depende de Foundational (T003-T011)
- [X] T015 [US1] Adicionar modo `--torneio <slug>` em `src/collector/run.py`: resolve o `Torneio` correspondente em `TORNEIOS` e chama `collect_round` para cada uma de suas fases, passando o `gera_classificacao` de cada uma — depende de T014
- [X] T016 [US1] Isolar falha por fase dentro de `--torneio <slug>`: uma fase falhando (ex.: mudança de schema) é logada explicitamente e não impede o processamento das demais fases do mesmo torneio — depende de T015

**Checkpoint**: validado contra a API real — `python -m collector.run --torneio
bronze2025` coletou 10 times, 220 jogadores, 45 jogos (Classificação) + 15
jogos (Playoffs), sem duplicar e sem que a falha real de classificação da
fase de Classificação (ver research.md #4b — critério 'overall' ausente
nessa fase específica, em aberto) impedisse a coleta dos jogos dela nem da
fase de Playoffs seguinte.

---

## Phase 4: User Story 2 - Coleta recorrente ampliada para Prata/Bronze 2026 (Priority: P1)

**Goal**: o cron existente passa a cobrir Ouro 2026 e Prata/Bronze 2026, com falha isolada por torneio.

**Independent Test**: rodar o modo recorrente localmente e confirmar que ambos os torneios ativos são processados numa única execução, e que a falha simulada de um não impede o outro (quickstart.md, passo 3).

### Tests

- [X] T017 [P] [US2] Teste unitário: modo `--modo recorrente` processa todos os torneios com `modo="recorrente"` do registro; uma falha simulada num torneio não impede o processamento do outro, em `tests/unit/collector/test_run_modes.py`

### Implementation

- [X] T018 [US2] Adicionar modo `--modo recorrente` em `src/collector/run.py`: itera todos os `Torneio` com `modo="recorrente"` em `TORNEIOS`, processando cada fase de cada um via o mesmo caminho de T015, capturando e logando falha por torneio sem interromper os demais (FR-008) — depende de T015 (implementado junto com T015/T016, ver commit anterior)
- [X] T019 [US2] Atualizar `.github/workflows/collect.yml`: o passo de coleta passa a chamar `python -m collector.run --modo recorrente` em vez dos `LBA_TOURNAMENT_ID`/`LBA_PHASE_ID` fixos de um único torneio — depende de T018

**Checkpoint**: o cron agendado cobre os dois torneios ativos numa única execução.

---

## Phase 5: User Story 3 - Selecionar temporada/série no dashboard (Priority: P1)

**Goal**: seletor de torneio no dashboard, propagado para as três páginas existentes.

**Independent Test**: selecionar cada um dos 5 torneios no dashboard e confirmar que classificação, estatísticas de jogadores e gráficos de impacto/utilização mostram só dados daquele torneio (quickstart.md, passo 4).

- [ ] T020 [US3] Implementar seletor de torneio em `src/dashboard/theme.py`: `st.selectbox` sobre `collector.tournaments.TORNEIOS`, guardando a seleção em `st.session_state`; expõe uma função que resolve o torneio selecionado para `tournament_id`, `phase_ids` (todas as fases) e `phase_id_classificacao` (a fase com `gera_classificacao=True`) — depende de Foundational (T003-T011)
- [ ] T021 [US3] Atualizar `src/dashboard/pages/1_visao_geral.py`: usa `phase_ids` do torneio selecionado para `get_games`, e `phase_id_classificacao` para `get_latest_standings_snapshot`/`get_teams` — depende de T020, T010
- [ ] T022 [US3] Atualizar `src/dashboard/pages/2_estatisticas_jogadores.py`: `get_teams`, `get_players`, `get_team_game_stats`, `get_player_game_stats` passam `tournament_id`/`phase_ids` do torneio selecionado — depende de T020, T008, T010
- [ ] T023 [US3] Atualizar `src/dashboard/pages/3_impacto_e_utilizacao.py`: mesma mudança de T022 — depende de T020, T008, T010
- [ ] T024 [P] [US3] Teste unitário: o resolvedor de torneio selecionado (T020) retorna `phase_ids`/`phase_id_classificacao` corretos para cada um dos 5 torneios do registro, em `tests/unit/dashboard/test_theme_torneio.py`

**Checkpoint**: trocar de torneio no dashboard troca todos os dados nas 3 páginas.

---

## Phase 6: User Story 4 - Isolamento de times e jogadores entre torneios (Priority: P2)

**Goal**: confirmar, com um cenário concreto (mesmo time/atleta em dois torneios), que nada se mistura — validação cross-cutting das garantias já construídas no Foundational.

**Independent Test**: com fixtures de dois torneios contendo um time com o mesmo nome (ids e `tournament_id` diferentes), confirmar que as estatísticas de cada torneio permanecem completamente separadas.

- [ ] T025 [P] [US4] Teste de integração (unit, com fixtures sintéticas): dois torneios com um time/jogador de mesmo nome mas `id`/`tournament_id` diferentes — `get_teams`/`get_players`/`get_player_game_stats`/`get_team_game_stats` de um torneio nunca incluem linhas do outro, em `tests/unit/storage/test_multi_tournament_isolation.py`

**Checkpoint**: garantia estrutural de US4 comprovada por teste, não apenas por inspeção manual.

---

## Phase Final: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Atualizar `README.md` documentando os modos `--torneio <slug>` e `--modo recorrente` de `collector.run`
- [ ] T027 [P] Rodar `quickstart.md` (passos 1-5) ponta a ponta e corrigir qualquer lacuna encontrada
- [ ] T028 [P] Auditar logs do coletor multi-torneio: confirmar que toda falha por fase/torneio identifica explicitamente qual torneio/fase falhou (Princípio II)
- [ ] T029 Executar a carga histórica real dos 3 torneios 2025 (6 execuções de fase) contra o Supabase e confirmar SC-001/SC-002 do spec.md

---

## Dependencies & Execution Order

### Ordem de fases

1. **Setup (T001-T002)** — sem dependências.
2. **Foundational (T003-T011)** — depende de Setup (fixtures usadas nos testes T004/T007/T009/T011); bloqueia todas as user stories.
3. **US1 (T012-T016)** — depende de Foundational. Entrega o MVP: dados históricos de 2025 já corretos e consultáveis via SQL/quickstart, mesmo antes do dashboard ter seletor.
4. **US2 (T017-T019)** — depende de Foundational e reusa o mecanismo de iteração por fase introduzido em T015 (US1); pode começar em paralelo com US1 se T015 for entregue primeiro, mas está listada depois por prioridade de spec.md.
5. **US3 (T020-T024)** — depende de Foundational (T008, T010); independente de US1/US2 em termos de código (só precisa que existam dados de *algum* torneio para ser testada de ponta a ponta).
6. **US4 (T025)** — depende de Foundational; é validação, não implementação nova.
7. **Polish (T026-T029)** — depende de todas as anteriores.

### Parallel Opportunities

- T001/T002 (Setup) em paralelo.
- T003/T004 (registro + seu teste) em paralelo com T001/T002 (não dependem das fixtures).
- Dentro do Foundational: T007 e T009 podem rodar em paralelo entre si depois de T006/T008 respectivamente; T011 depois de T010.
- T021/T022/T023 (as 3 páginas do dashboard) são paralelizáveis entre si — cada uma é um arquivo diferente — desde que T020 já esteja pronto.

## Implementation Strategy

### MVP primeiro

Foundational + US1 já entregam valor de ponta a ponta: as três temporadas 2025
carregadas, corretas e isoladas por torneio (verificável por SQL/quickstart),
mesmo sem o seletor do dashboard (US3) ainda existir. US2 (cron ampliado) e US3
(seletor) podem ser entregues em qualquer ordem depois do Foundational — nenhuma
depende da outra no código, só ambas dependem do Foundational.

### Entrega incremental

Foundational → US1 (valida com dados reais de 2025) → US2 (valida com o cron
rodando manualmente uma vez) → US3 (valida no navegador) → US4 (prova formal do
isolamento) → Polish.

## Notes

- `[P]` tasks = arquivos diferentes, sem dependência entre si.
- Cada task deixa o repositório num estado que roda (`pytest` verde) antes de
  passar para a próxima.
- Commitar ao final de cada task concluída (preferência do usuário para esta
  feature — ver histórico da conversa), não só ao final de cada fase.

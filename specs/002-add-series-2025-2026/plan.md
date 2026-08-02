# Implementation Plan: Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026

**Branch**: `002-add-series-2025-2026` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-add-series-2025-2026/spec.md`

## Summary

Estender a plataforma de torneio único (001, Ouro 2026) para suportar 5 torneios
simultâneos: Ouro 2026 e Prata/Bronze 2026 (em andamento, coleta recorrente
existente) mais Ouro 2025, Prata 2025 e Bronze 2025 (temporadas encerradas, carga
histórica única). A mudança central é introduzir um registro estático de torneios
(`collector/tournaments.py`) que substitui a configuração de "um `tournament_id`/
`phase_id` fixo" por uma lista de torneios, cada um com uma ou mais fases — as
três séries de 2025 têm fase de Classificação (gera tabela) e Playoffs (sem
tabela, apenas jogos). No armazenamento, `teams`/`players` ganham uma coluna
`tournament_id` (hoje ausentes de qualquer escopo — vinham embutidos no payload de
`/v1/tournaments/{id}`, um torneio por vez, então nunca precisaram de escopo
explícito). `games`/`player_game_stats`/`team_game_stats`/`standings_snapshot` já
são escopados por `phase_id`; não precisam de migração — a camada de leitura passa
a aceitar uma lista de `phase_id`s (resolvida a partir do registro) para agregar as
fases de um torneio. O dashboard ganha um seletor de torneio que decide qual
`tournament_id`/lista de `phase_id`s alimenta todas as três páginas existentes.

## Technical Context

**Language/Version**: Python 3.11+ (sem mudança em relação a 001)

**Primary Dependencies**: as mesmas de 001 (`requests`, `psycopg2-binary`,
`streamlit`, `plotly`, `pandas`, `python-dotenv`, `pytest`) — nenhuma dependência
nova. O registro de torneios é um módulo Python estático (dataclasses), não um
arquivo YAML/JSON externo, para não introduzir um parser novo por 5 registros
fixos (Princípio VI).

**Storage**: Supabase (Postgres gerenciado) — mesma instância; uma migration nova
(`0004_tournament_scoping.sql`) adiciona `tournament_id` a `teams`/`players`.

**Testing**: `pytest`, mesmo padrão de 001 (fixtures de payload real, sem rede em
CI); novas fixtures para o payload de uma fase tipo "Playoffs" (`eliminations`
vazio, campo `draws`) e para o payload de `/v1/tournaments/{id}` de um segundo
torneio, usadas para provar que dois torneios não se misturam.

**Target Platform**: mesmo de 001 (GitHub Actions para coleta recorrente; local
para coleta histórica manual e para o dashboard).

**Project Type**: mesma estrutura de 4 pacotes desacoplados de 001 — nenhum pacote
novo, apenas extensões pontuais dentro de `collector/`, `storage/` e `dashboard/`.

**Performance Goals**: inalterado — volume ainda é o de uma liga amadora (agora 5
torneios em vez de 1, mas cada um do mesmo porte pequeno já dimensionado em 001).

**Constraints**: mesmas de 001 (coleta sequencial, intervalo mínimo entre
requisições, credenciais via env/Secrets) + a nova restrição de que a carga
histórica das séries 2025 MUST ser idempotente e reexecutável (FR-009), e que uma
falha de coleta em um torneio MUST NOT impedir a coleta dos demais (FR-008).

**Scale/Scope**: 5 torneios, 8 fases no total (2 recorrentes de 1 fase cada + 3
históricos de 2 fases cada); mesma ordem de grandeza de linhas por torneio que
001, agora multiplicada por 5.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Integridade dos Dados (Idempotência) | **PASS** — a carga histórica (FR-009) usa o mesmo `collect_round`/upsert por id externo já existente; nenhum novo caminho de escrita "cega" é introduzido. Reexecutar a carga de um torneio 2025 corrige, nunca duplica. |
| II. Resiliência a Mudanças na Fonte e Coleta Responsável | **PASS** — mesmo cliente HTTP e mesma validação defensiva de 001; a fase de Playoffs (estrutura `draws`, sem `eliminations`) é tratada como uma variação **esperada e documentada** do contrato (não como uma falha a ser silenciada) — o registro de torneios marca explicitamente quais fases geram classificação, e o coletor pula a etapa de standings para as que não geram, sem tentar "adivinhar" ou mascarar o formato ausente. |
| III. Separação de Responsabilidades entre Camadas | **PASS** — o registro de torneios vive em `collector/`, mas é consumido também por `dashboard/` como puro dado de configuração (lista de ids/nomes), nunca como acesso a estrutura interna do coletor; a camada de armazenamento continua exposta só via `storage/reads.py`/`storage/upserts.py`. |
| IV. Preservação de Histórico | **PASS** — nenhuma tabela de fato é alterada de forma destrutiva; `tournament_id` é uma coluna adicionada (aditiva) a `teams`/`players`, preenchida por migração para os dados já existentes do Ouro 2026, sem apagar nem sobrescrever histórico. |
| V. Segurança de Credenciais | **PASS** — nenhuma credencial nova; os ids de torneio/fase são públicos (aparecem na URL do go-champs), não são segredo. |
| VI. Simplicidade Pragmática | **PASS** — registro de torneios é um módulo Python estático, não um sistema de configuração dinâmico; carga histórica reusa o `collector.run` existente via CLI, sem um "modo backfill" com código próprio separado. |
| VII. Rigor Estatístico em Métricas Derivadas | **PASS** — inalterado; as funções de `modeling/` continuam retornando contagem de jogos junto ao valor, agora computadas sobre o conjunto de jogos do torneio selecionado (que pode abranger mais de uma fase). |

Nenhuma violação — Complexity Tracking permanece vazio.

**Re-check pós Phase 1**: `data-model.md` confirma que a única migração de schema é
aditiva (`tournament_id` em `teams`/`players`); `games`/`player_game_stats`/
`team_game_stats`/`standings_snapshot` não mudam de schema, só a camada de leitura
passa a aceitar lista de `phase_id`s. Nenhum princípio é violado pelo desenho final.

## Project Structure

### Documentation (this feature)

```text
specs/002-add-series-2025-2026/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── tournament-registry.md   # ids reais de cada torneio/fase + o que cada fase produz
└── tasks.md              # Phase 2 output (/speckit-tasks — não criado por este comando)
```

### Source Code (repository root)

```text
src/
├── collector/
│   ├── tournaments.py     # NOVO — registro estático: Torneio (id, slug, nome, modo,
│   │                       # fases) e Fase (phase_id, nome, gera_classificacao)
│   ├── config.py            # ajustado — CollectorConfig ganha modo de operação
│   │                          # (--modo recorrente / --torneio <slug> / override manual
│   │                          # --tournament-id/--phase-id, este último inalterado)
│   ├── run.py                # ajustado — collect_round() ganha param gera_classificacao;
│   │                          # pula standings quando False; loop novo para processar
│   │                          # todas as fases de um torneio ou todos os torneios de um modo
│   ├── client.py              # inalterado
│   └── parsers.py              # inalterado (parse_phase_standings já falha explícito se
│                                  # eliminations vier vazio — chamado só quando aplicável)
│
├── storage/
│   ├── migrations/
│   │   └── 0004_tournament_scoping.sql   # NOVO — tournament_id em teams/players +
│   │                                       # backfill do Ouro 2026 já coletado + índices
│   ├── upserts.py             # ajustado — upsert_team/upsert_player recebem tournament_id
│   └── reads.py                 # ajustado — get_teams(tournament_id)/get_players(tournament_id)
│                                   # passam a exigir tournament_id; get_games/
│                                   # get_player_game_stats/get_team_game_stats passam a
│                                   # aceitar phase_ids: list[str] (via join com games onde
│                                   # ainda não existia o join, no caso das duas últimas)
│
└── dashboard/
    ├── theme.py               # ajustado — seletor de torneio substitui get_phase_id()
    │                           # fixo por env; expõe o Torneio selecionado (tournament_id +
    │                           # phase_ids + phase_id de classificação) via st.session_state
    └── pages/
        ├── 1_visao_geral.py         # ajustado — usa phase_ids agregados do torneio
        │                              # selecionado para jogos; phase_id só de Classificação
        │                              # para a tabela de classificação
        ├── 2_estatisticas_jogadores.py  # ajustado — get_teams/get_players/get_*_game_stats
        │                                  # passam tournament_id/phase_ids do torneio selecionado
        └── 3_impacto_e_utilizacao.py    # idem

tests/
├── fixtures/
│   ├── phase_playoffs_bracket.json   # NOVO — payload real de fase tipo draw/bracket
│   └── tournament_ouro2025.json        # NOVO — segundo torneio, para provar isolamento
├── unit/
│   ├── collector/    # teste novo: registro de torneios (ids únicos, modos válidos)
│   ├── storage/      # teste novo: upsert_team/upsert_player com tournament_id;
│   │                  # get_teams/get_players isolam por tournament_id
│   └── modeling/     # inalterado (já agnóstico a torneio — recebe stats já filtradas)
└── contract/           # teste novo: parse_phase_standings levantando erro esperado
                          # quando chamado sseria incorreto vs. quando é pulado de propósito

.github/
└── workflows/
    └── collect.yml     # ajustado — passo de coleta recorrente vira matrix sobre os
                          # torneios com modo="recorrente" do registro (hoje: Ouro 2026 e
                          # Prata/Bronze 2026); carga histórica das séries 2025 NÃO entra
                          # neste workflow — é uma execução manual local (FR-003, Assumptions)
```

**Structure Decision**: Mesma estrutura de 4 pacotes de 001, sem pacote novo. A
única tabela nova de configuração é um módulo Python (`collector/tournaments.py`),
não um pacote — decisão deliberada para manter a complexidade proporcional a 5
registros fixos (Princípio VI), evitando um sistema de configuração dinâmico que
esta escala não justifica.

## Complexity Tracking

*Sem violações da Constitution Check — tabela não aplicável nesta versão.*

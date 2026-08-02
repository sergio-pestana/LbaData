# Data Model: Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026

Este documento cobre apenas o que muda em relação a
[001/data-model.md](../001-lba-poa-analytics/data-model.md). Tabelas não
mencionadas aqui (`games`, `player_game_stats`, `team_game_stats`,
`standings_snapshot`) mantêm o schema exatamente como descrito em 001 — só a
camada de leitura (`storage/reads.py`) muda, para aceitar lista de `phase_id`s
(ver research.md #3).

## teams (dimensão) — coluna nova

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | inalterado — id externo do go-champs, chave de conflito |
| **`tournament_id`** | **uuid, NOT NULL** | **NOVO** — id externo do torneio ao qual este time pertence; times do mesmo clube em temporadas diferentes são linhas distintas, cada uma com seu próprio `id` e `tournament_id` (research.md #2) |
| `nome`, `tri_code`, `cor`, `criado_em`, `atualizado_em` | — | inalterados |

Índice novo: `idx_teams_tournament_id` em `tournament_id`.

## players (dimensão) — coluna nova

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | inalterado |
| **`tournament_id`** | **uuid, NOT NULL** | **NOVO** — mesmo racional de `teams` |
| `nome`, `team_id`, `numero_camisa`, `criado_em`, `atualizado_em` | — | inalterados |

Índice novo: `idx_players_tournament_id` em `tournament_id`.

**Migração (`0004_tournament_scoping.sql`)**: como `teams`/`players` já têm linhas
do Ouro 2026 coletadas em 001, a migração faz `ADD COLUMN tournament_id uuid`
(nullable), `UPDATE ... SET tournament_id = '5bf23f0b-6768-46ec-bcc1-4cd698105413'
WHERE tournament_id IS NULL` (backfill do único torneio já existente), depois `ALTER
COLUMN tournament_id SET NOT NULL` — aditiva e sem perda de dado (Princípio IV).

## Entidades de configuração (não são tabelas — vivem em `collector/tournaments.py`)

### Torneio

Representa uma série/temporada da LBA (Key Entity já prevista em spec.md).

| Campo | Tipo | Notas |
|---|---|---|
| `tournament_id` | str (uuid) | id externo do go-champs |
| `slug` | str | slug do go-champs (ex.: `ouro2025`), usado como identificador legível em CLI/UI |
| `nome` | str | nome de exibição (ex.: "Ouro 2025") |
| `modo` | `"recorrente"` \| `"historico"` | decide se entra no cron (`collect.yml`) ou é coletado manualmente uma vez (research.md #5) |
| `fases` | tupla de `Fase` | 1 fase para os torneios 2026 atuais; 2 fases (Classificação + Playoffs) para os três de 2025 |

### Fase

| Campo | Tipo | Notas |
|---|---|---|
| `phase_id` | str (uuid) | id externo da fase |
| `nome` | str | ex.: "Classificação", "Playoffs", "Temporada Regular" |
| `gera_classificacao` | bool | `False` para fases tipo chaveamento/bracket sem `eliminations` (research.md #4) — o coletor pula standings para essas |

**Registro completo com os 5 torneios e ids reais**: ver
[`contracts/tournament-registry.md`](./contracts/tournament-registry.md).

## Leituras afetadas (`storage/reads.py`)

- `get_teams(tournament_id: str)` — antes `get_teams()` sem parâmetro; agora
  **exige** `tournament_id`, filtra `WHERE tournament_id = %s`.
- `get_players(tournament_id: str)` — mesma mudança de `get_players()`.
- `get_games(phase_ids: list[str])` — antes `get_games(phase_id: str)`; agora
  aceita lista, `WHERE phase_id = ANY(%s)`, para agregar jogos de todas as fases
  de um torneio (ex.: Classificação + Playoffs de Ouro 2025).
- `get_player_game_stats(phase_ids: list[str], team_id: str | None = None)` —
  antes não filtrava por fase/torneio nenhum (achado em research.md #3); agora faz
  `JOIN games` e filtra `WHERE g.phase_id = ANY(%s)`, mantendo o filtro opcional de
  `team_id`.
- `get_team_game_stats(phase_ids: list[str], team_id: str | None = None)` — mesma
  mudança de `get_player_game_stats`.
- `get_latest_standings_snapshot(phase_id: str)` — **sem mudança de assinatura**:
  continua recebendo uma única fase, porque só a fase com `gera_classificacao=True`
  de um torneio produz snapshot; o dashboard resolve qual `phase_id` passar a
  partir do `Torneio` selecionado (a fase de Classificação, nunca a de Playoffs).
- `get_standings_history(phase_id: str, ...)` — mesma lógica de
  `get_latest_standings_snapshot`, sem mudança de assinatura.

## Regra de isolamento entre torneios (User Story 4)

Nenhuma consulta de leitura MUST retornar linhas de mais de um torneio numa mesma
chamada — `tournament_id`/`phase_ids` são sempre parâmetros obrigatórios (não mais
opcionais como `get_teams()`/`get_players()` eram em 001), para que seja
estruturalmente impossível esquecer o filtro ao adicionar uma nova página ou
gráfico ao dashboard.

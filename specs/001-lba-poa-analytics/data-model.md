# Data Model: Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026

Esquema dimensional simples: dimensões (`teams`, `players`) + fatos por partida
(`games`, `player_game_stats`, `team_game_stats`) + histórico de classificação
(`standings_snapshot`). Nenhuma tabela agregada de temporada é mantida — totais da
temporada são calculados sob demanda a partir de `player_game_stats`
(ver [research.md](./research.md) #1 e Princípio VI da constituição).

Toda tabela de fato/dimensão carrega o id externo do go-champs como chave natural
única, usada como chave de conflito em todo upsert (Princípio I).

**Nota sobre "Rodada"**: a Key Entity "Rodada" do spec.md é um conceito lógico
(agrupamento de `games.rodada_data` por fim de semana), não uma tabela própria.
A incrementalidade da coleta (FR-003) é garantida no nível de cada jogo
individual via upsert por id externo — não por um registro explícito de
"rodadas já processadas". Uma tabela `rodadas` adicionaria uma segunda fonte de
verdade sobre o mesmo dado sem necessidade real, o que contrariaria o Princípio
VI (Simplicidade Pragmática).

## teams (dimensão)

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | id externo do go-champs (`team_id`) — chave de conflito |
| `nome` | text | |
| `tri_code` | text | sigla de 3 letras usada pela fonte |
| `cor` | text | cor associada ao time na fonte |
| `criado_em` | timestamptz | preenchido no primeiro upsert |
| `atualizado_em` | timestamptz | atualizado a cada upsert |

## players (dimensão)

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | id externo do go-champs (`player_id`) — chave de conflito, estável por atleta |
| `nome` | text | |
| `team_id` (FK → teams.id) | uuid | time atual do jogador conforme última coleta |
| `numero_camisa` | text | |
| `criado_em` / `atualizado_em` | timestamptz | |

**Regra de identidade**: `player_id` do go-champs é estável por atleta (confirmado
pelo usuário), então uma troca de time no meio da temporada apenas atualiza
`team_id` no upsert — as linhas de `player_game_stats` já gravadas continuam
associadas ao `team_id` de cada partida específica via seu próprio campo
`time_id_na_partida` (ver abaixo), não são reatribuídas retroativamente (Assumption
do spec).

## games (fato — uma linha por partida)

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | id externo do go-champs (`game_id`) — chave de conflito |
| `phase_id` | uuid | id da fase (Ouro 2026) |
| `rodada_data` | date | data do jogo, conforme a fonte |
| `time_casa_id` (FK → teams.id) | uuid | |
| `time_visitante_id` (FK → teams.id) | uuid | |
| `placar_casa` | integer, nullable | null-safe até status confirmar jogo finalizado |
| `placar_visitante` | integer, nullable | idem |
| `status` | text (enum: `processada`, `cancelada`) | ver FR-018 — cancelamento é soft-status, nunca delete |
| `is_finished_raw` | boolean, nullable | valor bruto da fonte, guardado para auditoria enquanto o campo não é validado contra um exemplo `false` real (ver research.md #4) |
| `criado_em` | timestamptz | quando processado pela primeira vez |
| `corrigido_em` | timestamptz, nullable | atualizado sempre que uma coleta subsequente muda algum campo desta partida (Princípio I / FR-005) |

**Regra de correção (FR-004/FR-005)**: se uma coleta subsequente encontrar valores
diferentes para uma `game.id` já existente (placar, status), o `UPDATE` do upsert
grava os novos valores e atualiza `corrigido_em`; `criado_em` nunca muda.

**Regra de cancelamento (FR-018)**: se a fonte deixar de listar um jogo antes
`processado` como realizado dentro da fase/rodada esperada, ou sinalizar
cancelamento explicitamente, o registro é atualizado para `status = 'cancelada'`
— nunca excluído (Princípio IV).

## player_game_stats (fato — uma linha por jogador por partida)

Origem: `/v1/player-stats-logs?where[game_id]={game_id}`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | id externo do go-champs (`player_stats_log_id`) — chave de conflito |
| `game_id` (FK → games.id) | uuid | |
| `player_id` (FK → players.id) | uuid | |
| `time_id_na_partida` (FK → teams.id) | uuid | time do jogador **naquela partida específica** — não confundir com `players.team_id` (atual) |
| `jogou` | boolean | de `game_played`; `false` = esteve no elenco mas não jogou |
| `minutos_jogados` | numeric, nullable | normalizado para minutos decimais (ver research.md #4); null se `jogou = false` |
| `pontos` | integer | |
| `rebotes_ofensivos` / `rebotes_defensivos` | integer | |
| `assistencias` | integer | |
| `roubos` | integer | |
| `tocos` | integer | |
| `faltas_*` | integer | uma coluna por tipo de falta disponível na súmula |
| `arremessos_2pt_tentados` / `_convertidos` | integer | |
| `arremessos_3pt_tentados` / `_convertidos` | integer | |
| `lances_livres_tentados` / `_convertidos` | integer | |
| `turnovers` | integer | |
| `eficiencia` | numeric | já calculada pela fonte |
| `plus_minus` | numeric | já calculado pela fonte |
| `criado_em` / `corrigido_em` | timestamptz | mesma regra de correção de `games` |

## team_game_stats (fato — uma linha por time por partida)

Origem: `/v1/team-stats-logs?where[game_id]={game_id}`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid | id externo do go-champs — chave de conflito |
| `game_id` (FK → games.id) | uuid | |
| `team_id` (FK → teams.id) | uuid | |
| `vitoria` | boolean | |
| `saldo_pontos` | integer | |
| `fiba_group_points` | numeric, nullable | conforme disponibilidade na fonte |
| (demais totais agregados do time disponíveis na súmula) | | mapeados 1:1 conforme catálogo real do endpoint |
| `criado_em` / `corrigido_em` | timestamptz | mesma regra de correção |

## standings_snapshot (histórico — uma linha por time por coleta)

Origem: `/v1/phases/{phase_id}` (classificação já computada e ordenada pela fonte,
com desempates oficiais aplicados — Assumption do spec). **A extração exige
tradução de chaves opacas (`elimination_stats[i].id` → `team_stat_source`) — ver
`research.md` #9 e `contracts/go-champs-api-dependency.md` para a estrutura real
confirmada contra payload.**

| Campo | Tipo | Notas |
|---|---|---|
| `id` (PK) | uuid/serial | gerado internamente |
| `coletado_em` | timestamptz | timestamp da execução de coleta que gerou esta linha |
| `phase_id` | uuid | |
| `team_id` (FK → teams.id) | uuid | |
| `posicao` | integer | conforme ordenação da fonte |
| `jogos` | integer | |
| `vitorias` / `derrotas` | integer | |
| `saldo_pontos` | integer | |
| `pontos_fiba` | numeric | |

**Sem chave de conflito de upsert**: esta tabela é **append-only** por design — cada
execução de coleta grava uma linha nova por time, nunca atualiza uma linha
anterior. É essa tabela que permite reconstruir a evolução da classificação ao
longo da temporada (Princípio IV / User Story 4), o que uma tabela apenas com "o
estado atual" não permitiria.

## Métricas derivadas (calculadas pela camada de modelagem, não armazenadas)

Estas não são tabelas — são funções puras em `src/modeling/` que leem os fatos
acima e retornam valor + contagem de jogos (Princípio VII):

- **Totais/médias de temporada por jogador**: soma/média de `player_game_stats`
  filtrado por `player_id` (substitui a necessidade de espelhar
  `aggregated-player-stats-by-tournament` — ver research.md #1 e spec).
- **Índice de utilização** (`modeling/usage.py`): `(arremessos_2pt_tentados +
  arremessos_3pt_tentados + lances_livres_tentados + turnovers) /
  minutos_jogados`, por jogador, agregado no período selecionado.
- **Índice de impacto** (`modeling/impact.py`): z-score de `eficiencia` + z-score de
  `plus_minus`, peso igual (ver research.md #5).
- **Tendência** (`modeling/trends.py`): série de qualquer métrica de
  `player_game_stats`/`team_game_stats` agrupada por rodada/data do jogo.
- **Classificação histórica** (`modeling/standings.py`): leitura direta de
  `standings_snapshot` ordenada por `coletado_em`.
- **Baixa confiança** (`modeling/sample_size.py`): sinaliza quando a contagem de
  jogos por trás de qualquer métrica acima está abaixo do limiar configurado
  (default 3 — ver research.md #6).

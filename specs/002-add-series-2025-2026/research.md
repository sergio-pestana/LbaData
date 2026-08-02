# Research: Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026

## 1. Prata/Bronze 2026 é uma série combinada, diferente de 2025 — RESOLVIDO

**Decision**: Tratar "LBA 2026 - Série Prata/Bronze" (slug `bronze2026`,
`tournament_id=4cc1dacb-2619-48b8-8331-caa7103eefab`) como um único torneio na
modelagem — não duas séries separadas como em 2025 (`prata2025`/`bronze2025`, dois
torneios distintos).

**Rationale**: Confirmado com o mantenedor (2026-08-02): a liga de fato fundiu
Prata e Bronze em uma série só a partir de 2026. Modelar como um torneio combinado
evita inventar uma divisão que a própria fonte não expõe.

**Alternatives considered**: Assumir que faltava um torneio na listagem e
investigar mais a API — descartado após confirmação direta do mantenedor.

## 2. Teams/players não têm escopo de torneio hoje — por quê, e como resolver

**Decision**: Adicionar coluna `tournament_id` (uuid, NOT NULL) a `teams` e
`players`, mantendo `id` como chave primária única (sem chave composta).

**Rationale**: `parse_teams`/`parse_players` (`collector/parsers.py:96-127`) leem
`data.teams`/`data.players` de dentro do payload de **um único endpoint**,
`GET /v1/tournaments/{tournament_id}` — não existe um endpoint `/teams` ou
`/players` compartilhado entre torneios. Isso confirma que cada torneio carrega sua
própria lista de times/jogadores embutida no próprio documento do torneio; não há
evidência (nem motivo estrutural) para `id`s colidirem entre torneios diferentes,
já que são sub-objetos de documentos distintos na fonte. Logo, o problema real não
é risco de colisão de chave primária — é que `storage/reads.py:79-88`
(`get_teams()`/`get_players()`) faz `SELECT * FROM teams`/`players` sem nenhum
`WHERE`, retornando literalmente todas as linhas da tabela independente de
torneio. Com 5 torneios simultâneos, isso mistura times/jogadores de temporadas e
séries diferentes na mesma resposta. Uma coluna `tournament_id` filtrável resolve
isso sem exigir mudança de chave primária.

**Achado de implementação (2026-08-02)**: `psycopg2` manda uma `list[str]`
Python como um array `text[]` por padrão; `phase_id = ANY(%s)` contra uma
coluna `uuid` falha com `UndefinedFunction: operator does not exist: uuid =
text`. Corrigido com cast explícito `phase_id = ANY(%s::uuid[])` em
`storage/reads.py` — confirmado contra o Supabase real via
`tests/unit/storage/test_reads.py`.

**Alternatives considered**: Chave primária composta `(id, tournament_id)` —
rejeitada por não haver evidência de colisão de id entre torneios (ver acima) e por
adicionar complexidade (FKs compostas em `players.team_id`, `player_game_stats`,
etc.) sem benefício demonstrado, contrariando o Princípio VI.

## 3. `games`/`player_game_stats`/`team_game_stats`/`standings_snapshot` não precisam de migração

**Decision**: Não alterar o schema dessas quatro tabelas. `games` e
`standings_snapshot` já são escopadas por `phase_id`; a camada de leitura passa a
aceitar uma **lista** de `phase_id`s (resolvida a partir do registro de torneios em
`collector/tournaments.py`) para agregar as fases de um torneio, em vez de mudar o
schema para incluir `tournament_id` redundantemente.

**Rationale**: Um torneio pode ter mais de uma fase (ver item 4) — a granularidade
correta para "todos os jogos de um torneio" já existe (`phase_id`), só falta a
camada de leitura suportar mais de um valor por consulta. Introduzir uma coluna
`tournament_id` redundante nessas tabelas (quando `phase_id` já implica o torneio,
via o registro estático) duplicaria a mesma informação em dois lugares — o
oportunidade de inconsistência que o Princípio VI pede para evitar.

**Achado colateral, não bloqueante para esta decisão, mas relevante para a
implementação**: `get_player_game_stats()`/`get_team_game_stats()`
(`storage/reads.py:70-97`) hoje **não filtram por fase nem por jogo** quando
chamadas sem `team_id` — retornam a tabela inteira. Isso já seria um problema de
isolamento entre torneios mesmo que `teams`/`players` ganhassem escopo, e precisa
ser corrigido como parte desta feature (ver `data-model.md` e `plan.md` — join com
`games` para filtrar por `phase_id`s do torneio selecionado).

## 4. Um torneio pode ter mais de uma fase, e nem toda fase gera classificação

**Decision**: O registro de torneios (`collector/tournaments.py`) modela cada
torneio como uma lista de fases, cada uma com um flag `gera_classificacao: bool`. O
coletor pula a etapa de standings (não chama `parse_phase_standings`/
`insert_standings_snapshot`) para fases com `gera_classificacao=False`, mas
continua coletando jogos e estatísticas normalmente para elas.

**Rationale**: Confirmado contra a API real (2026-08-02) — `GET
/v1/tournaments/{id}` para os três torneios de 2025 retorna 2 fases cada:
"Classificação" (`type=elimination`) e "Playoffs" (`type=draw`). Os torneios de
2026 (em andamento) têm hoje só 1 fase ("Temporada Regular",
`type=elimination`) — o Playoffs de 2026 ainda não existe na fonte. Buscando `GET
/v1/phases/{phase_id}` da fase de Playoffs de Ouro 2025
(`51de7c2b-0be8-4a50-bdee-0ed3f5bacd94`), o payload retornou `eliminations: []` e
`elimination_stats: []` — vazio — mas trouxe um campo `draws` (estrutura de
chaveamento/bracket, não uma lista ordenada de times). O parsing existente de
`parse_phase_standings` (`collector/parsers.py:363+`) já levanta
`UnexpectedPayloadShape` quando `eliminations` vem vazio — correto para uma fase
que *deveria* ter classificação e não tem por erro/mudança de schema, mas **errado**
para uma fase que a fonte nunca pretendeu expor daquela forma. Por isso a decisão é
não chamar essa validação para fases marcadas como `gera_classificacao=False`, em
vez de capturar e engolir o erro — a distinção fica explícita na configuração, não
escondida atrás de um catch silencioso (mantém o espírito do Princípio II: falha
explícita quando é de fato inesperado, não quando é um formato já conhecido e
documentado).

**Alternatives considered**: Tentar parsear `draws` para reconstruir uma
classificação de playoffs — fora de escopo desta versão (spec.md, Assumptions); os
jogos de playoffs entram nos rankings/evolução de jogador, mas nenhuma tabela de
classificação é gerada para essa fase.

## 5. Cadência de coleta: recorrente vs. carga histórica única — RESOLVIDO

**Decision**: Torneios com `modo="recorrente"` (Ouro 2026, Prata/Bronze 2026) são
processados pelo mesmo workflow agendado do GitHub Actions (`collect.yml`), agora
iterando sobre os torneios recorrentes do registro. Torneios com
`modo="historico"` (Ouro/Prata/Bronze 2025) são processados por uma execução
manual do `collector.run` (uma vez por fase, 2 fases × 3 torneios = 6 execuções),
disparada localmente pelo mantenedor quando conveniente — sem entrar no cron.

**Rationale**: Confirmado com o mantenedor (2026-08-02). Temporadas encerradas não
mudam mais — colocá-las no cron recorrente gastaria chamadas à API sem necessidade
a cada execução agendada, sem nenhum ganho (Princípio II, "coleta responsável" +
Princípio VI).

**Alternatives considered**: Tratar todas as 5 igual no mesmo cron — mais simples
de implementar, mas rejeitado pelo mantenedor por desperdiçar chamadas à fonte para
dados que não mudam mais.

## 6. Registro de torneios como módulo Python estático, não YAML/JSON externo

**Decision**: `collector/tournaments.py` com `@dataclass(frozen=True)` para
`Fase`/`Torneio` e uma tupla `TORNEIOS` com os 5 registros, ids reais incluídos
(ver `contracts/tournament-registry.md`).

**Rationale**: `requirements.txt` não tem nenhum parser de YAML hoje (ver
`plan.md`, Technical Context); adicionar uma dependência nova só para ler 5
registros fixos, versionados junto com o código, não se justifica (Princípio VI).
Um módulo Python com dataclasses é tão auditável quanto YAML para este volume, e
ganha validação de tipo estática/em import-time de graça.

**Alternatives considered**: Arquivo `config/tournaments.yaml` — rejeitado por
exigir uma dependência nova (`PyYAML`) sem necessidade demonstrada.

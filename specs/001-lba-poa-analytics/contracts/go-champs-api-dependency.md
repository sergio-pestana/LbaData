# Contrato de Dependência Externa: API pública do go-champs

Este projeto não expõe API própria (uso individual, dashboard local). O contrato
crítico a documentar é o **inverso**: o que este sistema assume/depende da API
pública (não documentada oficialmente) do go-champs, e o que ele MUST validar antes
de confiar em cada resposta — em linha com o Princípio II da constituição
(resiliência a mudanças na fonte).

**IDs fixos da temporada (Ouro 2026)**:
- `tournament_id` = `5bf23f0b-6768-46ec-bcc1-4cd698105413`
- `phase_id` = `ede46bb2-21ac-411b-b07f-b93269bebd37`

## GET /v1/tournaments/{tournament_id}

**Uso**: metadados do torneio — catálogo de `player_stats`/`team_stats`
disponíveis (inclui `efficiency`, `plus_minus`), roster completo com `player_id`
estável, critérios de desempate (`elimination_stats`).

**Validação obrigatória antes de persistir**: confirmar que
`has_aggregated_player_stats = true` continua verdadeiro; se o catálogo de stats
mudar (campo esperado sumiu), tratar como mudança de schema (Princípio II) — logar
erro explícito, não seguir em frente silenciosamente.

**Cautela conhecida**: filtros `where[organization_slug]`/`where[slug]` não
demonstraram filtrar de forma confiável neste endpoint — buscar sempre por
`tournament_id` direto na URL, nunca confiar em filtro de query aqui.

## GET /v1/games?where[phase_id]={phase_id}

**Uso**: lista de jogos da fase — placar, times, data, `is_finished`/`live_state`.

**Validação obrigatória**: revalidar localmente que cada jogo retornado pertence
de fato ao `phase_id` esperado (não confiar cegamente no filtro `where[...]`,
mesma cautela do endpoint acima). Tratar `is_finished`/placar/data como
nullable/defensivo — nunca observamos `is_finished = false` em produção (não há
jogo futuro agendado no momento), então esse caminho não está validado contra um
exemplo real.

**Cautela conhecida**: os objetos de time embutidos aqui vêm com `players: []`
vazio — este endpoint é só para o resultado agregado do jogo, nunca usar como
fonte de roster/estatística por jogador.

## GET /v1/player-stats-logs?where[game_id]={game_id}

**Uso**: uma linha por jogador que esteve no elenco daquele jogo (inclui quem não
jogou, com `game_played = 0`) — fonte de `player_game_stats`.

**Validação obrigatória**: todos os campos estatísticos essenciais (pontos,
rebotes, assistências, arremessos, minutos, eficiência, plus/minus) MUST estar
presentes e com tipo esperado antes do upsert; qualquer ausência interrompe o
processamento apenas daquele jogo (Princípio II).

**Confirmado contra payload real** (jogo `1eb4007b-dc78-42aa-a5a0-70bfe476d4e2`,
2026-07-31):
- Todos os valores em `stats` vêm como **strings** (ex.: `"points": "4.0"`,
  `"game_played": "1"`), inclusive os campos booleanos-como-inteiro
  (`game_played`, `game_started`). O parser MUST converter explicitamente, nunca
  assumir tipo nativo.
- `minutes_played` está em **segundos**, não minutos nem `mm:ss` (confirmado:
  valor máximo observado no jogo = `2400` = 40 min × 60s, batendo com a duração
  regulamentar de uma partida; jogadores que não jogaram têm `"0"`).
- `field_goals_attempted`/`field_goals_made` representam **somente arremessos de
  2 pontos** (não incluem os de 3) — confirmado batendo a conta:
  `2×(field_goals_made) + 3×(three_point_field_goals_made) + free_throws_made`
  reproduz exatamente o placar do time (48 = 2×9 + 3×7 + 9). Isso é o oposto da
  convenção NBA (onde "FG" inclui os de 3) — **não presumir, usar sempre a soma
  dos dois campos para "arremessos de campo totais"**.

## GET /v1/team-stats-logs?where[game_id]={game_id}

**Uso**: equivalente ao endpoint acima, por time — fonte de `team_game_stats`.

**Validação obrigatória**: mesma postura do endpoint de player-stats-logs, com uma
diferença confirmada: aqui os valores em `stats` já vêm como **números** (não
strings) — inconsistência real entre os dois endpoints, o parser de cada um MUST
ter sua própria lógica de conversão de tipos, não compartilhar uma função ingênua
de cast.

**Confirmado contra payload real**: `wins`/`losses`/`fiba_group_points`/
`points_balance` neste endpoint são **do jogo específico** (ex.: 2 pontos FIBA por
vitória, 1 por derrota daquele jogo), não um total acumulado da temporada —
confirmado batendo `points`/`points_against` deste log contra `home_score`/
`away_score` do mesmo `game_id` em `/v1/games`.

## GET /v1/phases/{phase_id}

**Uso**: tabela de classificação já computada e ordenada pela plataforma, com
desempates oficiais aplicados — fonte de uma nova linha em `standings_snapshot` a
cada coleta.

**Estrutura real confirmada (2026-07-31) — bem diferente do que havíamos
assumido antes de ver o payload**: a resposta **não** tem uma lista plana de
times com campos legíveis. A classificação vem em:

```text
data.elimination_stats  → lista de critérios de desempate, cada um com
                           {id, ranking_criteria, ranking_order, team_stat_source, title}
                           (ex.: id=X, team_stat_source="wins", ranking_criteria="overall")
data.eliminations[0].team_stats → lista JÁ ORDENADA de times (posição = índice + 1);
                           cada item tem {team_id, stats: {<elimination_stats.id>: valor}}
```

Ou seja, os valores de cada time em `stats` são **indexados pelo `id` (uuid) do
critério em `elimination_stats`**, não por um nome legível como `"wins"` — é
necessário montar um dicionário `{elimination_stats[i].id: elimination_stats[i].team_stat_source}`
e usá-lo para traduzir as chaves antes de gravar. Também existem **critérios
duplicados por `team_stat_source`** distinguidos só pelo `ranking_criteria`
(ex.: `points_balance` aparece uma vez com `ranking_criteria="overall"` — o saldo
real da temporada — e outra com `"head_to_head"` — usado só como desempate).
**Usar sempre a entrada com `ranking_criteria="overall"`** para os campos de
`standings_snapshot`; a de `head_to_head` não deve ser confundida com o saldo
real. Confirmado com um torneio real de 8 times: `eliminations` tinha exatamente
1 elemento e `team_stats` continha os 8 times, na ordem certa.

**Validação obrigatória**: confirmar que `eliminations` tem pelo menos 1 elemento
e que `eliminations[0].team_stats` contém todos os times esperados do torneio
antes de gravar o snapshot; um snapshot parcial (times faltando, ou
`elimination_stats` sem as chaves esperadas — `game_played`, `wins`, `losses`,
`fiba_group_points`, `points_balance` overall) é tratado como falha daquela
coleta, não persistido parcialmente.

## GET /v1/aggregated-player-stats-by-tournament?where[team_id]={team_id}&where[tournament_id]={tournament_id}

**Uso**: apenas como referência cruzada eventual/depuração — **não é usado como
fonte de nenhuma tabela** nesta versão, já que os totais de temporada são
derivados de `player_game_stats` (ver data-model.md e research.md #1). Requer
iterar sobre todos os `team_id` do torneio para cobrir a liga inteira, uma
chamada por time.

## Regras gerais de acesso (todas as chamadas)

- Sem autenticação (API pública).
- Sequencial, nunca paralelo; intervalo mínimo configurável entre chamadas.
- `robots.txt` do host verificado antes da execução da coleta.
- `User-Agent` identificável enviado em toda requisição.
- Nenhuma resposta é confiada sem a validação descrita acima para o endpoint
  correspondente.

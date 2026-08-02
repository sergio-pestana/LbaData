# Phase 0 Research: Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026

## 1. Acesso ao Postgres/Supabase: `psycopg2` direto vs. cliente `supabase-py`

**Decision**: Usar `psycopg2` com SQL explícito (`INSERT ... ON CONFLICT (id_externo)
DO UPDATE SET ...`) para todos os writes, conectando diretamente à string de conexão
Postgres do Supabase.

**Rationale**: O upsert por chave de conflito é uma exigência direta do Princípio I
(Integridade dos Dados). `ON CONFLICT` do Postgres expressa essa regra de forma
explícita e auditável em SQL simples — visível e testável sem depender do
comportamento de upsert de uma biblioteca de terceiros (PostgREST via
`supabase-py`), que adiciona uma camada de abstração desnecessária para um projeto
deste volume (Princípio VI). Usar SQL direto também facilita escrever as
`migrations/` como arquivos `.sql` puros, revisáveis e versionáveis.

**Alternatives considered**: `supabase-py` (cliente oficial) — rejeitado por
adicionar uma dependência e uma camada de tradução (REST→SQL) sem ganho real para
um único mantenedor que já sabe SQL; `SQLAlchemy` — rejeitado pelo mesmo motivo
(ORM é complexidade extra não justificada pelo volume de dados real).

## 2. Cliente HTTP, rate limiting e `robots.txt`

**Decision**: `requests` com uma função wrapper que (a) aplica um intervalo mínimo
configurável entre chamadas (ex.: 1–2s, via `time.sleep`), (b) roda as chamadas
sempre sequencialmente (nunca em paralelo/threads), (c) verifica `robots.txt` do
host uma vez por execução via `urllib.robotparser`, recusando a coleta se o path da
API estiver desautorizado, e (d) envia um `User-Agent` identificável (nome do
projeto + finalidade, sem se passar por navegador).

**Rationale**: Atende diretamente ao Princípio II (coleta respeitosa) com as
ferramentas mais simples da biblioteca padrão do Python, sem necessidade de um
framework de scraping.

**Alternatives considered**: `httpx` (assíncrono) — rejeitado porque o volume e a
cautela exigida (sequencial, com pausas) tornam concorrência contraproducente;
`Scrapy` — rejeitado por ser um framework pesado para um coletor de poucos
endpoints JSON.

## 3. Validação defensiva do payload (schema da fonte não documentado)

**Decision**: Cada função de parsing em `collector/parsers.py` valida
explicitamente os campos essenciais esperados (presença + tipo) antes de retornar
um registro; qualquer campo ausente/tipo inesperado levanta uma exceção específica
(`UnexpectedPayloadShape`) capturada em `collector/run.py` e logada com o `game_id`
afetado — o processamento continua para os demais jogos da rodada. Filtros
`where[...]` da API (ex.: `phase_id`, `game_id`) não são confiados cegamente: a
resposta é sempre revalidada localmente (ex.: conferindo que os jogos retornados
realmente pertencem à `phase_id` esperada) antes de persistir, já que
`where[organization_slug]`/`where[slug]` em `/v1/tournaments` demonstrou não
filtrar de forma confiável.

**Rationale**: Implementa diretamente o Princípio II ("falhar de forma explícita e
logada, nunca silenciosamente") e a cautela relatada pelo usuário sobre filtros
`where[...]` não confiáveis.

**Alternatives considered**: Validação com `pydantic` — considerada, mas adiada
como possível refinamento futuro; para o volume atual, validação manual explícita
por campo é suficiente e mais simples de auditar linha a linha (Princípio VI).

## 4. Formato de "minutos jogados" no payload de `player-stats-logs` — RESOLVIDO

**Decision**: `stats.minutes_played` é uma **string representando segundos**
inteiros (ex.: `"826"`, `"2400"`). Confirmado contra payload real de um jogo:
o valor máximo observado foi `2400`, que é exatamente 40 minutos × 60 segundos
(duração regulamentar de uma partida) — dois jogadores titulares que não saíram
de quadra têm exatamente `2400`. `parsers.py` MUST converter para minutos
decimais dividindo por 60 (`float(stats["minutes_played"]) / 60`) antes de
qualquer cálculo (ex.: índice de utilização). Jogadores com `game_played="0"` têm
`"0"`.

**Rationale**: Validado empiricamente contra a API real (não documentada
oficialmente) durante a Camada 1 — a suposição anterior (aguardar confirmação)
foi resolvida com dados reais antes de a Camada 2 (armazenamento) ser construída,
como exigido pelo Princípio II.

**Alternatives considered**: `mm:ss` string — descartado, o valor observado não
tem separador e o máximo bate exatamente com segundos de jogo, não minutos
(`2400` seria um valor absurdo de minutos, mas é exatamente 40min em segundos).

## 5. Fórmula do índice de "impacto" (Eficiência + Plus/Minus)

**Decision**: Normalizar Eficiência e Plus/Minus por z-score dentro do conjunto de
jogadores com jogos suficientes na temporada, depois somar os dois z-scores com
peso igual (50/50) para formar o índice de impacto.

**Rationale**: Eficiência e Plus/Minus têm escalas muito diferentes (Eficiência
tende a ser um número positivo maior; Plus/Minus é tipicamente menor e pode ser
negativo) — somar os valores brutos faria Eficiência dominar o índice
artificialmente. Normalizar por z-score coloca as duas métricas na mesma escala
antes de combiná-las, sem introduzir pesos arbitrários não sustentados pelos dados
(Princípio VI — a alternativa mais simples que ainda resolve o problema real de
escala).

**Alternatives considered**: Soma direta dos valores brutos — rejeitada por deixar
Eficiência dominar; pesos arbitrários (ex.: 70/30) — rejeitados por não terem
justificativa a priori; combinação via ranking (média das posições em cada métrica)
— alternativa válida mas descartada por perder a magnitude da diferença entre
jogadores, informação que o z-score preserva.

## 6. Limiar de "baixa confiança" por amostra pequena (Princípio VII)

**Decision**: Definir um limiar mínimo configurável, com valor default de 3 jogos —
qualquer métrica derivada (ranking, tendência, utilização, impacto) calculada sobre
menos de 3 jogos do jogador/time é sinalizada como baixa confiança na
apresentação, mas o número de jogos que a sustenta é sempre exibido de qualquer
forma (FR-013), independentemente do limiar.

**Rationale**: O spec deixa o limiar exato a critério do mantenedor; 3 jogos é um
valor de partida razoável (evita marcar a maioria dos jogadores regulares como
baixa confiança, mas ainda sinaliza estreias/poucos jogos) e é trivialmente
ajustável depois, sem exigir mudança de schema.

**Alternatives considered**: Limiar de 5 ou 10 jogos — descartados por serem
excessivamente conservadores para uma temporada curta de liga amadora, onde
poderiam marcar quase todo mundo como baixa confiança nas primeiras rodadas.

## 7. Agendamento via GitHub Actions (cron em UTC)

**Decision**: Dois jobs de cron no mesmo workflow `collect.yml`: (a) domingo à
noite, horário de Porto Alegre (UTC-3) — expressão cron em UTC equivalente; (b)
segunda-feira de manhã (salvaguarda), também convertida para UTC. Ambos os jobs
chamam a mesma rotina incremental de coleta (`collector/run.py`), que naturalmente
não duplica rodadas já processadas corretamente (Princípio I) — a segunda execução
é uma rede de segurança barata, não um caminho de código separado.

**Rationale**: GitHub Actions cron roda em UTC; documentar a conversão explícita
evita o erro comum de agendar no fuso errado. Rodar a mesma rotina idempotente duas
vezes é mais simples (Princípio VI) do que criar lógica condicional para
diferenciar "coleta principal" de "coleta de salvaguarda".

**Alternatives considered**: Um único job de coleta (sem salvaguarda) — rejeitado
pelo próprio requisito do usuário de proteger contra jogos que terminam tarde no
domingo.

## 8. Estratégia de testes com fixtures

**Decision**: Salvar um payload JSON real (anonimizado apenas se necessário, mas os
dados aqui já são públicos) por endpoint em `tests/fixtures/` (`tournament.json`,
`games_phase.json`, `player_stats_logs_<game_id>.json`,
`team_stats_logs_<game_id>.json`, `phase_standings.json`). Testes de contrato
(`tests/contract/`) validam que `collector/parsers.py` extrai corretamente os
campos esperados desses fixtures. Testes unitários de `modeling/` usam listas de
dicts/DataFrames sintéticos (não fixtures de API), já que essa camada não depende do
formato HTTP. Um teste de integração manual (`tests/integration/test_live_api.py`)
roda contra a API real sob demanda (nunca em CI automática), para detectar
mudanças reais de schema na fonte.

**Rationale**: Implementa diretamente a orientação do usuário e o Princípio III
(cada camada testável isoladamente): `collector` é testado contra fixtures fixos
(determinístico, rápido, sem rede), `modeling` é testado sem nenhuma dependência de
rede ou banco.

**Alternatives considered**: Mockar a API com uma biblioteca de mocking HTTP (ex.:
`responses`) — desnecessário adicional; fixtures JSON estáticos já bastam e são
mais fáceis de inspecionar manualmente.

## 9. Parsing da classificação (`GET /v1/phases/{phase_id}`) — descoberto na Camada 1

**Decision**: A resposta real não é uma lista plana e legível — os valores por
time em `eliminations[0].team_stats[].stats` são indexados pelo `id` (uuid) de
cada critério em `elimination_stats`, não por um nome como `"wins"`. O parser
MUST montar um dicionário `{elimination_stats[i].id: team_stat_source}` e usar
esse dicionário para traduzir as chaves antes de extrair `jogos` (`game_played`),
`vitorias` (`wins`), `derrotas` (`losses`), `pontos_fiba` (`fiba_group_points`) e
`saldo_pontos` (`points_balance`) — sempre pegando a entrada com
`ranking_criteria = "overall"` quando o mesmo `team_stat_source` aparece
duplicado com `"head_to_head"` (usado só para desempate, não é o saldo real da
temporada). A posição na classificação é o índice do time dentro de
`eliminations[0].team_stats` (já vem ordenado pela plataforma).

**Rationale**: Só foi possível descobrir essa estrutura batendo o payload real —
a suposição inicial (lista plana com campos legíveis) estava incorreta. Isso é
exatamente o tipo de mudança de estrutura que o Princípio II pede para nunca ser
assumida silenciosamente; documentar aqui evita que a Camada 2 seja construída
sobre uma suposição errada.

**Alternatives considered**: Nenhuma — não há como adivinhar esse formato sem
inspecionar um payload real, já que a fonte não é documentada oficialmente.

## 10. Convenção de "arremessos de campo" (`field_goals_*`) — descoberto na Camada 1

**Decision**: Confirmado contra payload real que `field_goals_attempted`/
`field_goals_made` representam **somente arremessos de 2 pontos**, e
`three_point_field_goals_*` é uma categoria totalmente separada (não uma
subcategoria de `field_goals`, ao contrário da convenção usual da NBA). Confirmado
batendo a conta: `2×field_goals_made + 3×three_point_field_goals_made +
free_throws_made` reproduz exatamente o placar do time no jogo de referência
(48 = 2×9 + 3×7 + 9). O mapeamento em `data-model.md`
(`arremessos_2pt_tentados`/`_convertidos` ← `field_goals_*`;
`arremessos_3pt_tentados`/`_convertidos` ← `three_point_field_goals_*`) está
correto e não precisa mudar.

**Rationale**: Validação empírica evita um bug silencioso de contagem dupla (ou
subcontagem) de arremessos de 3 pontos em qualquer métrica que some "arremessos
de campo totais" — Princípio II.

**Alternatives considered**: N/A — achado de validação, não uma escolha de
design.

## 11. Conexão com o Supabase: pooler (Supavisor), não conexão direta — descoberto ao configurar a Camada 2

**Decision**: Conectar sempre via **Session Pooler** do Supabase
(`aws-0-<região>.pooler.supabase.com`, usuário no formato
`postgres.<project-ref>`), nunca via conexão direta
(`db.<project-ref>.supabase.co`).

**Rationale**: Testado contra o projeto real — a conexão direta só resolve
para um endereço IPv6, e a rede usada aqui (como a maioria das redes
domésticas/ISPs) não tem rota IPv6 funcional, resultando em "Connection
refused" mesmo com credenciais corretas. IPv4 dedicado para a conexão direta é
um add-on pago (Pro Plan) do Supabase. O pooler (Supavisor) tem endereço IPv4
e é gratuito em qualquer plano — resolve o problema sem custo adicional e sem
exigir configuração de rede.

**Alternatives considered**: IPv4 dedicado (add-on pago) — descartado, custo
desnecessário para um projeto de liga amadora (Princípio VI); configurar
túnel/rota IPv6 manualmente — descartado, complexidade operacional
desproporcional ao problema.

## 12. Campos de contagem ausentes na súmula real — descoberto na primeira coleta completa (Camada 2)

**Decision**: Em `player-stats-logs`, campos CENTRAIS (`points`,
`minutes_played`, `game_played`, `efficiency`, `plus_minus`) continuam
obrigatórios — ausência ou tipo inválido derruba o processamento daquele jogo
(Princípio II). Campos de CONTAGEM (rebotes, assistências, roubos, tocos,
faltas de todos os tipos, arremessos, lances livres, turnovers) que vierem
ausentes são tratados como `0`, com um `WARNING` logado explicitando
jogo/jogador/campo — não interrompem mais o processamento do jogo inteiro.

**Rationale**: Na primeira coleta real completa (2026-07-31), 2 dos 23 jogos
falharam porque um único jogador, em cada um, tinha uma linha de súmula
parcial — claramente havia jogado (pontos, minutos e eficiência presentes),
mas faltavam campos como `rebounds_offensive`, `assists`, `fouls_personal`,
em alguns casos até `field_goals_made`/`turnovers`. O padrão indica que a mesa
da liga às vezes omite a chave de um campo por completo quando o valor seria
zero, em vez de mandar `"0"` — um comportamento inconsistente da fonte
(esperado dado que não é documentada oficialmente), não uma mudança real de
schema. Falhar o jogo inteiro por isso era desproporcional: o usuário decidiu
explicitamente (após ver os dois casos reais) que graus de incompletude em
campos secundários não deveriam bloquear os dados centrais do jogo, desde que
a omissão fique visível em log — decisão tomada com dados reais em mãos, não
hipoteticamente antes de rodar a coleta.

**Alternatives considered**: Manter estrito (derrubar o jogo inteiro) —
rejeitado pelo usuário por ser desproporcional a uma omissão em estatística
secundária quando o essencial do jogo está íntegro; usar `pydantic` com
campos opcionais — desnecessário, a validação manual explícita já cobre o
caso com clareza equivalente (Princípio VI).

## 13. Colunas `numeric` do Postgres voltam como `Decimal`, não `float` — descoberto ao validar a Camada 3

**Decision**: `storage/reads.py` converte todo `decimal.Decimal` para `float`
antes de devolver as linhas para a camada de modelagem (função `_normalize`,
aplicada a toda linha de toda leitura).

**Rationale**: `psycopg2` devolve colunas `numeric` (`eficiencia`,
`minutos_jogados`, `fiba_group_points`, `pontos_fiba`, `saldo_pontos` em
alguns casos) como `decimal.Decimal`, não `float`. `usage_index` quebrou na
primeira execução real (`TypeError: unsupported operand type(s) for +=:
'float' and 'decimal.Decimal'`) porque a modelagem assumia `float` em toda
aritmética. Corrigir na leitura (Camada 2), uma vez só, é mais simples do que
espalhar conversões por cada função de modelagem (Princípio III — a
modelagem não deveria precisar saber de detalhes de tipo do driver do banco;
Princípio VI — um único ponto de conversão é mais simples que N).

**Alternatives considered**: Converter em cada função de `modeling/` que usa
um campo numérico — rejeitado, motivo de bug repetido a cada nova função;
usar `psycopg2` com um adaptador de tipo customizado para `numeric` global —
mais complexo que a solução adotada para o ganho equivalente.

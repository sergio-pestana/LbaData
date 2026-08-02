# Feature Specification: Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026

**Feature Branch**: `001-lba-poa-analytics`

**Created**: 2026-07-31

**Status**: Draft

**Input**: User description: "Quero construir, com padrão profissional, uma plataforma de acompanhamento e análise do campeonato amador de basquete da minha cidade (LBA POA, temporada Ouro 2026), cujos dados de jogos e estatísticas são publicados em https://go-champs.com/lba-poa/ouro2026. Coleta de dados: depois que as partidas de um final de semana (sábado e domingo) terminam, o sistema deve capturar automaticamente todos os jogos realizados e a súmula completa de cada um — placar, estatísticas por jogador e por time. Os dados de uma rodada devem estar disponíveis para consulta até a segunda-feira seguinte. A coleta deve ser incremental: rodadas já processadas corretamente não podem ser reprocessadas do zero, mas o sistema deve conseguir corrigir uma partida se a súmula publicada mudar depois. Análise e visualização: jogos realizados/restantes, classificação, melhores jogadores por diferentes critérios, evolução (tendência) de times e jogadores, concentração de posse/utilização, e impacto no resultado das partidas. Uso individual, sem autenticação nesta versão, mas com qualidade de produção. Fora de escopo: dados em tempo real, outras ligas/temporadas, previsões/apostas, edição manual de dados."

## Clarifications

### Session 2026-07-31

- Q: Qual métrica usar para "impacto no resultado das partidas" (FR-012)? → A: Criar um índice próprio de impacto combinando Eficiência e Plus/Minus (ambos já calculados pela plataforma-fonte) em um único valor; o método exato de combinação/peso fica definido na fase de planejamento.
- Q: Como calcular a métrica de "utilização/posse" ofensiva por jogador (FR-011)? → A: Índice simples (arremessos de campo tentados + lances livres tentados + turnovers) normalizado por minuto jogado, sem estimar posses do time inteiro.
- Q: O que o sistema deve fazer quando um jogo já processado como "realizado" é depois marcado como cancelado/adiado na fonte? → A: Marcar a partida como "cancelada" (status), preservando o registro histórico, e excluí-la das contagens/classificação a partir da próxima coleta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coleta automática confiável após cada rodada (Priority: P1)

Como mantenedor, depois que os jogos de um fim de semana (sábado e domingo) terminam,
quero que o sistema capture sozinho todos os jogos e súmulas completas daquela
rodada, para que eu não precise coletar nada manualmente e possa confiar que os
dados estarão prontos até a segunda-feira seguinte.

**Why this priority**: Sem essa capacidade, nenhuma das visões analíticas tem dado
fresco para mostrar. É a fundação de que tudo mais depende — sem ela o resto do
sistema fica com dados desatualizados ou exige trabalho manual repetido toda semana.

**Independent Test**: Pode ser testado isoladamente aguardando o fim de uma rodada
real (ou simulando uma resposta da fonte) e verificando, na segunda-feira seguinte,
que todos os jogos daquele fim de semana e suas súmulas completas estão persistidos
e consultáveis, sem qualquer ação manual do mantenedor.

**Acceptance Scenarios**:

1. **Given** uma rodada de sábado/domingo terminou e a fonte publicou as súmulas,
   **When** o sistema roda sua coleta agendada, **Then** todos os jogos da rodada e
   suas estatísticas completas (por jogador e por time) ficam disponíveis para
   consulta até a segunda-feira seguinte.
2. **Given** uma rodada já foi processada corretamente anteriormente, **When** o
   sistema roda novamente, **Then** os jogos dessa rodada não são duplicados nem
   reprocessados do zero.
3. **Given** uma partida já processada teve sua súmula corrigida na fonte (ex.: erro
   de digitação da mesa), **When** o sistema roda a coleta seguinte, **Then** o
   registro da partida é atualizado com os dados corrigidos, sem criar uma partida
   duplicada, e mantendo rastro de quando a correção ocorreu.
4. **Given** a fonte muda a estrutura da resposta ou retorna dados incompletos para
   um jogo, **When** o sistema tenta processar esse jogo, **Then** o processamento
   daquele jogo específico falha de forma explícita e logada, sem comprometer os
   demais jogos da rodada e sem persistir dado incompleto ou inventado.

---

### User Story 2 - Panorama da temporada e classificação (Priority: P1)

Como mantenedor, quero ver quantos jogos já aconteceram e quantos faltam, além da
tabela de classificação atualizada dos times, para acompanhar o andamento geral da
temporada de forma rápida.

**Why this priority**: É a pergunta mais básica e recorrente sobre qualquer
campeonato ("como está o campeonato?") e depende apenas da coleta (User Story 1) já
estar funcionando — entrega valor imediato assim que há dados de pelo menos uma
rodada.

**Independent Test**: Pode ser testado abrindo o dashboard após pelo menos uma
rodada processada e conferindo que a contagem de jogos realizados/restantes e a
classificação batem com os resultados oficiais publicados pela fonte.

**Acceptance Scenarios**:

1. **Given** existem jogos processados de pelo menos uma rodada, **When** o
   mantenedor abre a visão de panorama da temporada, **Then** o sistema mostra
   quantos jogos já ocorreram e quantos ainda restam no calendário da temporada.
2. **Given** os jogos de uma rodada foram processados, **When** o mantenedor abre a
   tabela de classificação, **Then** ela reflete vitórias, derrotas e critérios de
   ordenação consistentes com os resultados de todos os jogos já processados.

---

### User Story 3 - Melhores jogadores por critério, por time e pela liga (Priority: P2)

Como mantenedor, quero identificar os melhores jogadores de cada time e da liga
inteira, segundo diferentes critérios estatísticos (pontos, eficiência, etc.), para
poder comparar desempenho individual de forma objetiva.

**Why this priority**: Depende apenas de dados já coletados (não exige a
modelagem de tendência ou impacto), mas entrega um valor analítico claro acima do
panorama básico da User Story 2.

**Independent Test**: Pode ser testado escolhendo um critério estatístico
disponível (ex.: pontos) e conferindo que a ordenação de jogadores — por time e
para a liga inteira — corresponde aos totais/médias calculados a partir das
súmulas processadas.

**Acceptance Scenarios**:

1. **Given** existem jogos processados, **When** o mantenedor seleciona um critério
   estatístico (ex.: pontos, eficiência), **Then** o sistema mostra o ranking de
   jogadores daquele critério, tanto por time quanto para a liga inteira.
2. **Given** um jogador tem poucas partidas disputadas, **When** ele aparece em um
   ranking, **Then** o número de jogos que sustenta o valor exibido é visível junto
   ao ranking.

---

### User Story 4 - Evolução de times e jogadores ao longo da temporada (Priority: P2)

Como mantenedor, quero ver como cada time e cada jogador vêm evoluindo ao longo da
temporada — a tendência rodada a rodada, não apenas o total acumulado — para
identificar quem está melhorando, piorando ou estável.

**Why this priority**: Agrega uma dimensão temporal que o ranking estático da User
Story 3 não oferece; depende de já existir histórico de mais de uma rodada para
fazer sentido, por isso vem depois.

**Independent Test**: Pode ser testado com dados de pelo menos duas rodadas
processadas, verificando que a visão de evolução mostra o valor de cada métrica
rodada a rodada (não só o acumulado até a última rodada).

**Acceptance Scenarios**:

1. **Given** existem jogos processados de duas ou mais rodadas, **When** o
   mantenedor abre a visão de evolução de um time ou jogador, **Then** o sistema
   mostra a métrica selecionada rodada a rodada ao longo da temporada, não apenas o
   valor acumulado atual.

---

### User Story 5 - Concentração de utilização/posse por time (Priority: P3)

Como mantenedor, quero saber quem mais concentra a posse/utilização do jogo em cada
time, para identificar quem são os jogadores em torno de quem o ataque do time gira.

**Why this priority**: É uma métrica aproximada (a fonte não expõe "posse de bola"
diretamente) e de menor urgência que classificação e rankings diretos, mas ainda
assim um diferencial analítico desejado pelo mantenedor.

**Independent Test**: Pode ser testado calculando a métrica de utilização
aproximada para os jogadores de um time com jogos processados e verificando que o
jogador apontado como maior concentrador de utilização é consistente com o volume
de arremessos/lances-livres tentados e turnovers que ele acumula.

**Acceptance Scenarios**:

1. **Given** existem jogos processados para um time, **When** o mantenedor abre a
   visão de utilização daquele time, **Then** o sistema aponta o(s) jogador(es) com
   maior concentração de utilização, com o número de jogos que sustenta o cálculo.

---

### User Story 6 - Impacto no resultado das partidas (Priority: P3)

Como mantenedor, quero saber quem tem maior impacto no resultado das partidas, para
identificar os jogadores mais decisivos da liga, não apenas os de maior volume
estatístico bruto.

**Why this priority**: Complementa as demais visões com uma leitura de "quem decide
jogos"; assim como a User Story 5, é uma métrica derivada de segunda ordem que
depende das demais camadas já estarem funcionando.

**Independent Test**: Pode ser testado calculando a métrica de impacto para
jogadores com jogos processados e verificando que o resultado é rastreável às
estatísticas de origem (Eficiência e/ou Plus/Minus) usadas na fórmula escolhida.

**Acceptance Scenarios**:

1. **Given** existem jogos processados, **When** o mantenedor abre o ranking de
   impacto, **Then** o sistema mostra os jogadores ordenados por impacto no
   resultado das partidas, com o número de jogos que sustenta cada valor.

---

### Edge Cases

- O que acontece se, até a segunda-feira, a fonte ainda não tiver publicado a
  súmula de um ou mais jogos do fim de semana? O sistema deve tratar esse jogo como
  pendente e não deve bloquear a disponibilização dos demais jogos já publicados da
  mesma rodada.
- Um jogo que aparece cancelado ou adiado na fonte depois de já ter sido processado
  como realizado é marcado com status "cancelada", preservando o registro para
  auditoria, e passa a ser excluído das contagens de jogos e da classificação a
  partir da próxima coleta (ver FR-018). Um jogo remarcado para outra data continua
  sendo tratado pela rodada a que pertence na fonte (ver Assumptions).
- Como o sistema trata um jogador que troca de time no meio da temporada? (ver
  Assumptions — estatísticas ficam associadas ao time em que a partida foi jogada.)
- O que acontece quando duas rodadas de fins de semana diferentes precisam ser
  processadas juntas (ex.: coleta atrasada por mais de uma semana)? O sistema deve
  processar cada rodada pendente de forma incremental, sem pular nem duplicar
  nenhuma.
- O que acontece quando um ranking (jogadores, utilização, impacto) é calculado
  sobre uma amostra muito pequena de jogos (ex.: jogador que entrou na liga há uma
  rodada)? O valor deve ser sinalizado como baixa confiança em vez de aparecer
  indistinguível de valores baseados em amostras maiores.
- Como critérios de desempate na classificação são resolvidos quando dois times têm
  o mesmo número de vitórias? O sistema segue o mesmo critério de desempate adotado
  pela fonte oficial, sem recalcular uma regra própria.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST coletar automaticamente, após o encerramento dos jogos
  de um fim de semana (sábado e domingo), todos os jogos realizados na rodada e a
  súmula completa de cada partida — placar, estatísticas por jogador e por time.
- **FR-002**: Os dados de uma rodada MUST estar disponíveis para consulta no sistema
  até a segunda-feira seguinte ao fim de semana em que os jogos ocorreram.
- **FR-003**: A coleta MUST ser incremental — rodadas já processadas corretamente
  MUST NOT ser reprocessadas do zero em execuções subsequentes.
- **FR-004**: O sistema MUST detectar quando a súmula de uma partida já processada
  foi alterada na fonte (ex.: correção de erro de digitação da mesa) e MUST
  atualizar o registro correspondente sem criar uma partida duplicada.
- **FR-005**: Toda correção de partida MUST ser auditável — o sistema MUST manter
  registro de quando cada partida foi originalmente processada e quando foi
  corrigida pela última vez.
- **FR-006**: O sistema MUST falhar de forma explícita e logada (nunca silenciosa)
  quando a estrutura da resposta da fonte mudar ou dados essenciais de um jogo
  vierem incompletos, interrompendo apenas o processamento daquele jogo específico,
  sem comprometer os demais jogos da rodada.
- **FR-007**: O sistema MUST exibir quantos jogos da temporada já ocorreram e
  quantos ainda restam no calendário.
- **FR-008**: O sistema MUST exibir uma tabela de classificação de times, atualizada
  com os resultados de todos os jogos processados.
- **FR-009**: O sistema MUST permitir identificar os melhores jogadores, tanto por
  time quanto para a liga inteira, ordenando por diferentes critérios estatísticos
  disponíveis na súmula (ex.: pontos, eficiência, rebotes, assistências).
- **FR-010**: O sistema MUST exibir a evolução de cada time e de cada jogador ao
  longo da temporada, rodada a rodada, além do valor acumulado.
- **FR-011**: O sistema MUST identificar, para cada time, o(s) jogador(es) que mais
  concentram a utilização/posse ofensiva do time, calculada como um índice de
  envolvimento ofensivo (arremessos de campo tentados + lances livres tentados +
  turnovers) normalizado por minuto jogado, sem estimar as posses totais do time.
- **FR-012**: O sistema MUST identificar os jogadores com maior impacto no resultado
  das partidas, usando um índice de impacto próprio que combina Eficiência e
  Plus/Minus (ambos já calculados pela fonte) em um único valor por jogador; a
  fórmula exata de combinação/peso é uma decisão de planejamento, não de escopo.
- **FR-013**: Toda métrica derivada exibida (rankings, tendência, utilização,
  impacto) MUST exibir, junto ao valor, o número de jogos que sustenta o cálculo.
- **FR-014**: O sistema MUST restringir a coleta e a análise à temporada Ouro 2026
  da LBA POA nesta versão, sem suportar outras ligas ou temporadas.
- **FR-015**: O sistema MUST NOT oferecer edição manual de dados pela interface;
  toda correção de dado MUST se originar de uma nova coleta a partir da fonte
  original.
- **FR-016**: O sistema MUST NOT processar ou exibir dados de jogos em andamento em
  tempo real; apenas dados pós-jogo (súmula final publicada).
- **FR-017**: O sistema MUST operar sem exigir autenticação de usuário nesta versão,
  sendo de uso individual pelo mantenedor.
- **FR-018**: Quando a fonte indicar que uma partida já processada como realizada foi
  cancelada ou adiada, o sistema MUST marcá-la com um status de "cancelada" —
  preservando o registro histórico para auditoria — e MUST excluí-la das contagens
  de jogos realizados e da tabela de classificação a partir da coleta seguinte.

### Key Entities *(include if feature involves data)*

- **Temporada**: a temporada Ouro 2026 da LBA POA — escopo fixo desta versão, não há
  múltiplas temporadas nem múltiplas ligas.
- **Rodada**: conjunto de jogos de um fim de semana (sábado e domingo), usada para
  rastrear o que já foi processado e o que ainda está pendente.
- **Partida**: confronto entre dois times, com placar final, data, status de
  processamento (ex.: processada, cancelada), e registro de quando foi criada e
  quando foi corrigida pela última vez, se aplicável. Partidas com status
  "cancelada" são preservadas para auditoria, mas excluídas de contagens e da
  classificação.
- **Time**: entidade participante da temporada; acumula vitórias, derrotas e saldo
  de pontos a partir das partidas processadas.
- **Jogador**: pertence a um time na temporada; acumula estatísticas por partida e
  agregadas ao longo da temporada.
- **Estatística de Partida por Jogador**: uma linha da súmula por jogador por
  partida — pontos, rebotes ofensivos/defensivos, assistências, roubos, tocos,
  faltas por tipo, arremessos de 2/3 pontos e lances livres tentados/convertidos,
  turnovers, minutos jogados, Eficiência e Plus/Minus.
- **Estatística de Partida por Time**: uma linha da súmula por time por partida —
  vitória/derrota, saldo de pontos, e demais totais agregados do time naquela
  partida.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após qualquer fim de semana com jogos realizados, 100% dos jogos e
  súmulas completas publicadas pela fonte estão disponíveis para consulta até a
  segunda-feira seguinte, sem qualquer intervenção manual do mantenedor.
- **SC-002**: A tabela de classificação e os totais de cada time correspondem
  exatamente aos resultados oficiais publicados pela fonte, para 100% dos jogos já
  processados.
- **SC-003**: O mantenedor consegue identificar os melhores jogadores da liga e de
  qualquer time, em qualquer critério estatístico suportado, em uma única visão, sem
  precisar cruzar ou calcular dados manualmente.
- **SC-004**: Quando uma súmula publicada é corrigida pela fonte após já ter sido
  processada, a correção se reflete no sistema sem duplicar a partida e sem exigir
  reprocessamento manual de rodadas anteriores.
- **SC-005**: 100% das métricas derivadas exibidas (rankings, tendência, utilização,
  impacto) indicam o número de jogos que sustenta o valor mostrado.
- **SC-006**: Ao longo de uma temporada completa, zero incidentes de partidas
  duplicadas ou de dados corretos sobrescritos incorretamente na base.

## Assumptions

- A fonte de dados (go-champs, torneio ouro2026 da LBA POA) permanece publicamente
  acessível para leitura durante toda a temporada, mantendo
  `has_aggregated_player_stats=true` e o catálogo completo de estatísticas via API.
- "Fim de semana" é definido como sábado e domingo; um jogo eventualmente disputado
  em outro dia é tratado como parte da rodada à qual pertence na fonte, não pela
  data em que a coleta rodou.
- O critério de desempate na tabela de classificação segue o mesmo critério adotado
  pela fonte oficial (ex.: FIBA group points), sem recálculo de uma regra própria.
- Uso do sistema é individual (o próprio mantenedor), sem necessidade de múltiplos
  perfis, permissões ou autenticação nesta versão — mas construído com qualidade de
  produção, não como protótipo descartável.
- O volume de dados é o de uma liga amadora — algumas centenas de linhas por
  temporada — e a complexidade da solução deve ser dimensionada para esse volume
  real.
- Um jogador que troca de time no meio da temporada mantém as estatísticas de cada
  partida associadas ao time pelo qual ele efetivamente jogou aquela partida, sem
  reatribuição retroativa ao novo time.
- Dados em tempo real durante o jogo, outras ligas/temporadas além de ouro2026,
  previsões/apostas e edição manual de dados pela interface estão fora do escopo
  desta primeira versão.

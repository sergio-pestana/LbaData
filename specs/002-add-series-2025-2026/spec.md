# Feature Specification: Múltiplos Torneios — Ouro 2025, Prata 2025, Bronze 2025 e Prata/Bronze 2026

**Feature Branch**: `002-add-series-2025-2026`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Adicionar coleta e dashboard para as séries Ouro 2025, Prata 2025/2026 e Bronze 2025/2026 — hoje o sistema só suporta Ouro 2026."

## Clarifications

### Session 2026-08-02

- Q: Prata e Bronze aparecem como um único torneio combinado em 2026 ("LBA 2026 -
  Série Prata/Bronze", slug `bronze2026`), diferente de 2025 que tem dois torneios
  separados (`prata2025` e `bronze2025`). Confirma que é isso mesmo, não um torneio
  faltando na listagem? → A: Sim, é uma série combinada em 2026 (mudança de formato
  da liga).
- Q: As temporadas 2025 já terminaram — a coleta delas deve ser uma carga histórica
  única (backfill) ou entrar no mesmo job recorrente que já existe para 2026? → A:
  Carga histórica única para as três séries de 2025; 2026 (Ouro e agora também
  Prata/Bronze) continua no job recorrente existente.
- Q: A fase de Playoffs (existe só nas séries 2025 até agora) não tem tabela de
  classificação pronta na fonte — deve coletar jogos/estatísticas dessa fase mesmo
  assim? → A: Sim, coletar jogos e estatísticas dos playoffs; só não gerar
  classificação para essa fase específica (a fonte não a disponibiliza nesse
  formato).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Carga histórica das temporadas 2025 encerradas (Priority: P1)

Como mantenedor, quero carregar de uma vez os dados completos de Ouro 2025, Prata
2025 e Bronze 2025 — todos os jogos e súmulas de Classificação e Playoffs — para
poder consultar essas temporadas já encerradas no mesmo dashboard, sem precisar de
coleta recorrente para dados que não vão mais mudar.

**Why this priority**: É o pré-requisito de dado para qualquer visão dessas três
temporadas; sem essa carga não há nada para mostrar. Prioridade P1 porque libera de
imediato três temporadas inteiras de conteúdo histórico.

**Independent Test**: Pode ser testado rodando a carga histórica para um dos três
torneios e conferindo que todos os jogos de ambas as fases (Classificação e
Playoffs) e as súmulas completas ficam disponíveis para consulta, batendo com os
resultados oficiais publicados pela fonte.

**Acceptance Scenarios**:

1. **Given** um torneio de 2025 (Ouro, Prata ou Bronze) com temporada encerrada na
   fonte, **When** o mantenedor executa a carga histórica desse torneio, **Then**
   todos os jogos e súmulas completas de todas as fases do torneio ficam persistidos
   e consultáveis.
2. **Given** a carga histórica de um torneio já foi executada com sucesso, **When**
   o mantenedor a executa novamente, **Then** nenhum jogo é duplicado — a operação é
   segura para reexecutar.
3. **Given** a carga histórica de um torneio é interrompida no meio (ex.: erro de
   rede), **When** o mantenedor a executa novamente, **Then** o processamento
   retoma sem duplicar os jogos já processados com sucesso antes da interrupção.
4. **Given** um torneio tem uma fase do tipo chaveamento/bracket (ex.: Playoffs) sem
   tabela de classificação pronta na fonte, **When** o sistema coleta essa fase,
   **Then** os jogos e estatísticas dessa fase são persistidos normalmente, e a
   ausência de classificação para essa fase específica não é tratada como falha.

---

### User Story 2 - Coleta recorrente ampliada para Prata/Bronze 2026 (Priority: P1)

Como mantenedor, quero que a coleta automática recorrente que já existe para Ouro
2026 passe a cobrir também Prata/Bronze 2026, para acompanhar as duas temporadas em
andamento com a mesma confiabilidade.

**Why this priority**: Mesma criticidade da coleta original (spec 001) — sem ela, a
nova série em andamento fica sem dados atualizados. P1 porque é uma temporada ativa,
ao contrário das históricas da User Story 1.

**Independent Test**: Pode ser testado aguardando uma rodada de Prata/Bronze 2026
terminar e conferindo, após a execução agendada, que os jogos e súmulas daquela
rodada estão disponíveis, do mesmo jeito que já acontece hoje para Ouro 2026.

**Acceptance Scenarios**:

1. **Given** uma rodada de Prata/Bronze 2026 terminou e a fonte publicou as súmulas,
   **When** a coleta agendada roda, **Then** os jogos e estatísticas dessa rodada
   ficam disponíveis para consulta, com a mesma janela de tempo garantida hoje para
   Ouro 2026 (spec 001, SC-001).
2. **Given** a coleta recorrente processa múltiplos torneios ativos, **When** a
   coleta de um torneio falha, **Then** a falha não impede a coleta dos demais
   torneios ativos naquela execução.

---

### User Story 3 - Selecionar temporada/série no dashboard (Priority: P1)

Como mantenedor, quero escolher no dashboard qual torneio/temporada estou vendo
(Ouro 2026, Prata/Bronze 2026, Ouro 2025, Prata 2025 ou Bronze 2025), para navegar
entre as diferentes séries e temporadas sem que os dados se misturem.

**Why this priority**: Sem um seletor, as demais User Stories não têm como ser
consumidas — é a porta de entrada para tudo que já existe no dashboard (spec 001)
funcionar por torneio. P1 porque bloqueia o uso de qualquer temporada além da atual.

**Independent Test**: Pode ser testado selecionando cada um dos torneios
disponíveis no dashboard e conferindo que classificação, estatísticas de jogadores e
gráficos de impacto/utilização mostram exclusivamente dados daquele torneio.

**Acceptance Scenarios**:

1. **Given** existem dados de mais de um torneio carregados, **When** o mantenedor
   seleciona um torneio no dashboard, **Then** todas as visões (classificação,
   estatísticas de jogadores, impacto e utilização) mostram apenas dados daquele
   torneio.
2. **Given** o mantenedor troca de um torneio para outro no dashboard, **When** a
   troca acontece, **Then** nenhum dado do torneio anterior permanece visível ou
   contamina os cálculos do torneio recém-selecionado.

---

### User Story 4 - Isolamento de times e jogadores entre torneios (Priority: P2)

Como mantenedor, quero que times e jogadores sejam tratados como registros
independentes por torneio, mesmo quando o mesmo time ou atleta aparece em mais de
uma temporada, para que estatísticas de uma temporada nunca sejam somadas ou
confundidas com as de outra.

**Why this priority**: É uma garantia estrutural que sustenta a corretude de todas
as outras User Stories, mas só se torna um risco concreto (e observável) quando há
múltiplos torneios simultâneos — daí vir depois das P1 que já entregam a navegação
básica.

**Independent Test**: Pode ser testado identificando um time ou jogador que
participou de dois torneios diferentes cobertos por este projeto e conferindo que
cada aparição tem estatísticas e identidade completamente separadas, sem soma ou
mistura entre os dois torneios.

**Acceptance Scenarios**:

1. **Given** um time participa de dois torneios diferentes (ex.: Ouro 2025 e Ouro
   2026), **When** o mantenedor consulta as estatísticas desse time em cada
   torneio, **Then** os valores mostrados refletem apenas os jogos daquele torneio
   específico.

---

### Edge Cases

- Uma fase do tipo chaveamento/bracket (ex.: Playoffs) sem tabela de classificação
  pronta na fonte tem seus jogos e estatísticas coletados normalmente; nenhuma linha
  de classificação é gerada para essa fase específica, e isso não é um erro (ver
  User Story 1, cenário 4).
- Um torneio em andamento (2026) ainda não tem fase de Playoffs criada na fonte no
  momento desta versão; quando a fonte criar essa fase, o sistema deve conseguir
  incluí-la na coleta recorrente por configuração, sem exigir nova versão de código.
- O mesmo time ou jogador aparece em mais de um torneio coberto (ex.: joga Ouro 2025
  e também Ouro 2026): cada aparição é um registro independente por torneio (ver
  User Story 4 e Assumptions) — não há tentativa de unificar identidade entre
  temporadas nesta versão.
- O que acontece se a carga histórica de um torneio 2025 for executada antes de
  todas as três fases (Classificação e Playoffs) estarem completas na fonte? O
  sistema deve coletar o que já estiver publicado e permitir reexecução posterior
  sem duplicar (mesma garantia de idempotência da User Story 1, cenário 2/3).
- Um torneio novo sem nenhum dado carregado ainda aparece no seletor do dashboard? O
  seletor deve deixar claro quando um torneio selecionado não tem dados suficientes
  para popular uma visão, em vez de mostrar uma tela quebrada ou vazia sem
  explicação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST suportar múltiplos torneios simultaneamente: Ouro 2026
  (já existente), Prata/Bronze 2026, Ouro 2025, Prata 2025 e Bronze 2025.
- **FR-002**: Todo dado por torneio (times, jogadores, jogos, estatísticas,
  classificação) MUST ficar isolado entre torneios — nenhuma listagem ou métrica
  MUST combinar registros de torneios diferentes.
- **FR-003**: Para os torneios de temporada encerrada (Ouro 2025, Prata 2025, Bronze
  2025), o sistema MUST oferecer uma carga histórica que colete os dados uma única
  vez, cobrindo todas as fases do torneio (Classificação e Playoffs), sem exigir
  coleta recorrente contínua para esses torneios.
- **FR-004**: Para os torneios em andamento (Ouro 2026 e Prata/Bronze 2026), o
  sistema MUST manter a coleta automática recorrente já existente (spec 001),
  estendida para cobrir também Prata/Bronze 2026 com a mesma cadência e garantia de
  disponibilidade.
- **FR-005**: O sistema MUST coletar jogos e estatísticas por jogador/time de toda
  fase de um torneio, incluindo fases do tipo chaveamento/bracket (ex.: Playoffs),
  do mesmo modo que fases de classificação.
- **FR-006**: O sistema MUST NOT exigir uma tabela de classificação pronta para
  fases em que a fonte não a disponibiliza nesse formato (ex.: fase de chaveamento);
  a ausência de classificação para essa fase específica MUST NOT ser tratada como
  falha de coleta.
- **FR-007**: O dashboard MUST permitir ao mantenedor selecionar qual torneio está
  visualizando entre os torneios suportados, e toda visão analítica existente
  (classificação, estatísticas de jogadores, impacto e utilização) MUST refletir
  exclusivamente os dados do torneio selecionado.
- **FR-008**: Ao processar múltiplos torneios numa mesma execução de coleta, uma
  falha na coleta de um torneio MUST NOT impedir a coleta dos demais torneios
  daquela execução — mesmo princípio de isolamento de falha já aplicado por jogo
  individual (spec 001, FR-006), agora também por torneio.
- **FR-009**: A carga histórica de um torneio (FR-003) MUST ser idempotente —
  reexecutá-la, inclusive após uma interrupção parcial, MUST NOT duplicar jogos já
  processados com sucesso.

### Key Entities *(include if feature involves data)*

- **Torneio**: uma série/temporada específica da LBA (ex.: "Ouro 2026", "Prata 2025",
  "Bronze/Prata 2026"), identificada por um `tournament_id` da fonte; tem um status
  de ciclo de vida (em andamento, com coleta recorrente; ou encerrado, com carga
  histórica única) e uma ou mais fases.
- **Fase**: subdivisão de um torneio (ex.: "Classificação", "Playoffs"), cada uma com
  seu próprio conjunto de jogos; nem toda fase produz uma tabela de classificação
  (fases de chaveamento/bracket não produzem).
- **Time** e **Jogador**: já existiam na spec 001, agora escopados por torneio — o
  mesmo time/atleta em torneios diferentes é tratado como registros independentes,
  sem estatística compartilhada entre torneios.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: As cinco temporadas/séries (Ouro 2026, Prata/Bronze 2026, Ouro 2025,
  Prata 2025, Bronze 2025) estão disponíveis para consulta no dashboard, cada uma
  com dados corretos e completamente isolados das demais.
- **SC-002**: Para cada um dos três torneios de 2025, 100% dos jogos e súmulas de
  todas as fases publicados pela fonte estão persistidos após a execução da carga
  histórica, sem exigir nenhuma coleta recorrente adicional.
- **SC-003**: Trocar de torneio no seletor do dashboard nunca deixa dado do torneio
  anterior visível ou influenciando um cálculo do torneio recém-selecionado.
- **SC-004**: A coleta recorrente de Prata/Bronze 2026 atinge a mesma garantia de
  disponibilidade já validada para Ouro 2026 (spec 001, SC-001) — dados de uma
  rodada disponíveis até a segunda-feira seguinte.

## Assumptions

- Os identificadores (`tournament_id`, slugs `ouro2025`, `prata2025`, `bronze2025`,
  `bronze2026`, `ouro2026`) permanecem estáveis na fonte durante o desenvolvimento
  e uso desta feature.
- Prata/Bronze 2026 é, de fato, uma única série combinada na fonte (confirmado com o
  mantenedor em 2026-08-02) — diferente de 2025, que tinha Prata e Bronze como
  torneios distintos.
- Times e jogadores são entidades por torneio nesta versão — não há tentativa de
  unificar a identidade de um mesmo atleta ou time entre temporadas diferentes.
- A carga histórica das séries 2025 (FR-003) é disparada manualmente pelo
  mantenedor quando conveniente, não precisa de agendamento automático — mas deve
  ser segura para reexecutar (FR-009).
- Quando a fonte criar a fase de Playoffs para Ouro 2026 ou Prata/Bronze 2026 (ainda
  não existe no momento desta versão), ela passa a ser coletada pela mesma coleta
  recorrente, via configuração, sem exigir mudança de código.
- Esta versão não inclui nenhuma visão que compare ou combine múltiplos torneios ao
  mesmo tempo (ex.: comparar um jogador entre a temporada 2025 e 2026) — o seletor
  troca o contexto inteiro para um torneio por vez.

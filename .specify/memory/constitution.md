<!--
Sync Impact Report
Version change: N/A (unfilled template) → 1.0.0
Modified principles: none renamed — initial ratification, all seven principles newly defined
  - [PRINCIPLE_1_NAME] → I. Integridade dos Dados (Idempotência)
  - [PRINCIPLE_2_NAME] → II. Resiliência a Mudanças na Fonte e Coleta Responsável
  - [PRINCIPLE_3_NAME] → III. Separação de Responsabilidades entre Camadas
  - [PRINCIPLE_4_NAME] → IV. Preservação de Histórico
  - [PRINCIPLE_5_NAME] → V. Segurança de Credenciais
  - Added: VI. Simplicidade Pragmática
  - Added: VII. Rigor Estatístico em Métricas Derivadas
Added sections:
  - Restrições Técnicas e Operacionais (was [SECTION_2_NAME])
  - Fluxo de Desenvolvimento e Qualidade (was [SECTION_3_NAME])
Removed sections: none
Templates requiring follow-up review (not modified by this command):
  - .specify/templates/plan-template.md ⚠ Constitution Check gates should reference these 7 principles
  - .specify/templates/spec-template.md ⚠ specs that surface derived metrics should account for Principle VII (sample-size disclosure)
  - .specify/templates/tasks-template.md ⚠ task breakdown should reflect the 4-layer separation in Principle III
Deferred TODOs: none — all placeholders resolved with values derived from user input and repo context
-->

# LBA Data Constitution

## Core Principles

### I. Integridade dos Dados (Idempotência) (NON-NEGOTIABLE)

Toda rotina de ingestão MUST ser idempotente: reexecutar o coletor para o mesmo
período, rodada ou partida MUST produzir o mesmo estado final no banco, sem
duplicar registros e sem sobrescrever dados corretos com dados incorretos ou
incompletos. Cada entidade coletada (partida, jogador, estatística) MUST ser
identificada por uma chave natural estável vinda da fonte, usada em operações
de upsert; inserts que não verificam existência prévia são proibidos.
Reprocessamentos manuais (backfills, correções pontuais) MUST ser auditáveis —
deve ser possível saber quando um registro foi criado e quando foi atualizado
pela última vez.

Rationale: sem idempotência, falhas de rede, reexecuções manuais ou
re-agendamentos do coletor corrompem silenciosamente a base histórica. A partir
daí o dado deixa de ser confiável, o que invalida todo o trabalho de modelagem
e apresentação construído sobre ele.

### II. Resiliência a Mudanças na Fonte e Coleta Responsável

A API consumida é pública, não documentada oficialmente, e pode mudar sem
aviso prévio. O coletor MUST validar a estrutura da resposta antes de
persistir qualquer dado; campo esperado ausente, tipo de dado inesperado ou
payload incompleto MUST interromper o processamento daquele registro
específico e MUST gerar um log de erro explícito — nunca ser ignorado
silenciosamente, nunca ser preenchido com um valor default arbitrário para
"seguir em frente". Falhas parciais MUST permitir retomada sem violar o
Princípio I (sem perda e sem duplicação). O coletor MUST ser respeitoso com a
fonte: sem paralelismo agressivo, com intervalo mínimo obrigatório entre
requisições, respeitando o `robots.txt` do domínio e identificando-se com um
User-Agent apropriado. Uma mudança de schema detectada MUST resultar em um log
de nível erro (não apenas aviso), sinalizando a necessidade de intervenção
manual do mantenedor.

Rationale: como não existe contrato formal com a fonte, a única forma de
manter a confiabilidade do pipeline é presumir que ela vai quebrar em algum
momento e projetar o coletor para falhar de forma ruidosa, nunca para
"adivinhar" a estrutura e seguir em frente com dado errado.

### III. Separação de Responsabilidades entre Camadas

O projeto MUST manter quatro camadas desacopladas — Coleta, Armazenamento,
Modelagem, Apresentação —, cada uma testável de forma independente, sem exigir
que as demais estejam em execução. A comunicação entre camadas MUST ocorrer
por meio de contratos estáveis (schema do banco, views, ou uma API interna
bem definida), nunca por acesso a estruturas ou formatos internos de outra
camada — por exemplo, o dashboard não MUST fazer parsing do JSON bruto da
API, e a modelagem não MUST depender de como o coletor formata seus logs.
Cada camada MUST ter sua própria suíte de testes, executável isoladamente com
uso de fixtures/mocks das camadas vizinhas quando necessário.

Rationale: mantido por uma única pessoa, o projeto depende de conseguir
isolar e depurar uma camada de cada vez. Acoplamento entre camadas transforma
qualquer mudança pequena — uma coluna nova, um campo renomeado na fonte — em
um problema de sistema inteiro.

### IV. Preservação de Histórico

Nenhuma decisão de modelagem MUST descartar informação que impeça reconstruir
a evolução de uma métrica ao longo do tempo. Tabelas que representam um
estado (classificação, médias, rankings, índices calculados) MUST ser
complementadas por um registro histórico — snapshot por rodada/data, ou um
padrão equivalente a slowly-changing-dimension — mesmo quando o requisito
atual pede apenas "o estado mais recente". Operações que substituem um valor
anterior sem preservar esse valor anterior em algum lugar consultável são
proibidas em tabelas de fatos e em métricas derivadas.

Rationale: reconstruir um histórico já perdido é, na prática, impossível ou
caríssimo — exige reprocessar a fonte inteira, se ela ainda existir e ainda
tiver os dados antigos disponíveis, ou aceitar uma lacuna permanente. Gravar o
histórico desde o início custa pouco em comparação.

### V. Segurança de Credenciais

Chaves de API, strings de conexão, tokens e qualquer outro segredo MUST NUNCA
ser hardcoded no código-fonte nem commitados no repositório. Todo segredo
MUST ser lido via variáveis de ambiente (ou um cofre de segredos
equivalente), com um arquivo de exemplo (ex.: `.env.example`) documentando as
chaves esperadas sem conter valores reais. Arquivos com segredos reais (ex.:
`.env`) MUST constar no `.gitignore`.

Rationale: é o requisito de segurança de menor custo e maior retorno
disponível. Para um projeto sem equipe de segurança para reagir a incidentes,
o vazamento de uma credencial é um risco desproporcional ao esforço
necessário para evitá-lo.

### VI. Simplicidade Pragmática

A complexidade técnica do projeto MUST ser dimensionada para o volume de
dados real — uma liga amadora, algumas centenas de linhas por temporada —,
não para hipotéticos de escala (milhões de registros, alta concorrência,
múltiplos times de desenvolvimento) que não existem neste contexto.
Introduzir filas de mensagens, orquestradores distribuídos, arquiteturas de
microsserviços ou camadas de cache antes que exista uma necessidade concreta
e demonstrada é proibido. Simplicidade é uma escolha de engenharia
deliberada — justificada pelo volume real de dados e pela natureza de
mantenedor único do projeto — e não uma desculpa para pular os testes,
validações ou registros mínimos exigidos pelos demais princípios desta
constituição.

Rationale: complexidade não utilizada não é "preparo para o futuro", é custo
de manutenção pago hoje em troca de um benefício hipotético que talvez nunca
se materialize. Para um mantenedor único, cada componente extra é tempo
tirado da integridade, da resiliência e da correção dos dados.

### VII. Rigor Estatístico em Métricas Derivadas

Toda métrica derivada exposta no dashboard ou em relatórios — rankings,
índices de "impacto", tendências, médias móveis — MUST expor, junto ao
valor, o tamanho da amostra (número de jogos ou partidas) que a sustenta.
Comparações entre jogadores ou times MUST NUNCA ser apresentadas como
equivalentes quando baseadas em números de jogos muito diferentes, sem
alertar essa diferença de forma visível. Métricas calculadas sobre amostras
abaixo de um limiar mínimo definido pelo mantenedor MUST ser sinalizadas
visualmente como baixa confiança, em vez de ficarem indistinguíveis de
métricas calculadas sobre amostras robustas.

Rationale: numa liga amadora com poucos jogos por temporada, é fácil
apresentar ruído estatístico como sinal. Expor o tamanho da amostra é o que
impede o dashboard de sugerir conclusões fortes que os dados disponíveis não
sustentam.

## Restrições Técnicas e Operacionais

Toda mudança de schema no banco de dados MUST ser versionada por meio de
migrations explícitas e, sempre que tecnicamente viável, reversíveis — nunca
por alteração manual direta na estrutura de produção. Os logs do coletor MUST
ser estruturados o suficiente para responder, sem precisar reexecutar nada: o
que foi coletado, quando, e o que falhou e por quê. Dependências externas
(bibliotecas, serviços de terceiros) MUST ser mantidas no mínimo necessário
para cumprir os princípios acima; toda nova dependência MUST se justificar
explicitamente frente ao Princípio VI (Simplicidade Pragmática).

## Fluxo de Desenvolvimento e Qualidade

Antes de qualquer mudança ser considerada concluída, o mantenedor MUST rodar
a suíte de testes da(s) camada(s) afetada(s) e, quando a mudança tocar
ingestão ou modelagem, MUST confirmar manualmente que os Princípios I
(Integridade dos Dados) e IV (Preservação de Histórico) não foram violados.
Mudanças no coletor que alterem o tratamento de erros ou as expectativas
sobre o schema da fonte MUST vir acompanhadas de um teste que simule a falha
ou o formato inesperado, não apenas o caminho feliz. Por se tratar de um
projeto de mantenedor único, não há exigência de aprovação por terceiros,
mas todo `plan.md` ou `tasks.md` gerado para uma feature MUST citar
explicitamente qual(is) princípio(s) desta constituição a mudança afeta.

## Governança

Esta constituição prevalece sobre qualquer prática, atalho ou convenção
informal que esteja em conflito com ela. Emendas MUST ser feitas editando
este documento e registrando a razão da mudança no Sync Impact Report
gerado no topo do arquivo. O versionamento segue semver: MAJOR para remoção
ou redefinição incompatível de um princípio existente; MINOR para adição de
um novo princípio ou expansão material de um já existente; PATCH para
correções de redação e esclarecimentos que não mudam o sentido. Toda revisão
de plano (`/speckit-plan`) ou de tarefas (`/speckit-tasks`) MUST verificar
aderência a estes sete princípios antes de prosseguir; qualquer complexidade
adicional proposta MUST ser justificada explicitamente contra o Princípio VI.

**Version**: 1.0.0 | **Ratified**: 2026-07-31 | **Last Amended**: 2026-07-31

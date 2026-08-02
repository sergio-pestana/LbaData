# Quickstart: Validação da Plataforma LBA POA Ouro 2026

Guia para rodar e validar o pipeline ponta a ponta localmente. Detalhes de schema
em [data-model.md](./data-model.md); detalhes do contrato com a API externa em
[contracts/go-champs-api-dependency.md](./contracts/go-champs-api-dependency.md).

## Pré-requisitos

- Python 3.11+
- Um projeto Supabase (Postgres) criado, com host/usuário/senha disponíveis
- Variáveis de ambiente (nunca hardcoded — Princípio V; em variáveis separadas,
  não uma única URI, para evitar bugs de parsing quando a senha tem caracteres
  especiais como `@`):
  - `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`, `SUPABASE_DB_NAME`, `SUPABASE_DB_USER`, `SUPABASE_DB_PASSWORD`
  - `LBA_TOURNAMENT_ID` = `5bf23f0b-6768-46ec-bcc1-4cd698105413`
  - `LBA_PHASE_ID` = `ede46bb2-21ac-411b-b07f-b93269bebd37`
  - `COLLECTOR_REQUEST_INTERVAL_SECONDS` (default sugerido: `1.5`)
- Um arquivo `.env` local (gitignored) para desenvolvimento; em produção, as
  mesmas chaves como GitHub Actions Secrets

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m storage.migrations.apply   # cria teams/players/games/player_game_stats/
                                       # team_game_stats/standings_snapshot no Supabase
```

## Cenário 1 — Coleta contra fixtures (sem rede)

Prova que o parsing e o upsert funcionam de forma determinística, sem depender da
API real estar no ar.

```bash
pytest tests/contract/ tests/unit/
```

**Resultado esperado**: todos os testes passam usando os payloads salvos em
`tests/fixtures/`; nenhuma chamada de rede é feita.

## Cenário 2 — Coleta manual contra a API real (validação de integração)

Prova que os endpoints reais ainda respondem no formato assumido — a rede de
segurança contra mudanças silenciosas de schema (Princípio II).

```bash
pytest tests/integration/test_live_api.py -v
```

**Resultado esperado**: o teste roda contra a API real do go-champs e falha
ruidosamente (não silenciosamente) se qualquer campo essencial estiver ausente ou
com tipo inesperado.

## Cenário 3 — Execução completa de uma coleta de rodada

```bash
python -m collector.run --phase-id "$LBA_PHASE_ID"
```

**Resultado esperado**:
- Jogos novos da fase são inseridos; jogos já existentes com dado alterado são
  atualizados (`corrigido_em` populado), nunca duplicados.
- Uma nova linha por time é adicionada em `standings_snapshot` com o timestamp da
  execução.
- Se um jogo específico tiver payload incompleto/schema inesperado, ele é
  logado como erro e pulado — os demais jogos da rodada continuam sendo
  processados.

## Cenário 4 — Idempotência (critério de aceite do Princípio I)

```bash
python -m collector.run --phase-id "$LBA_PHASE_ID"
python -m collector.run --phase-id "$LBA_PHASE_ID"   # roda de novo, mesma rodada
```

**Resultado esperado**: a segunda execução não cria nenhuma linha duplicada em
`games`, `player_game_stats` ou `team_game_stats`. Uma nova linha é adicionada em
`standings_snapshot` (append-only por design), não uma duplicata no sentido de
dado incorreto.

## Cenário 5 — Dashboard local

```bash
streamlit run src/dashboard/app.py
```

**Resultado esperado** (critério de aceite do spec): após rodar o Cenário 3 com os
dados de um fim de semana, abrir o dashboard mostra esse fim de semana refletido em
todas as visões — panorama/classificação, estatísticas de jogadores, tendências,
impacto e utilização — cada métrica derivada exibindo o número de jogos que a
sustenta.

## Cenário 6 — Agendamento (validação manual do workflow)

```bash
gh workflow run collect.yml
```

**Resultado esperado**: o job roda a mesma rotina do Cenário 3 usando os Secrets do
GitHub Actions (nunca credenciais hardcoded), sem exigir intervenção manual.

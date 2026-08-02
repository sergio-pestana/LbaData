# Quickstart: Validar Múltiplos Torneios

Pré-requisitos: mesmo `.env` de 001 (credenciais Supabase), `.venv` com
`requirements.txt` instalado, migrations em dia.

## 1. Aplicar a migração nova

```bash
PYTHONPATH=src python -m storage.migrations.apply
```

Verificar que `teams`/`players` ganharam a coluna `tournament_id` e que as linhas
já existentes do Ouro 2026 foram preenchidas (não ficaram `NULL`):

```sql
SELECT tournament_id, count(*) FROM teams GROUP BY tournament_id;
SELECT tournament_id, count(*) FROM players GROUP BY tournament_id;
```

## 2. Carregar um torneio histórico (ex.: Bronze 2025 — o menor, bom para testar rápido)

```bash
PYTHONPATH=src python -m collector.run --torneio bronze2025
```

Esperado: coleta as duas fases (Classificação e Playoffs) de Bronze 2025;
`standings_snapshot` recebe linhas só da fase de Classificação; `games`/
`player_game_stats`/`team_game_stats` recebem linhas de ambas as fases, sem erro
por causa da ausência de classificação nos Playoffs (ver research.md #4).

Reexecutar o mesmo comando e confirmar que a contagem de linhas em `games` não
muda (idempotência, FR-009).

## 3. Rodar a coleta recorrente ampliada

```bash
PYTHONPATH=src python -m collector.run --modo recorrente
```

Esperado: processa Ouro 2026 e Prata/Bronze 2026 na mesma execução; se uma delas
falhar (ex.: API fora do ar), a outra ainda é processada (FR-008).

## 4. Validar o dashboard

```bash
PYTHONPATH=src streamlit run src/dashboard/app.py
```

- Confirmar que existe um seletor de torneio (não mais um `LBA_PHASE_ID` fixo de
  ambiente) listando os 5 torneios.
- Selecionar Bronze 2025 (carregado no passo 2): classificação, estatísticas de
  jogadores e gráficos de impacto/utilização devem mostrar só times/jogadores de
  Bronze 2025.
- Trocar para Ouro 2026: os dados de Bronze 2025 não devem aparecer em nenhuma
  tabela/gráfico (User Story 3/4).
- Se algum time/jogador jogou tanto em 2025 quanto em 2026 (mesmo nome), conferir
  que aparecem como entradas independentes em cada torneio, sem estatística somada
  entre os dois.

## 5. Testes automatizados

```bash
PYTHONPATH=src pytest tests/unit tests/contract
```

Deve incluir (novos nesta feature): teste de `collector/tournaments.py` (ids
únicos, todo torneio com pelo menos 1 fase), teste de `upsert_team`/`upsert_player`
com `tournament_id`, teste de `get_teams`/`get_players` isolando por torneio, e
teste de contrato para o payload de fase tipo `draw` (Playoffs) sendo
corretamente pulado na geração de standings em vez de levantar erro.

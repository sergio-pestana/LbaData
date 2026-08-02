# LBA POA — Plataforma de Acompanhamento e Análise

Coleta, armazena e apresenta dados de basquete da LBA POA (liga amadora de
Porto Alegre), publicados pela API pública do [go-champs](https://go-champs.com/lba-poa).
Cobre 5 torneios: Ouro 2026 e Prata/Bronze 2026 (temporadas em andamento,
coleta recorrente) e Ouro 2025, Prata 2025, Bronze 2025 (temporadas
encerradas, carga histórica única) — ver
`specs/002-add-series-2025-2026/contracts/tournament-registry.md` para os
ids exatos.

Arquitetura em 4 camadas desacopladas (`src/collector`, `src/storage`,
`src/modeling`, `src/dashboard` — ver `.specify/memory/constitution.md`,
Princípio III). Detalhes de decisão técnica ficam em
`specs/001-lba-poa-analytics/` e `specs/002-add-series-2025-2026/`
(`spec.md`, `plan.md`, `research.md`, `data-model.md`).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# crie um arquivo .env na raiz com:
#   SUPABASE_DB_HOST=...       (Session Pooler do Supabase)
#   SUPABASE_DB_PORT=...
#   SUPABASE_DB_NAME=...
#   SUPABASE_DB_USER=...
#   SUPABASE_DB_PASSWORD=...
```

Aplicar o schema (idempotente — seguro rodar de novo a qualquer momento):

```bash
PYTHONPATH=src python -m storage.migrations.apply
```

## Coleta

Três modos, todos via `python -m collector.run` (com `PYTHONPATH=src`):

- **`--modo recorrente`** — coleta todos os torneios com `modo="recorrente"`
  no registro (`src/collector/tournaments.py`: hoje Ouro 2026 e Prata/Bronze
  2026). É o modo usado pelo cron (`.github/workflows/collect.yml`).
- **`--torneio <slug>`** — coleta todas as fases de um único torneio do
  registro (ex.: `--torneio ouro2025`). Uso manual, para a carga histórica
  única das temporadas encerradas (slugs: `ouro2025`, `prata2025`,
  `bronze2025`).
- **`--phase-id <id> --tournament-id <id>`** (ou via env
  `LBA_PHASE_ID`/`LBA_TOURNAMENT_ID`) — override manual de uma fase avulsa,
  fora do registro. Uso pontual/depuração.

Todos os modos são idempotentes (Princípio I) — reexecutar não duplica nada.

```bash
PYTHONPATH=src python -m collector.run --modo recorrente
PYTHONPATH=src python -m collector.run --torneio bronze2025
```

## Dashboard

```bash
PYTHONPATH=src streamlit run src/dashboard/app.py
```

Um seletor de torneio na sidebar troca o contexto das 3 páginas (Visão
geral, Estatísticas de jogadores, Impacto e utilização) entre os 5 torneios
suportados.

## Testes

```bash
PYTHONPATH=src pytest tests/unit tests/contract
```

Testes de `tests/unit/storage` e `tests/unit/collector` rodam contra o
Supabase real configurado no `.env` (não há como testar upserts/`ON
CONFLICT` de forma fiel sem um Postgres de verdade) — usam ids de teste
reservados e limpam tudo ao final. `tests/integration/` é manual, roda
contra a API real do go-champs, e não entra na suíte padrão.

## Documentação

- `specs/001-lba-poa-analytics/` — spec original (torneio único, Ouro 2026).
- `specs/002-add-series-2025-2026/` — extensão para múltiplos torneios,
  incluindo o `quickstart.md` com um roteiro de validação manual passo a
  passo.
- `.specify/memory/constitution.md` — princípios de engenharia do projeto.

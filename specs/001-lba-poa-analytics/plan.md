# Implementation Plan: Plataforma de Acompanhamento e Análise — LBA POA Ouro 2026

**Branch**: `001-lba-poa-analytics` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-lba-poa-analytics/spec.md`

## Summary

Construir um pipeline de dados de ponta a ponta para a LBA POA (Ouro 2026): um
coletor Python que consulta a API pública (não documentada oficialmente) do
go-champs após cada rodada de fim de semana, persiste jogos e súmulas completas em
Supabase (Postgres) via upsert idempotente, mantém um esquema dimensional simples
que preserva histórico (incluindo snapshots de classificação por rodada), e expõe
tudo em um dashboard Streamlit local com gráficos Plotly. A coleta roda agendada via
GitHub Actions (cron sábado/domingo + salvaguarda de segunda de manhã), sem
autenticação de usuário nesta versão, e todas as métricas derivadas (rankings,
tendência, utilização, impacto) exibem o número de jogos que as sustenta.

## Technical Context

**Language/Version**: Python 3.11+ (única linguagem para coletor, modelagem e
dashboard)

**Primary Dependencies**: `requests` (cliente HTTP para a API go-champs);
`psycopg2` (acesso direto a Postgres/Supabase via SQL, incluindo `INSERT ... ON
CONFLICT` para upserts); `streamlit` + `plotly` (dashboard); `pandas` (manipulação
tabular na camada de modelagem); `python-dotenv` (carregar variáveis de ambiente
localmente); `pytest` (testes)

**Storage**: Supabase (Postgres gerenciado)

**Testing**: `pytest` com testes unitários e de contrato baseados em fixtures
(payloads JSON reais salvos de cada endpoint go-champs), sem chamadas à rede em CI;
um teste de integração separado (`tests/integration/`), executado manualmente, para
validar contra a API real

**Target Platform**: Linux (runner do GitHub Actions, para a coleta agendada);
qualquer SO local (para o dashboard, via `streamlit run`)

**Project Type**: Aplicação Python única em quatro pacotes desacoplados
(coletor, armazenamento, modelagem, dashboard) — sem split frontend/backend
tradicional, já que o Streamlit é a própria camada de apresentação lendo
diretamente do Supabase

**Performance Goals**: Não há meta de performance agressiva — volume de uma liga
amadora (algumas centenas de linhas por temporada); uma execução de coleta de
rodada deve completar em poucos minutos; navegação no dashboard deve responder em
menos de 1s para esse volume, sem necessidade de otimizações específicas

**Constraints**: Coleta sequencial (sem paralelismo agressivo) com intervalo
mínimo configurável entre requisições; respeito ao `robots.txt` do domínio;
credenciais somente via variáveis de ambiente/GitHub Secrets; sem dados em tempo
real; escopo restrito à temporada Ouro 2026

**Scale/Scope**: 1 temporada, ~10-14 times, algumas centenas de linhas de
estatística por jogador/jogo no total; uso individual; 1-2 execuções de coleta por
semana (fim de semana + salvaguarda de segunda)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Integridade dos Dados (Idempotência) | **PASS** — todo write em Supabase é `UPSERT` com o id externo do go-champs como chave de conflito (`ON CONFLICT ... DO UPDATE`); nenhum insert cego. Reprocessar uma rodada corrige, nunca duplica. |
| II. Resiliência a Mudanças na Fonte e Coleta Responsável | **PASS** — cliente HTTP simples (sem browser/Playwright), requisições sequenciais com intervalo mínimo configurável, checagem de `robots.txt` antes de coletar, parsing valida a estrutura da resposta e levanta erro explícito/logado por jogo específico em caso de campo ausente/tipo inesperado, sem interromper os demais jogos da rodada. |
| III. Separação de Responsabilidades entre Camadas | **PASS** — quatro pacotes (`collector/`, `storage/`, `modeling/`, `dashboard/`) comunicam-se por interfaces de função e pelo schema do banco, nunca por acesso a estruturas internas de outra camada; cada um testável isoladamente com fixtures/mocks (ver Project Structure). |
| IV. Preservação de Histórico | **PASS** — `player_game_stats`/`team_game_stats` são fatos por partida (nunca agregados destrutivamente); `standings_snapshot` grava uma linha nova por time a cada coleta, permitindo reconstruir a evolução da classificação; partidas canceladas recebem status, nunca são apagadas (FR-018). |
| V. Segurança de Credenciais | **PASS** — credenciais do Supabase via `.env` local (gitignored) e GitHub Actions Secrets em produção; nenhuma chave hardcoded. |
| VI. Simplicidade Pragmática | **PASS** — sem filas, orquestradores ou microsserviços; totais agregados da temporada são calculados sob demanda (view/query) em vez de uma tabela própria sincronizada manualmente, evitando uma fonte adicional de bugs para um volume de dados pequeno. |
| VII. Rigor Estatístico em Métricas Derivadas | **PASS** — toda função de modelagem que produz ranking/tendência/utilização/impacto retorna também a contagem de jogos por trás do valor; o dashboard exibe esse número ao lado de cada métrica (FR-013). |

Nenhuma violação — Complexity Tracking permanece vazio.

**Re-check pós Phase 1**: o desenho final em `data-model.md` (upserts por chave
externa, `standings_snapshot` append-only, sem tabela agregada duplicada) e o
contrato documentado em `contracts/go-champs-api-dependency.md` (validação
defensiva por endpoint) confirmam os sete PASS acima sem introduzir nenhuma nova
violação.

## Project Structure

### Documentation (this feature)

```text
specs/001-lba-poa-analytics/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
requirements.txt / .env.example / pytest.ini / README.md   # config e docs na raiz (Setup/Polish)

src/
├── collector/
│   ├── client.py         # cliente HTTP para a API go-champs (rate limit + robots.txt)
│   ├── parsers.py        # resposta bruta → registros validados; erro explícito se schema mudar
│   ├── run.py            # orquestra a coleta de uma rodada (fetch → valida → persiste via storage)
│   └── config.py         # tournament_id/phase_id e settings a partir de variáveis de ambiente
│
├── storage/
│   ├── supabase_client.py # conexão Postgres/Supabase a partir de variáveis de ambiente
│   ├── upserts.py          # upsert_team, upsert_player, upsert_game, upsert_player_game_stat,
│   │                       # upsert_team_game_stat, insert_standings_snapshot
│   ├── reads.py             # leituras usadas pela camada de modelagem
│   └── migrations/          # SQL do schema (teams, players, games, player_game_stats,
│                             # team_game_stats, standings_snapshot) com constraints de unicidade
│                             # nos ids externos do go-champs
│
├── modeling/
│   ├── standings.py         # classificação atual + evolução histórica (via standings_snapshot)
│   ├── leaderboards.py       # melhores jogadores por critério, por time e pela liga
│   ├── trends.py               # séries temporais por jogador/time (rodada a rodada)
│   ├── usage.py                 # índice de utilização: (arremessos_2pt_tentados + arremessos_3pt_tentados
│   │                              # + lances_livres_tentados + turnovers) / minutos_jogados (data-model.md)
│   ├── impact.py                 # índice de impacto: combinação normalizada de Eficiência + Plus/Minus
│   └── sample_size.py              # marcação de "baixa confiança" quando nº de jogos < limiar
│
└── dashboard/
    ├── app.py                   # entrypoint Streamlit (st.navigation com título/ícone por página)
    ├── theme.py                 # CSS/tema compartilhado + helpers de tabela
    └── pages/
        ├── 1_visao_geral.py       # jogos realizados/restantes, classificação atual
        ├── 2_estatisticas_jogadores.py  # ranking de times (total/média) + tabela completa de
        │                               # jogadores (todas as métricas, ordenável por header, filtro de time)
        └── 3_impacto_e_utilizacao.py # top 5 por métrica escolhida, total ou média
        # "Tendências" (evolução rodada a rodada) foi removida do dashboard após revisão
        # do usuário sobre o produto real — modeling/trends.py e seus testes continuam
        # implementados e passando, só não estão mais expostos nesta versão da UI.

tests/
├── fixtures/                   # payloads JSON reais salvos de cada endpoint go-champs
├── unit/
│   ├── collector/
│   ├── storage/
│   └── modeling/
├── contract/                    # valida o parsing de cada endpoint contra o payload salvo em fixtures/
└── integration/
    └── test_live_api.py           # execução manual contra a API real (não roda em CI por padrão)

.github/
└── workflows/
    └── collect.yml                # cron sáb/dom + salvaguarda segunda de manhã; usa Secrets do Supabase
```

**Structure Decision**: Repositório Python único com quatro pacotes desacoplados
(`collector`, `storage`, `modeling`, `dashboard`) mapeados 1:1 às quatro camadas
exigidas pelo Princípio III da constituição. Não há split frontend/backend
tradicional: o Streamlit já é a camada de apresentação, lendo dados diretamente do
Supabase através da camada de modelagem — sem necessidade de uma API própria, dado
o uso individual local nesta versão.

## Complexity Tracking

*Sem violações da Constitution Check — tabela não aplicável nesta versão.*

# Contrato: Registro de Torneios e Fases (LBA POA)

Ids confirmados contra a API real do go-champs em 2026-08-02 (ver research.md #1 e
#4 para como/por que foram validados). Este documento é a fonte de verdade para o
conteúdo de `collector/tournaments.py` — qualquer divergência entre os dois deve
ser tratada como bug de implementação, não como uma segunda versão dos dados.

| Torneio | slug | tournament_id | modo |
|---|---|---|---|
| Ouro 2026 | `ouro2026` | `5bf23f0b-6768-46ec-bcc1-4cd698105413` | recorrente (já em produção desde 001) |
| Prata/Bronze 2026 | `bronze2026` | `4cc1dacb-2619-48b8-8331-caa7103eefab` | recorrente (novo) |
| Ouro 2025 | `ouro2025` | `9fa9ecef-c361-4d82-9fd5-ae8f3919b011` | histórico (carga única) |
| Prata 2025 | `prata2025` | `e72d3f2f-d55e-48b1-b4df-6d0305588b96` | histórico (carga única) |
| Bronze 2025 | `bronze2025` | `354be508-1cc8-4deb-a42c-57abd2377fcd` | histórico (carga única) |

## Fases por torneio

| Torneio | Fase | phase_id | type (fonte) | gera_classificacao |
|---|---|---|---|---|
| Ouro 2026 | Temporada Regular | `ede46bb2-21ac-411b-b07f-b93269bebd37` | elimination | `True` |
| Prata/Bronze 2026 | Temporada Regular | `3cf0e777-d532-46e5-9b00-eefb59e9075a` | elimination | `True` |
| Ouro 2025 | Classificação | `7fc86b0f-36d6-4f8d-bb40-9e00a688b47e` | elimination | `True` |
| Ouro 2025 | Playoffs | `51de7c2b-0be8-4a50-bdee-0ed3f5bacd94` | draw | `False` |
| Prata 2025 | Classificação | `c2740a29-a81a-4eea-b962-c5d14921a36f` | elimination | `True` |
| Prata 2025 | Playoffs | `c5b71c3b-23be-4ef3-9a26-573ed634f16c` | draw | `False` |
| Bronze 2025 | Classificação | `c70b7fdd-96cd-4a8a-adcc-f94c439213f8` | elimination | `True` |
| Bronze 2025 | Playoffs | `08dd0f20-d69e-49cf-b77e-9c17fc985563` | draw | `False` |

## Como cada campo foi obtido

- `tournament_id`/slug: `GET /v1/tournaments?where[organization_slug]=lba-poa` —
  todos os 22 torneios históricos da liga; os 5 acima foram selecionados por nome
  (ver conversa de 2026-08-02).
- Fases de cada torneio: `GET /v1/tournaments/{tournament_id}` → campo `data.phases`
  (lista de `{id, name/title, type}`).
- `gera_classificacao`: `True` quando a fase é `type=elimination` **e**
  `GET /v1/phases/{phase_id}` retorna `eliminations` não-vazio; `False` quando
  `type=draw` (confirmado vazio em `eliminations`/`elimination_stats`, com um
  campo `draws` no lugar — estrutura de chaveamento, fora do escopo desta versão
  para gerar classificação).

## Garantias que este contrato assume da fonte (revalidar se o coletor começar a falhar)

- Os 5 `tournament_id` acima permanecem estáveis e resolvíveis via
  `GET /v1/tournaments/{tournament_id}` durante o desenvolvimento e uso desta
  feature.
- Times e jogadores continuam vindo embutidos em `data.teams`/`data.players` do
  payload de `/v1/tournaments/{tournament_id}` (não há endpoint `/teams`/`/players`
  separado) — é essa característica que sustenta a decisão de research.md #2 de não
  precisar de chave composta.
- Fases novas (ex.: Playoffs 2026, quando a fonte criar) precisam ser adicionadas
  manualmente a este contrato e a `collector/tournaments.py` — não há descoberta
  automática de fases nesta versão (Princípio VI; ver spec.md, Assumptions).

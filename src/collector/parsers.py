"""Parsers da API go-champs → registros validados prontos para persistência.

Princípio II da constituição: qualquer campo essencial ausente ou com tipo
inesperado levanta `UnexpectedPayloadShape` imediatamente — nunca é ignorado
silenciosamente nem substituído por um valor default arbitrário. Cada parser
valida apenas UM jogo/registro por vez, para que uma falha isolada não derrube
o processamento dos demais (ver `collector/run.py`, Camada 2).

Formatos confirmados contra payload real (ver research.md #4, #9, #10 e
contracts/go-champs-api-dependency.md) — não são suposições:
- `stats.*` de player-stats-logs vêm como strings; `minutes_played` está em
  SEGUNDOS.
- `stats.*` de team-stats-logs já vêm como números.
- `field_goals_*` = somente 2 pontos; `three_point_field_goals_*` é categoria
  separada (não inclui/exclui uma da outra por soma).
- A classificação de `/v1/phases/{phase_id}` vem em `eliminations[0].team_stats`,
  com valores indexados pelo `id` de `elimination_stats`, não por nome legível.
- Confirmado contra coleta real (Camada 2, 2026-07-31): a mesa da liga às vezes
  omite por completo a chave de um campo de CONTAGEM (rebotes, assistências,
  faltas, arremessos, turnovers) quando o valor seria zero, em vez de mandar
  `"0"` — em duas partidas reais, jogadores que claramente jogaram (minutos e
  pontos presentes) vieram sem `rebounds_offensive`/`assists`/etc. Campos
  centrais (`points`, `minutes_played`, `game_played`, `efficiency`,
  `plus_minus`) sempre estiveram presentes nos dois casos observados. Por
  decisão explícita do usuário: campos de contagem ausentes viram `0` com um
  aviso logado (não silencioso); campos centrais ausentes ou com tipo inválido
  continuam derrubando o jogo inteiro.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("collector.parsers")


class UnexpectedPayloadShape(Exception):
    """Levantado quando a resposta da API não tem a estrutura/tipo esperado.

    Carrega `context` (ex.: game_id) para que o chamador possa logar qual
    registro específico falhou sem interromper o processamento dos demais.
    """

    def __init__(self, message: str, *, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.context = context or {}


def _require(d: dict, key: str, *, context: dict[str, Any] | None = None) -> Any:
    if key not in d or d[key] is None:
        raise UnexpectedPayloadShape(f"Campo essencial ausente: '{key}'", context=context)
    return d[key]


def _as_float(value: Any, *, field_name: str, context: dict[str, Any] | None = None) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise UnexpectedPayloadShape(
            f"Campo '{field_name}' com tipo inesperado (esperava número, veio {value!r})",
            context=context,
        ) from exc


def _as_int(value: Any, *, field_name: str, context: dict[str, Any] | None = None) -> int:
    return int(round(_as_float(value, field_name=field_name, context=context)))


def _as_bool01(value: Any, *, field_name: str, context: dict[str, Any] | None = None) -> bool:
    return _as_int(value, field_name=field_name, context=context) == 1


# ---------------------------------------------------------------------------
# GET /v1/tournaments/{tournament_id}
# ---------------------------------------------------------------------------

def parse_tournament(payload: dict) -> dict:
    """Valida metadados do torneio e retorna {has_aggregated_player_stats, teams, players}."""
    data = _require(payload, "data")
    has_aggregated = _require(data, "has_aggregated_player_stats")
    if has_aggregated is not True:
        raise UnexpectedPayloadShape(
            f"Torneio não tem has_aggregated_player_stats=true (veio {has_aggregated!r}); "
            "catálogo de estatísticas por jogador pode não estar disponível."
        )
    teams = parse_teams(payload)
    players = parse_players(payload)
    return {
        "has_aggregated_player_stats": has_aggregated,
        "teams": teams,
        "players": players,
    }


def parse_teams(payload: dict) -> list[dict]:
    data = _require(payload, "data")
    raw_teams = _require(data, "teams")
    teams = []
    for raw in raw_teams:
        context = {"team_id": raw.get("id")}
        teams.append(
            {
                "id": _require(raw, "id", context=context),
                "nome": _require(raw, "name", context=context),
                "tri_code": _require(raw, "tri_code", context=context),
                "cor": raw.get("primary_color"),
            }
        )
    return teams


def parse_players(payload: dict) -> list[dict]:
    data = _require(payload, "data")
    raw_players = _require(data, "players")
    players = []
    for raw in raw_players:
        context = {"player_id": raw.get("id")}
        players.append(
            {
                "id": _require(raw, "id", context=context),
                "nome": _require(raw, "name", context=context),
                "team_id": _require(raw, "team_id", context=context),
                "numero_camisa": raw.get("shirt_number"),
            }
        )
    return players


# ---------------------------------------------------------------------------
# GET /v1/games?where[phase_id]={phase_id}
# ---------------------------------------------------------------------------

def parse_games(payload: dict, *, expected_phase_id: str) -> list[dict]:
    """Parseia a lista de jogos, revalidando localmente o phase_id de cada um
    (o filtro where[] da API não é confiável — ver research.md #3)."""
    raw_games = _require(payload, "data")
    games = []
    for raw in raw_games:
        context = {"game_id": raw.get("id")}
        game_id = _require(raw, "id", context=context)
        phase_id = _require(raw, "phase_id", context=context)
        if phase_id != expected_phase_id:
            raise UnexpectedPayloadShape(
                f"Jogo {game_id} retornado com phase_id={phase_id}, esperado {expected_phase_id} "
                "(filtro where[phase_id] da API não é confiável)",
                context=context,
            )
        home_team = _require(raw, "home_team", context=context)
        away_team = _require(raw, "away_team", context=context)
        games.append(
            {
                "id": game_id,
                "phase_id": phase_id,
                "rodada_data": raw.get("datetime"),
                "time_casa_id": _require(home_team, "id", context=context),
                "time_visitante_id": _require(away_team, "id", context=context),
                "placar_casa": raw.get("home_score"),
                "placar_visitante": raw.get("away_score"),
                "is_finished_raw": raw.get("is_finished"),
                "status": "processada",
            }
        )
    return games


# ---------------------------------------------------------------------------
# GET /v1/player-stats-logs?where[game_id]={game_id}
# ---------------------------------------------------------------------------

# Campos centrais: ausência ou tipo inválido derruba o jogo inteiro (Princípio II).
# Confirmados presentes nas duas súmulas reais com dados parciais observadas.
_CORE_PLAYER_STAT_FIELDS = (
    "points",
    "minutes_played",
    "game_played",
    "efficiency",
    "plus_minus",
)

# Campos de contagem: se ausentes, viram 0 com um WARNING logado (não
# silencioso) em vez de derrubar o jogo — decisão explícita do usuário após
# observar essa omissão em dados reais da mesa da liga.
_COUNT_PLAYER_STAT_FIELDS = (
    "rebounds_offensive",
    "rebounds_defensive",
    "assists",
    "steals",
    "blocks",
    "fouls_personal",
    "fouls_technical",
    "fouls_unsportsmanlike",
    "fouls_disqualifying",
    "fouls_disqualifying_fighting",
    "fouls_flagrant",
    "fouls_game_disqualifying",
    "field_goals_attempted",
    "field_goals_made",
    "three_point_field_goals_attempted",
    "three_point_field_goals_made",
    "free_throws_attempted",
    "free_throws_made",
    "turnovers",
)


def _count_field(stats: dict, field_name: str, *, context: dict[str, Any]) -> int:
    if field_name not in stats:
        logger.warning(
            "Campo de contagem '%s' ausente — tratado como 0 (contexto=%s)",
            field_name, context,
        )
        return 0
    return _as_int(stats[field_name], field_name=field_name, context=context)


def parse_player_stats_logs(payload: dict, *, expected_game_id: str) -> list[dict]:
    raw_rows = _require(payload, "data")
    rows = []
    for raw in raw_rows:
        context = {"game_id": raw.get("game_id"), "player_id": raw.get("player_id")}
        game_id = _require(raw, "game_id", context=context)
        if game_id != expected_game_id:
            raise UnexpectedPayloadShape(
                f"player-stats-log retornado com game_id={game_id}, esperado {expected_game_id}",
                context=context,
            )
        player_id = _require(raw, "player_id", context=context)
        team_id = _require(raw, "team_id", context=context)
        stats = _require(raw, "stats", context=context)
        for field_name in _CORE_PLAYER_STAT_FIELDS:
            _require(stats, field_name, context=context)

        jogou = _as_bool01(stats["game_played"], field_name="game_played", context=context)
        minutos_segundos = _as_float(stats["minutes_played"], field_name="minutes_played", context=context)

        rows.append(
            {
                "id": _require(raw, "id", context=context),
                "game_id": game_id,
                "player_id": player_id,
                "time_id_na_partida": team_id,
                "jogou": jogou,
                "minutos_jogados": (minutos_segundos / 60.0) if jogou else None,
                "pontos": _as_int(stats["points"], field_name="points", context=context),
                "rebotes_ofensivos": _count_field(stats, "rebounds_offensive", context=context),
                "rebotes_defensivos": _count_field(stats, "rebounds_defensive", context=context),
                "assistencias": _count_field(stats, "assists", context=context),
                "roubos": _count_field(stats, "steals", context=context),
                "tocos": _count_field(stats, "blocks", context=context),
                "faltas_pessoais": _count_field(stats, "fouls_personal", context=context),
                "faltas_tecnicas": _count_field(stats, "fouls_technical", context=context),
                "faltas_antidesportivas": _count_field(stats, "fouls_unsportsmanlike", context=context),
                "faltas_desqualificantes": _count_field(stats, "fouls_disqualifying", context=context),
                "faltas_desqualificantes_briga": _count_field(stats, "fouls_disqualifying_fighting", context=context),
                "faltas_flagrantes": _count_field(stats, "fouls_flagrant", context=context),
                "faltas_desqualificantes_jogo": _count_field(stats, "fouls_game_disqualifying", context=context),
                "arremessos_2pt_tentados": _count_field(stats, "field_goals_attempted", context=context),
                "arremessos_2pt_convertidos": _count_field(stats, "field_goals_made", context=context),
                "arremessos_3pt_tentados": _count_field(stats, "three_point_field_goals_attempted", context=context),
                "arremessos_3pt_convertidos": _count_field(stats, "three_point_field_goals_made", context=context),
                "lances_livres_tentados": _count_field(stats, "free_throws_attempted", context=context),
                "lances_livres_convertidos": _count_field(stats, "free_throws_made", context=context),
                "turnovers": _count_field(stats, "turnovers", context=context),
                "eficiencia": _as_float(stats["efficiency"], field_name="efficiency", context=context),
                "plus_minus": _as_int(stats["plus_minus"], field_name="plus_minus", context=context),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# GET /v1/team-stats-logs?where[game_id]={game_id}
# ---------------------------------------------------------------------------

_TEAM_STAT_FIELDS = (
    "wins",
    "losses",
    "points",
    "points_against",
    "points_balance",
    "fiba_group_points",
    "field_goals_attempted",
    "field_goals_made",
    "three_point_field_goals_attempted",
    "three_point_field_goals_made",
    "free_throws_attempted",
    "free_throws_made",
    "rebounds_offensive",
    "rebounds_defensive",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "fouls",
    "efficiency",
    "plus_minus",
)


def parse_team_stats_logs(payload: dict, *, expected_game_id: str) -> list[dict]:
    raw_rows = _require(payload, "data")
    rows = []
    for raw in raw_rows:
        context = {"game_id": raw.get("game_id"), "team_id": raw.get("team_id")}
        game_id = _require(raw, "game_id", context=context)
        if game_id != expected_game_id:
            raise UnexpectedPayloadShape(
                f"team-stats-log retornado com game_id={game_id}, esperado {expected_game_id}",
                context=context,
            )
        team_id = _require(raw, "team_id", context=context)
        stats = _require(raw, "stats", context=context)
        for field_name in _TEAM_STAT_FIELDS:
            _require(stats, field_name, context=context)

        rows.append(
            {
                "id": _require(raw, "id", context=context),
                "game_id": game_id,
                "team_id": team_id,
                "vitoria": _as_bool01(stats["wins"], field_name="wins", context=context),
                "saldo_pontos": _as_int(stats["points_balance"], field_name="points_balance", context=context),
                "fiba_group_points": _as_float(stats["fiba_group_points"], field_name="fiba_group_points", context=context),
                "pontos": _as_int(stats["points"], field_name="points", context=context),
                "pontos_sofridos": _as_int(stats["points_against"], field_name="points_against", context=context),
                "arremessos_2pt_tentados": _as_int(stats["field_goals_attempted"], field_name="field_goals_attempted", context=context),
                "arremessos_2pt_convertidos": _as_int(stats["field_goals_made"], field_name="field_goals_made", context=context),
                "arremessos_3pt_tentados": _as_int(stats["three_point_field_goals_attempted"], field_name="three_point_field_goals_attempted", context=context),
                "arremessos_3pt_convertidos": _as_int(stats["three_point_field_goals_made"], field_name="three_point_field_goals_made", context=context),
                "lances_livres_tentados": _as_int(stats["free_throws_attempted"], field_name="free_throws_attempted", context=context),
                "lances_livres_convertidos": _as_int(stats["free_throws_made"], field_name="free_throws_made", context=context),
                "rebotes_ofensivos": _as_int(stats["rebounds_offensive"], field_name="rebounds_offensive", context=context),
                "rebotes_defensivos": _as_int(stats["rebounds_defensive"], field_name="rebounds_defensive", context=context),
                "assistencias": _as_int(stats["assists"], field_name="assists", context=context),
                "roubos": _as_int(stats["steals"], field_name="steals", context=context),
                "tocos": _as_int(stats["blocks"], field_name="blocks", context=context),
                "turnovers": _as_int(stats["turnovers"], field_name="turnovers", context=context),
                "faltas": _as_int(stats["fouls"], field_name="fouls", context=context),
                "eficiencia": _as_float(stats["efficiency"], field_name="efficiency", context=context),
                "plus_minus": _as_int(stats["plus_minus"], field_name="plus_minus", context=context),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# GET /v1/phases/{phase_id}
# ---------------------------------------------------------------------------

# team_stat_source -> nome do campo em standings_snapshot; sempre preferindo a
# entrada com ranking_criteria="overall" quando o mesmo source aparece
# duplicado (ex.: points_balance também existe como critério "head_to_head").
_STANDINGS_FIELD_MAP = {
    "game_played": "jogos",
    "wins": "vitorias",
    "losses": "derrotas",
    "fiba_group_points": "pontos_fiba",
    "points_balance": "saldo_pontos",
}


def parse_phase_standings(payload: dict) -> list[dict]:
    """Extrai a classificação já ordenada pela plataforma.

    Estrutura real (ver research.md #9): os valores de cada time em
    `eliminations[0].team_stats[].stats` são indexados pelo `id` de
    `elimination_stats`, não por um nome legível — é preciso montar o mapa
    id -> team_stat_source (filtrando ranking_criteria="overall") antes de
    extrair jogos/vitórias/derrotas/saldo/pontos FIBA.
    """
    data = _require(payload, "data")
    elimination_stats = _require(data, "elimination_stats")
    eliminations = _require(data, "eliminations")
    if not eliminations:
        raise UnexpectedPayloadShape("'eliminations' veio vazio — sem classificação para extrair")

    id_to_field: dict[str, str] = {}
    for criterio in elimination_stats:
        source = criterio.get("team_stat_source")
        criterio_id = criterio.get("id")
        if source in _STANDINGS_FIELD_MAP and criterio.get("ranking_criteria") == "overall":
            id_to_field[criterio_id] = _STANDINGS_FIELD_MAP[source]

    missing_fields = set(_STANDINGS_FIELD_MAP.values()) - set(id_to_field.values())
    if missing_fields:
        raise UnexpectedPayloadShape(
            f"elimination_stats não tem os critérios 'overall' esperados: {sorted(missing_fields)}"
        )

    team_stats = _require(eliminations[0], "team_stats")
    rows = []
    for posicao, entry in enumerate(team_stats, start=1):
        context = {"team_id": entry.get("team_id"), "posicao": posicao}
        team_id = _require(entry, "team_id", context=context)
        raw_stats = _require(entry, "stats", context=context)

        row = {"posicao": posicao, "team_id": team_id}
        for criterio_id, field_name in id_to_field.items():
            if criterio_id not in raw_stats:
                raise UnexpectedPayloadShape(
                    f"Time {team_id} sem o critério de classificação '{field_name}' (id={criterio_id})",
                    context=context,
                )
            row[field_name] = _as_float(raw_stats[criterio_id], field_name=field_name, context=context)
        rows.append(row)

    return rows

"""Leituras usadas pela camada de modelagem (Camada 3).

Retornam listas de dicts simples — a camada de modelagem não precisa saber
nada sobre SQL/psycopg2 (Princípio III, separação de camadas). Em particular,
colunas `numeric` do Postgres voltam do psycopg2 como `decimal.Decimal`, não
`float` — convertidas aqui para `float` antes de sair da camada de
armazenamento, para que a modelagem possa somar/dividir esses valores livremente
sem precisar saber de onde vieram (achado real ao validar a Camada 3 contra o
Supabase, 2026-07-31).
"""

from __future__ import annotations

from decimal import Decimal

from psycopg2.extras import RealDictCursor

from storage.supabase_client import get_connection


def _normalize(row: dict) -> dict:
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


def _query(sql: str, params: tuple = (), conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [_normalize(dict(row)) for row in cur.fetchall()]
    finally:
        if owns_conn:
            conn.close()


def get_games(phase_id: str) -> list[dict]:
    return _query(
        "SELECT * FROM games WHERE phase_id = %s ORDER BY rodada_data, id",
        (phase_id,),
    )


def get_latest_standings_snapshot(phase_id: str) -> list[dict]:
    """Última linha de standings_snapshot por time (o snapshot mais recente da
    fase), ordenada por posição."""
    return _query(
        """
        SELECT DISTINCT ON (team_id) *
        FROM standings_snapshot
        WHERE phase_id = %s
        ORDER BY team_id, coletado_em DESC
        """,
        (phase_id,),
    )


def get_standings_history(phase_id: str, team_id: str | None = None) -> list[dict]:
    if team_id is not None:
        return _query(
            "SELECT * FROM standings_snapshot WHERE phase_id = %s AND team_id = %s ORDER BY coletado_em",
            (phase_id, team_id),
        )
    return _query(
        "SELECT * FROM standings_snapshot WHERE phase_id = %s ORDER BY coletado_em",
        (phase_id,),
    )


def get_player_game_stats(team_id: str | None = None) -> list[dict]:
    if team_id is not None:
        return _query(
            "SELECT * FROM player_game_stats WHERE time_id_na_partida = %s",
            (team_id,),
        )
    return _query("SELECT * FROM player_game_stats", ())


def get_teams() -> list[dict]:
    """Dimensão de times — usada pelo dashboard para mostrar nome/cor em vez
    do id externo cru."""
    return _query("SELECT * FROM teams ORDER BY nome", ())


def get_players() -> list[dict]:
    """Dimensão de jogadores — usada pelo dashboard para mostrar nome em vez
    do id externo cru."""
    return _query("SELECT * FROM players ORDER BY nome", ())


def get_team_game_stats(team_id: str | None = None) -> list[dict]:
    if team_id is not None:
        return _query(
            "SELECT * FROM team_game_stats WHERE team_id = %s",
            (team_id,),
        )
    return _query("SELECT * FROM team_game_stats", ())


def get_team_game_stats_series(team_id: str) -> list[dict]:
    """Estatísticas do time rodada a rodada, usadas por modeling/trends.py."""
    return _query(
        """
        SELECT tgs.*, g.rodada_data
        FROM team_game_stats tgs
        JOIN games g ON g.id = tgs.game_id
        WHERE tgs.team_id = %s AND g.status = 'processada'
        ORDER BY g.rodada_data
        """,
        (team_id,),
    )


def get_player_game_stats_series(player_id: str) -> list[dict]:
    """Estatísticas do jogador rodada a rodada (join com games para ordenar por
    data), usadas por modeling/trends.py."""
    return _query(
        """
        SELECT pgs.*, g.rodada_data
        FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        WHERE pgs.player_id = %s AND g.status = 'processada'
        ORDER BY g.rodada_data
        """,
        (player_id,),
    )

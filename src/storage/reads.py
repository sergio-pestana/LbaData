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


def get_games(phase_ids: list[str]) -> list[dict]:
    """`phase_ids`: uma ou mais fases de um mesmo torneio (um torneio pode ter
    Classificação + Playoffs — data-model.md) cujos jogos entram na mesma
    consulta."""
    return _query(
        "SELECT * FROM games WHERE phase_id = ANY(%s::uuid[]) ORDER BY rodada_data, id",
        (phase_ids,),
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


def get_player_game_stats(phase_ids: list[str], team_id: str | None = None) -> list[dict]:
    """`phase_ids` é obrigatório: antes desta feature esta função não filtrava
    por fase/torneio nenhum quando chamada sem `team_id`, retornando a tabela
    inteira — bug de isolamento corrigido aqui (research.md #3 de
    specs/002-add-series-2025-2026)."""
    if team_id is not None:
        return _query(
            """
            SELECT pgs.* FROM player_game_stats pgs
            JOIN games g ON g.id = pgs.game_id
            WHERE g.phase_id = ANY(%s::uuid[]) AND pgs.time_id_na_partida = %s
            """,
            (phase_ids, team_id),
        )
    return _query(
        """
        SELECT pgs.* FROM player_game_stats pgs
        JOIN games g ON g.id = pgs.game_id
        WHERE g.phase_id = ANY(%s::uuid[])
        """,
        (phase_ids,),
    )


def get_teams(tournament_id: str) -> list[dict]:
    """Dimensão de times de um único torneio — usada pelo dashboard para
    mostrar nome/cor em vez do id externo cru. `tournament_id` é obrigatório
    (não opcional) para que seja estruturalmente impossível esquecer o
    isolamento entre torneios (data-model.md, User Story 4)."""
    return _query(
        "SELECT * FROM teams WHERE tournament_id = %s ORDER BY nome",
        (tournament_id,),
    )


def get_players(tournament_id: str) -> list[dict]:
    """Dimensão de jogadores de um único torneio — mesma regra de get_teams."""
    return _query(
        "SELECT * FROM players WHERE tournament_id = %s ORDER BY nome",
        (tournament_id,),
    )


def get_team_game_stats(phase_ids: list[str], team_id: str | None = None) -> list[dict]:
    """Mesma correção de isolamento de `get_player_game_stats` (research.md #3)."""
    if team_id is not None:
        return _query(
            """
            SELECT tgs.* FROM team_game_stats tgs
            JOIN games g ON g.id = tgs.game_id
            WHERE g.phase_id = ANY(%s::uuid[]) AND tgs.team_id = %s
            """,
            (phase_ids, team_id),
        )
    return _query(
        """
        SELECT tgs.* FROM team_game_stats tgs
        JOIN games g ON g.id = tgs.game_id
        WHERE g.phase_id = ANY(%s::uuid[])
        """,
        (phase_ids,),
    )


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

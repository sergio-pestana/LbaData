"""Upserts idempotentes — Princípio I da constituição.

Todo write usa `ON CONFLICT (id) DO UPDATE`, nunca um INSERT cego. Duas
variantes:

- `_touch_upsert`: para dimensões (teams, players) — atualiza incondicionalmente
  a cada chamada, inclusive `atualizado_em` (per data-model.md: "atualizado a
  cada upsert").
- `_correction_upsert`: para fatos por partida (games, player_game_stats,
  team_game_stats) — só atualiza a linha (e só bump `corrigido_em`) quando algum
  campo rastreado realmente mudou; se nada mudou, a linha existente fica
  intocada, inclusive `corrigido_em` antigo (Princípio I / FR-005: correção
  auditável, não uma reescrita cega a cada coleta).

Cada função aceita uma conexão opcional (`conn`): uma coleta de rodada inteira
(`collector/run.py`) processa centenas de linhas em sequência, e abrir uma
conexão nova por linha custaria um handshake TLS a cada chamada através do
pooler — lento sem necessidade. Quando nenhuma conexão é passada (uso avulso,
ex.: testes), a função abre e fecha a sua própria, como antes.
"""

from __future__ import annotations

from typing import Any

import psycopg2

from storage.supabase_client import get_connection


def _touch_upsert(table: str, row: dict[str, Any], conn=None) -> None:
    columns = list(row.keys())
    col_list = ", ".join(columns)
    placeholders = ", ".join(f"%({c})s" for c in columns)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id")

    sql = f"""
        INSERT INTO {table} ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET
            {update_set},
            atualizado_em = now()
    """

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, row)
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


def _correction_upsert(table: str, row: dict[str, Any], conn=None) -> None:
    columns = list(row.keys())
    col_list = ", ".join(columns)
    placeholders = ", ".join(f"%({c})s" for c in columns)
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id")
    changed_check = " OR ".join(
        f"{table}.{c} IS DISTINCT FROM EXCLUDED.{c}" for c in columns if c != "id"
    )

    sql = f"""
        INSERT INTO {table} ({col_list})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET
            {update_set},
            corrigido_em = now()
        WHERE {changed_check}
    """

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, row)
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


def upsert_team(
    team: dict[str, Any], tournament_id: str, conn: psycopg2.extensions.connection | None = None
) -> None:
    _touch_upsert("teams", {**team, "tournament_id": tournament_id}, conn=conn)


def upsert_player(
    player: dict[str, Any], tournament_id: str, conn: psycopg2.extensions.connection | None = None
) -> None:
    _touch_upsert("players", {**player, "tournament_id": tournament_id}, conn=conn)


def upsert_game(game: dict[str, Any], conn: psycopg2.extensions.connection | None = None) -> None:
    _correction_upsert("games", game, conn=conn)


def upsert_player_game_stat(row: dict[str, Any], conn: psycopg2.extensions.connection | None = None) -> None:
    _correction_upsert("player_game_stats", row, conn=conn)


def upsert_team_game_stat(row: dict[str, Any], conn: psycopg2.extensions.connection | None = None) -> None:
    _correction_upsert("team_game_stats", row, conn=conn)


def insert_standings_snapshot(
    rows: list[dict[str, Any]], conn: psycopg2.extensions.connection | None = None
) -> None:
    """Append-only: sempre INSERT, nunca upsert — cada coleta grava uma linha
    nova por time (Princípio IV, preservação de histórico)."""
    if not rows:
        return

    columns = [c for c in rows[0].keys() if c != "id"]
    col_list = ", ".join(columns)
    placeholders = ", ".join(f"%({c})s" for c in columns)
    sql = f"INSERT INTO standings_snapshot ({col_list}) VALUES ({placeholders})"

    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
    finally:
        if owns_conn:
            conn.close()

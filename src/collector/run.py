"""Orquestra a coleta de uma rodada: busca jogos + súmulas da API real,
valida, e persiste no Supabase de forma idempotente (Princípio I).

Uma única conexão é aberta e reutilizada durante toda a execução — abrir uma
conexão nova por upsert seria centenas de handshakes TLS através do pooler
para uma única rodada.

Falhas de schema em um jogo específico são logadas e não interrompem os
demais (Princípio II, FR-006). Um jogo que estava `processada` e sumiu da
resposta da fase é marcado `cancelada`, nunca excluído (Princípio IV, FR-018).
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor

from collector.client import GoChampsClient
from collector.config import CollectorConfig
from collector.parsers import (
    UnexpectedPayloadShape,
    parse_games,
    parse_phase_standings,
    parse_player_stats_logs,
    parse_team_stats_logs,
    parse_tournament,
)
from storage.supabase_client import get_connection
from storage.upserts import (
    insert_standings_snapshot,
    upsert_game,
    upsert_player,
    upsert_player_game_stat,
    upsert_team,
    upsert_team_game_stat,
)

logger = logging.getLogger("collector.run")


def _fetch_existing_processed_game_ids(conn, phase_id: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM games WHERE phase_id = %s AND status = 'processada'",
            (phase_id,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def _fetch_game_row(conn, game_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM games WHERE id = %s", (game_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def mark_missing_games_as_cancelled(conn, phase_id: str, current_game_ids: set[str]) -> None:
    """FR-018: um jogo antes processado que sumiu da resposta atual da fase é
    marcado como cancelada, nunca excluído (Princípio IV)."""
    existing = _fetch_existing_processed_game_ids(conn, phase_id)
    missing = existing - current_game_ids
    for game_id in missing:
        row = _fetch_game_row(conn, game_id)
        if row is None:
            continue
        row = {k: v for k, v in row.items() if k not in ("criado_em", "corrigido_em")}
        row["status"] = "cancelada"
        upsert_game(row, conn=conn)
        logger.warning(
            "Jogo %s não veio mais na resposta da fase %s — marcado como cancelada",
            game_id, phase_id,
        )


def collect_round(
    phase_id: str,
    tournament_id: str,
    client: GoChampsClient | None = None,
    *,
    gera_classificacao: bool = True,
) -> None:
    """`gera_classificacao=False` pula a etapa de classificação por completo —
    usado para fases tipo chaveamento/bracket (ex.: Playoffs) que a fonte não
    expõe no formato `eliminations` (research.md #4 de
    specs/002-add-series-2025-2026). A distinção fica explícita na chamada,
    em vez de tentar buscar a classificação e engolir o erro esperado."""
    client = client or GoChampsClient()
    conn = get_connection()

    try:
        tournament_payload = client.get(f"/v1/tournaments/{tournament_id}")
        tournament = parse_tournament(tournament_payload)
        for team in tournament["teams"]:
            upsert_team(team, tournament_id, conn=conn)
        for player in tournament["players"]:
            upsert_player(player, tournament_id, conn=conn)
        logger.info(
            "Roster sincronizado: %d times, %d jogadores",
            len(tournament["teams"]), len(tournament["players"]),
        )

        games_payload = client.get("/v1/games", params={"where[phase_id]": phase_id})
        games = parse_games(games_payload, expected_phase_id=phase_id)

        for game in games:
            upsert_game(game, conn=conn)

            if not game["is_finished_raw"]:
                continue

            try:
                player_payload = client.get(
                    "/v1/player-stats-logs", params={"where[game_id]": game["id"]}
                )
                player_rows = parse_player_stats_logs(player_payload, expected_game_id=game["id"])
                for row in player_rows:
                    upsert_player_game_stat(row, conn=conn)

                team_payload = client.get(
                    "/v1/team-stats-logs", params={"where[game_id]": game["id"]}
                )
                team_rows = parse_team_stats_logs(team_payload, expected_game_id=game["id"])
                for row in team_rows:
                    upsert_team_game_stat(row, conn=conn)
            except UnexpectedPayloadShape as exc:
                logger.error(
                    "Falha ao processar súmula do jogo %s: %s (contexto=%s)",
                    game["id"], exc, exc.context,
                )
                continue

        mark_missing_games_as_cancelled(conn, phase_id, {g["id"] for g in games})

        if not gera_classificacao:
            logger.info(
                "Fase %s marcada como sem classificação (ex.: chaveamento/bracket) — "
                "pulando snapshot de classificação de propósito",
                phase_id,
            )
        else:
            try:
                standings_payload = client.get(f"/v1/phases/{phase_id}")
                standings_rows = parse_phase_standings(standings_payload)
                coletado_em = datetime.now(timezone.utc)
                snapshot_rows = [
                    {
                        "coletado_em": coletado_em,
                        "phase_id": phase_id,
                        "team_id": row["team_id"],
                        "posicao": int(row["posicao"]),
                        "jogos": int(row["jogos"]),
                        "vitorias": int(row["vitorias"]),
                        "derrotas": int(row["derrotas"]),
                        "saldo_pontos": int(row["saldo_pontos"]),
                        "pontos_fiba": row["pontos_fiba"],
                    }
                    for row in standings_rows
                ]
                insert_standings_snapshot(snapshot_rows, conn=conn)
                logger.info("Snapshot de classificação gravado (%d times)", len(snapshot_rows))
            except UnexpectedPayloadShape as exc:
                logger.error("Falha ao processar classificação da fase %s: %s", phase_id, exc)

        logger.info("Coleta da fase %s concluída: %d jogos processados", phase_id, len(games))
    finally:
        conn.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    arg_parser = argparse.ArgumentParser(description="Coleta uma rodada da LBA POA Ouro 2026")
    arg_parser.add_argument("--phase-id", dest="phase_id", default=None)
    arg_parser.add_argument("--tournament-id", dest="tournament_id", default=None)
    args = arg_parser.parse_args()

    config = CollectorConfig.from_env()
    phase_id = args.phase_id or config.phase_id
    tournament_id = args.tournament_id or config.tournament_id
    client = GoChampsClient(min_interval_seconds=config.request_interval_seconds)

    logger.info("Iniciando coleta da fase %s", phase_id)
    collect_round(phase_id, tournament_id, client=client)


if __name__ == "__main__":
    main()

"""Aplica os arquivos .sql de src/storage/migrations/ em ordem alfabética.

Idempotente: cada migration usa CREATE TABLE IF NOT EXISTS / CREATE INDEX IF
NOT EXISTS, então rodar de novo não falha nem duplica nada.

Uso:
    python -m storage.migrations.apply
"""

from __future__ import annotations

from pathlib import Path

from storage.supabase_client import get_connection

MIGRATIONS_DIR = Path(__file__).resolve().parent


def apply_all() -> None:
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("Nenhum arquivo .sql encontrado em", MIGRATIONS_DIR)
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for sql_file in sql_files:
                print(f"Aplicando {sql_file.name}...")
                cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
        print(f"{len(sql_files)} migration(s) aplicadas com sucesso.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    apply_all()

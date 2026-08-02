"""Conexão Postgres/Supabase a partir de variáveis de ambiente separadas.

Princípio V (segurança de credenciais): nenhuma credencial hardcoded. Usamos
host/porta/banco/usuário/senha em variáveis distintas — não uma única URI —
porque uma URI quebra silenciosamente quando a senha contém caracteres
especiais como "@" (achado real, ver research.md #1). Conectar sempre via
Session Pooler do Supabase, não conexão direta: a conexão direta só tem
endereço IPv6 no plano free, inacessível em redes sem rota IPv6
(ver research.md #11).
"""

from __future__ import annotations

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


class MissingConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingConfigError(
            f"Variável de ambiente obrigatória '{name}' não definida. Veja .env.example."
        )
    return value


def get_connection() -> psycopg2.extensions.connection:
    """Abre uma nova conexão Postgres. O volume do projeto (Princípio VI) não
    justifica um pool de conexões — cada chamador fecha a conexão que abrir."""
    return psycopg2.connect(
        host=_require_env("SUPABASE_DB_HOST"),
        port=os.environ.get("SUPABASE_DB_PORT", "5432"),
        dbname=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=_require_env("SUPABASE_DB_USER"),
        password=_require_env("SUPABASE_DB_PASSWORD"),
        connect_timeout=10,
    )

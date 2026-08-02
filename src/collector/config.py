"""Configuração do coletor a partir de variáveis de ambiente — Princípio V
(segredos e parâmetros nunca hardcoded no código)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class MissingConfigError(RuntimeError):
    """Levantado quando uma variável de ambiente obrigatória não está definida."""


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingConfigError(
            f"Variável de ambiente obrigatória '{name}' não definida. "
            f"Veja .env.example."
        )
    return value


@dataclass(frozen=True)
class CollectorConfig:
    tournament_id: str
    phase_id: str
    request_interval_seconds: float

    @classmethod
    def from_env(cls) -> "CollectorConfig":
        return cls(
            tournament_id=_require_env("LBA_TOURNAMENT_ID"),
            phase_id=_require_env("LBA_PHASE_ID"),
            request_interval_seconds=float(
                os.environ.get("COLLECTOR_REQUEST_INTERVAL_SECONDS", "1.5")
            ),
        )

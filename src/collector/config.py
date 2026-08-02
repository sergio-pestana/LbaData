"""Configuração do coletor a partir de variáveis de ambiente — Princípio V
(segredos e parâmetros nunca hardcoded no código)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class CollectorConfig:
    tournament_id: str | None
    phase_id: str | None
    request_interval_seconds: float

    @classmethod
    def from_env(cls) -> "CollectorConfig":
        """`LBA_TOURNAMENT_ID`/`LBA_PHASE_ID` agora são opcionais: só fazem
        sentido no modo de override manual de `collector.run` (uma fase
        avulsa); os modos `--torneio`/`--modo recorrente` resolvem tudo a
        partir de `collector/tournaments.py`, sem precisar de env var nenhuma
        (feature 002 — múltiplos torneios)."""
        return cls(
            tournament_id=os.environ.get("LBA_TOURNAMENT_ID"),
            phase_id=os.environ.get("LBA_PHASE_ID"),
            request_interval_seconds=float(
                os.environ.get("COLLECTOR_REQUEST_INTERVAL_SECONDS", "1.5")
            ),
        )

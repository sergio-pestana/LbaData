"""Marcação de baixa confiança por amostra pequena — Princípio VII da
constituição: toda métrica derivada deve deixar explícito o nº de jogos por
trás do valor, para não sugerir conclusões fortes a partir de poucos jogos.
"""

from __future__ import annotations

from typing import Any

LIMIAR_PADRAO = 3  # ver research.md #6


def flag_low_confidence(valor: Any, num_jogos: int, limiar: int = LIMIAR_PADRAO) -> dict:
    """Envolve um valor calculado com a contagem de jogos que o sustenta e uma
    marca de baixa confiança quando `num_jogos < limiar`."""
    return {
        "valor": valor,
        "num_jogos": num_jogos,
        "baixa_confianca": num_jogos < limiar,
    }

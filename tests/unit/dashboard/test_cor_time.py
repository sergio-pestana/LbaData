"""cor_time: fallback determinístico para times sem cor ou com cor
branca/quase-branca demais para um fundo branco."""

from __future__ import annotations

from dashboard.theme import cor_time


def test_returns_source_color_when_visible():
    assert cor_time({"id": "x", "cor": "#1f77b4"}) == "#1f77b4"


def test_falls_back_when_color_is_none():
    cor = cor_time({"id": "time-sem-cor", "cor": None})
    assert cor != "#888888"
    assert cor.startswith("#")


def test_falls_back_when_color_is_white():
    cor = cor_time({"id": "time-branco", "cor": "#ffffff"})
    assert cor.lower() != "#ffffff"


def test_fallback_is_stable_for_the_same_team_id():
    a1 = cor_time({"id": "mesmo-id", "cor": None})
    a2 = cor_time({"id": "mesmo-id", "cor": None})
    assert a1 == a2


def test_none_team_returns_generic_gray():
    assert cor_time(None) == "#888888"

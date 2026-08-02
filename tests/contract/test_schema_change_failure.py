"""Princípio II: qualquer campo essencial ausente ou com tipo inesperado MUST
levantar UnexpectedPayloadShape de forma explícita — nunca ser ignorado
silenciosamente nem substituído por um valor default arbitrário."""

import copy

import pytest

from collector.parsers import (
    UnexpectedPayloadShape,
    parse_games,
    parse_player_stats_logs,
    parse_team_stats_logs,
    parse_tournament,
)


def test_tournament_missing_essential_field_raises():
    payload = {"data": {"has_aggregated_player_stats": True, "players": []}}  # sem "teams"
    with pytest.raises(UnexpectedPayloadShape):
        parse_tournament(payload)


def test_games_missing_home_team_raises(games_phase_payload, known_phase_id):
    payload = copy.deepcopy(games_phase_payload)
    del payload["data"][0]["home_team"]

    with pytest.raises(UnexpectedPayloadShape):
        parse_games(payload, expected_phase_id=known_phase_id)


def test_player_stats_missing_essential_stat_field_raises(player_stats_logs_payload, known_game_id):
    payload = copy.deepcopy(player_stats_logs_payload)
    del payload["data"][0]["stats"]["points"]

    with pytest.raises(UnexpectedPayloadShape):
        parse_player_stats_logs(payload, expected_game_id=known_game_id)


def test_player_stats_unexpected_type_raises(player_stats_logs_payload, known_game_id):
    payload = copy.deepcopy(player_stats_logs_payload)
    payload["data"][0]["stats"]["points"] = "não-é-um-número"

    with pytest.raises(UnexpectedPayloadShape):
        parse_player_stats_logs(payload, expected_game_id=known_game_id)


def test_team_stats_missing_essential_field_raises(team_stats_logs_payload, known_game_id):
    payload = copy.deepcopy(team_stats_logs_payload)
    del payload["data"][0]["stats"]["wins"]

    with pytest.raises(UnexpectedPayloadShape):
        parse_team_stats_logs(payload, expected_game_id=known_game_id)


def test_only_the_malformed_row_needs_to_fail_not_the_whole_batch(player_stats_logs_payload, known_game_id):
    """Uma linha malformada MUST interromper só aquele registro — o chamador
    (collector/run.py, Camada 2) é quem decide continuar com os demais jogos.
    Aqui confirmamos que o parser levanta a exceção com contexto suficiente
    (game_id/player_id) para o chamador logar o registro específico afetado."""
    payload = copy.deepcopy(player_stats_logs_payload)
    broken_player_id = payload["data"][5]["player_id"]
    del payload["data"][5]["stats"]["efficiency"]

    with pytest.raises(UnexpectedPayloadShape) as exc_info:
        parse_player_stats_logs(payload, expected_game_id=known_game_id)

    assert exc_info.value.context.get("player_id") == broken_player_id

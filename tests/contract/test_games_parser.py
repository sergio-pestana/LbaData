import pytest

from collector.parsers import parse_games, UnexpectedPayloadShape


def test_parses_games_and_revalidates_phase_id(games_phase_payload, known_phase_id):
    games = parse_games(games_phase_payload, expected_phase_id=known_phase_id)

    assert len(games) == 22
    assert all(g["phase_id"] == known_phase_id for g in games)
    assert all(g["status"] == "processada" for g in games)


def test_game_has_required_fields(games_phase_payload, known_phase_id):
    games = parse_games(games_phase_payload, expected_phase_id=known_phase_id)
    game = games[0]

    assert game["id"]
    assert game["time_casa_id"]
    assert game["time_visitante_id"]


def test_raises_when_phase_id_does_not_match_expected(games_phase_payload):
    with pytest.raises(UnexpectedPayloadShape):
        parse_games(games_phase_payload, expected_phase_id="phase-id-diferente-do-esperado")

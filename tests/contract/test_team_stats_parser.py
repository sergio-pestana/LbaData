from collector.parsers import parse_team_stats_logs


def test_parses_one_row_per_team(team_stats_logs_payload, known_game_id):
    rows = parse_team_stats_logs(team_stats_logs_payload, expected_game_id=known_game_id)

    assert len(rows) == 2
    assert {r["vitoria"] for r in rows} == {True, False}


def test_points_and_points_against_are_symmetric_between_the_two_teams(team_stats_logs_payload, known_game_id):
    rows = parse_team_stats_logs(team_stats_logs_payload, expected_game_id=known_game_id)
    a, b = rows

    assert a["pontos"] == b["pontos_sofridos"]
    assert b["pontos"] == a["pontos_sofridos"]
    assert a["saldo_pontos"] == -b["saldo_pontos"]


def test_team_stats_values_are_already_numeric_not_strings(team_stats_logs_payload, known_game_id):
    rows = parse_team_stats_logs(team_stats_logs_payload, expected_game_id=known_game_id)
    row = rows[0]

    assert isinstance(row["pontos"], int)
    assert isinstance(row["vitoria"], bool)

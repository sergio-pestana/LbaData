from collector.parsers import parse_tournament, UnexpectedPayloadShape


def test_parses_tournament_with_aggregated_stats(tournament_payload):
    result = parse_tournament(tournament_payload)

    assert result["has_aggregated_player_stats"] is True
    assert len(result["teams"]) == 8
    assert len(result["players"]) == 126


def test_parsed_team_has_required_fields(tournament_payload):
    result = parse_tournament(tournament_payload)
    team = result["teams"][0]

    assert team["id"]
    assert team["nome"]
    assert team["tri_code"]


def test_parsed_player_has_required_fields(tournament_payload):
    result = parse_tournament(tournament_payload)
    player = result["players"][0]

    assert player["id"]
    assert player["nome"]
    assert player["team_id"]


def test_raises_when_aggregated_stats_flag_is_false():
    payload = {"data": {"has_aggregated_player_stats": False, "teams": [], "players": []}}

    try:
        parse_tournament(payload)
        assert False, "deveria ter levantado UnexpectedPayloadShape"
    except UnexpectedPayloadShape:
        pass

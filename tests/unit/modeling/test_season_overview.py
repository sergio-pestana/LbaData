from modeling.standings import season_overview


def _game(status="processada", is_finished_raw=True):
    return {"status": status, "is_finished_raw": is_finished_raw}


def test_counts_played_and_remaining_games():
    games = [
        _game(is_finished_raw=True),
        _game(is_finished_raw=True),
        _game(is_finished_raw=False),
    ]
    result = season_overview(games)
    assert result == {"jogos_realizados": 2, "jogos_restantes": 1}


def test_cancelled_games_are_excluded_from_both_counts():
    games = [
        _game(is_finished_raw=True),
        _game(status="cancelada", is_finished_raw=True),
        _game(status="cancelada", is_finished_raw=False),
    ]
    result = season_overview(games)
    assert result == {"jogos_realizados": 1, "jogos_restantes": 0}


def test_empty_season():
    assert season_overview([]) == {"jogos_realizados": 0, "jogos_restantes": 0}

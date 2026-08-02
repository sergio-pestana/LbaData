from modeling.impact import impact_index


def _row(player_id, eficiencia, plus_minus, jogou=True):
    return {"player_id": player_id, "eficiencia": eficiencia, "plus_minus": plus_minus, "jogou": jogou}


def test_player_with_higher_efficiency_and_plus_minus_ranks_first():
    rows = [
        _row("a", eficiencia=20, plus_minus=10),
        _row("b", eficiencia=5, plus_minus=-5),
        _row("c", eficiencia=10, plus_minus=0),
    ]
    ranking = impact_index(rows)

    assert ranking[0]["player_id"] == "a"
    assert ranking[-1]["player_id"] == "b"


def test_averages_across_multiple_games_before_scoring():
    rows = [
        _row("a", eficiencia=10, plus_minus=0),
        _row("a", eficiencia=30, plus_minus=0),  # média 20
        _row("b", eficiencia=20, plus_minus=0),  # média 20 também
    ]
    ranking = impact_index(rows)

    a = next(r for r in ranking if r["player_id"] == "a")
    b = next(r for r in ranking if r["player_id"] == "b")
    assert a["valor"] == b["valor"]
    assert a["num_jogos"] == 2
    assert b["num_jogos"] == 1


def test_ignores_rows_where_player_did_not_play():
    rows = [_row("a", 10, 0), _row("a", 999, 999, jogou=False)]
    ranking = impact_index(rows)

    assert ranking[0]["num_jogos"] == 1


def test_single_player_group_has_zero_impact_no_variance():
    rows = [_row("a", 10, 5)]
    ranking = impact_index(rows)

    assert ranking[0]["valor"] == 0.0
    assert ranking[0]["baixa_confianca"] is True

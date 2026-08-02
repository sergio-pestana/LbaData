from modeling.trends import player_trend, team_trend


def test_player_trend_returns_one_point_per_round_with_growing_game_count():
    series = [
        {"rodada_data": "2026-08-01", "pontos": 10, "jogou": True},
        {"rodada_data": "2026-08-08", "pontos": 15, "jogou": True},
        {"rodada_data": "2026-08-15", "pontos": 20, "jogou": True},
    ]
    trend = player_trend(series, "pontos")

    assert [p["valor"] for p in trend] == [10, 15, 20]
    assert [p["num_jogos"] for p in trend] == [1, 2, 3]
    assert trend[0]["baixa_confianca"] is True
    assert trend[2]["baixa_confianca"] is False


def test_player_trend_skips_rounds_the_player_did_not_play():
    series = [
        {"rodada_data": "2026-08-01", "pontos": 10, "jogou": True},
        {"rodada_data": "2026-08-08", "pontos": 0, "jogou": False},
        {"rodada_data": "2026-08-15", "pontos": 20, "jogou": True},
    ]
    trend = player_trend(series, "pontos")

    assert len(trend) == 2
    assert [p["valor"] for p in trend] == [10, 20]


def test_team_trend_returns_one_point_per_game():
    series = [
        {"rodada_data": "2026-08-01", "eficiencia": 50},
        {"rodada_data": "2026-08-08", "eficiencia": 60},
    ]
    trend = team_trend(series, "eficiencia")

    assert [p["valor"] for p in trend] == [50, 60]
    assert [p["num_jogos"] for p in trend] == [1, 2]

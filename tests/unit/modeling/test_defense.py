from modeling.defense import defense_index


def _row(player_id, reb_def=0, roubos=0, tocos=0, minutos=10.0, jogou=True):
    return {
        "player_id": player_id,
        "rebotes_defensivos": reb_def,
        "roubos": roubos,
        "tocos": tocos,
        "minutos_jogados": minutos,
        "jogou": jogou,
    }


def test_defense_index_formula():
    # (5 + 2 + 1) / 10 minutos = 0.8 por minuto
    rows = [_row("a", reb_def=5, roubos=2, tocos=1, minutos=10.0)]
    ranking = defense_index(rows)

    assert ranking[0]["player_id"] == "a"
    assert ranking[0]["valor"] == 0.8


def test_ranks_by_defense_descending_and_ignores_bench_rows():
    rows = [
        _row("a", reb_def=10, minutos=10.0),  # 1.0/min
        _row("b", reb_def=1, minutos=10.0),  # 0.1/min
        _row("c", reb_def=999, jogou=False),
    ]
    ranking = defense_index(rows)

    assert [r["player_id"] for r in ranking] == ["a", "b"]


def test_aggregates_across_multiple_games():
    rows = [
        _row("a", roubos=5, minutos=10.0),
        _row("a", roubos=5, minutos=10.0),
    ]
    ranking = defense_index(rows)

    assert ranking[0]["num_jogos"] == 2
    assert ranking[0]["valor"] == 0.5  # 10 ações / 20 minutos

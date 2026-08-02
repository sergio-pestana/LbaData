from modeling.usage import usage_index


def _row(player_id, arr2=0, arr3=0, lances=0, turnovers=0, minutos=10.0, jogou=True):
    return {
        "player_id": player_id,
        "arremessos_2pt_tentados": arr2,
        "arremessos_3pt_tentados": arr3,
        "lances_livres_tentados": lances,
        "turnovers": turnovers,
        "minutos_jogados": minutos,
        "jogou": jogou,
    }


def test_usage_index_formula_matches_fr011():
    # (5 + 2 + 3 + 1) / 10 minutos = 1.1 por minuto
    rows = [_row("a", arr2=5, arr3=2, lances=3, turnovers=1, minutos=10.0)]
    ranking = usage_index(rows)

    assert ranking[0]["player_id"] == "a"
    assert ranking[0]["valor"] == 1.1


def test_ranks_by_usage_descending_and_ignores_bench_rows():
    rows = [
        _row("a", arr2=10, minutos=10.0),  # 1.0/min
        _row("b", arr2=1, minutos=10.0),  # 0.1/min
        _row("c", arr2=999, jogou=False),
    ]
    ranking = usage_index(rows)

    assert [r["player_id"] for r in ranking] == ["a", "b"]


def test_aggregates_across_multiple_games():
    rows = [
        _row("a", arr2=5, minutos=10.0),
        _row("a", arr2=5, minutos=10.0),
    ]
    ranking = usage_index(rows)

    assert ranking[0]["num_jogos"] == 2
    assert ranking[0]["valor"] == 0.5  # 10 tentativas / 20 minutos

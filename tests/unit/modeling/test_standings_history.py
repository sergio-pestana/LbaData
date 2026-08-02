from modeling.trends import standings_trend


def test_returns_shaped_points_preserving_input_order():
    rows = [
        {
            "coletado_em": "2026-08-02T00:00:00Z",
            "posicao": 3,
            "jogos": 1,
            "vitorias": 0,
            "derrotas": 1,
            "saldo_pontos": -5,
            "pontos_fiba": 1,
        },
        {
            "coletado_em": "2026-08-09T00:00:00Z",
            "posicao": 1,
            "jogos": 2,
            "vitorias": 2,
            "derrotas": 0,
            "saldo_pontos": 10,
            "pontos_fiba": 4,
        },
    ]
    trend = standings_trend(rows)

    assert [p["coletado_em"] for p in trend] == [
        "2026-08-02T00:00:00Z",
        "2026-08-09T00:00:00Z",
    ]
    assert trend[1]["posicao"] == 1
    assert trend[1]["pontos_fiba"] == 4


def test_empty_history():
    assert standings_trend([]) == []

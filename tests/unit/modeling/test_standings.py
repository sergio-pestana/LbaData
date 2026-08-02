from modeling.standings import current_standings


def test_sorts_by_posicao():
    rows = [
        {"team_id": "b", "posicao": 2},
        {"team_id": "a", "posicao": 1},
        {"team_id": "c", "posicao": 3},
    ]
    result = current_standings(rows)
    assert [r["team_id"] for r in result] == ["a", "b", "c"]


def test_empty_snapshot():
    assert current_standings([]) == []

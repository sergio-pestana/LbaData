import pytest

from collector.parsers import parse_phase_standings, UnexpectedPayloadShape


def test_parses_all_teams_in_order(phase_standings_payload):
    rows = parse_phase_standings(phase_standings_payload)

    assert len(rows) == 8
    assert [r["posicao"] for r in rows] == list(range(1, 9))


def test_translates_opaque_elimination_stats_ids_to_readable_fields(phase_standings_payload):
    """Os valores por time vêm indexados por uuid de elimination_stats, não por
    nome legível — ver research.md #9. Este teste falha se essa tradução quebrar."""
    rows = parse_phase_standings(phase_standings_payload)
    leader = rows[0]

    for field in ("jogos", "vitorias", "derrotas", "saldo_pontos", "pontos_fiba"):
        assert field in leader

    # líder (posição 1) deve ter mais pontos FIBA que o último colocado
    assert rows[0]["pontos_fiba"] >= rows[-1]["pontos_fiba"]


def test_uses_overall_points_balance_not_head_to_head(phase_standings_payload):
    """points_balance aparece duplicado (overall e head_to_head) — devemos usar
    sempre o overall, nunca confundir com o de desempate."""
    rows = parse_phase_standings(phase_standings_payload)

    # saldo geral da temporada deve bater com jogos * margem plausível, não um
    # valor de desempate isolado; checagem básica de sanidade de magnitude
    for row in rows:
        assert -200 <= row["saldo_pontos"] <= 200


def test_raises_when_eliminations_is_empty():
    payload = {
        "data": {
            "elimination_stats": [],
            "eliminations": [],
        }
    }
    with pytest.raises(UnexpectedPayloadShape):
        parse_phase_standings(payload)


def test_derives_jogos_and_pontos_fiba_when_source_omits_them(phase_standings_sem_overall_payload):
    """research.md #4c: Ouro/Prata/Bronze 2025 só expõem wins/losses/points_balance
    (sem ranking_criteria='overall', sem game_played/fiba_group_points) — jogos e
    pontos_fiba precisam ser derivados de vitórias/derrotas, sem alterar a ordem
    (que continua vindo 100% da posição em team_stats)."""
    rows = parse_phase_standings(phase_standings_sem_overall_payload)

    assert len(rows) == 10
    assert [r["posicao"] for r in rows] == list(range(1, 11))
    for row in rows:
        assert row["jogos"] == row["vitorias"] + row["derrotas"]
        assert row["pontos_fiba"] == 2 * row["vitorias"] + row["derrotas"]


def test_raises_when_expected_criteria_missing():
    payload = {
        "data": {
            "elimination_stats": [
                {"id": "x1", "team_stat_source": "wins", "ranking_criteria": "overall"},
            ],
            "eliminations": [{"team_stats": [{"team_id": "t1", "stats": {"x1": 1}}]}],
        }
    }
    with pytest.raises(UnexpectedPayloadShape):
        parse_phase_standings(payload)

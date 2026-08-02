from modeling.leaderboards import player_stats_table, rank_players, team_metric_ranking


def _row(player_id, pontos, jogou=True):
    return {"player_id": player_id, "pontos": pontos, "jogou": jogou}


def test_ranks_players_by_criterion_descending():
    rows = [
        _row("a", 10), _row("a", 20),  # a: 30
        _row("b", 5), _row("b", 5), _row("b", 5),  # b: 15
    ]
    ranking = rank_players(rows, "pontos")

    assert [r["player_id"] for r in ranking] == ["a", "b"]
    assert ranking[0]["valor"] == 30
    assert ranking[0]["num_jogos"] == 2
    assert ranking[1]["valor"] == 15
    assert ranking[1]["num_jogos"] == 3


def test_ignores_rows_where_player_did_not_play():
    rows = [_row("a", 10), _row("a", 999, jogou=False)]
    ranking = rank_players(rows, "pontos")

    assert ranking[0]["valor"] == 10
    assert ranking[0]["num_jogos"] == 1


def test_low_confidence_flag_present_per_player():
    rows = [_row("a", 10)]
    ranking = rank_players(rows, "pontos")

    assert ranking[0]["num_jogos"] == 1
    assert ranking[0]["baixa_confianca"] is True


def _team_row(team_id, pontos):
    return {"team_id": team_id, "pontos": pontos}


def test_team_metric_ranking_computes_total_and_media():
    rows = [
        _team_row("a", 50), _team_row("a", 70),  # total 120, media 60
        _team_row("b", 40), _team_row("b", 40), _team_row("b", 40),  # total 120, media 40
    ]
    ranking = team_metric_ranking(rows, "pontos")

    assert ranking["a"]["total"] == 120
    assert ranking["a"]["media"] == 60
    assert ranking["a"]["num_jogos"] == 2
    assert ranking["b"]["total"] == 120
    assert ranking["b"]["media"] == 40
    assert ranking["b"]["num_jogos"] == 3


def _player_row(player_id, **stats):
    row = {"player_id": player_id, "jogou": True, "pontos": 0, "arremessos_2pt_tentados": 0,
           "arremessos_2pt_convertidos": 0, "arremessos_3pt_tentados": 0, "arremessos_3pt_convertidos": 0,
           "lances_livres_tentados": 0, "lances_livres_convertidos": 0}
    row.update(stats)
    return row


def test_player_stats_table_computes_total_and_media_per_metric():
    rows = [_player_row("a", pontos=10), _player_row("a", pontos=20)]
    tabela = player_stats_table(rows)

    linha = next(r for r in tabela if r["player_id"] == "a")
    assert linha["jogos"] == 2
    assert linha["pontos_total"] == 30
    assert linha["pontos_media"] == 15


def test_player_stats_table_computes_shooting_percentage_from_totals_not_average_of_games():
    # jogo 1: 1/1 (100%), jogo 2: 0/3 (0%) -> média ingênua seria 50%, mas o
    # correto é 1 convertido / 4 tentados = 25%
    rows = [
        _player_row("a", arremessos_2pt_tentados=1, arremessos_2pt_convertidos=1),
        _player_row("a", arremessos_2pt_tentados=3, arremessos_2pt_convertidos=0),
    ]
    tabela = player_stats_table(rows)
    linha = next(r for r in tabela if r["player_id"] == "a")

    assert linha["fg2_pct"] == 25.0


def test_player_stats_table_ignores_bench_rows():
    rows = [_player_row("a", pontos=10), _player_row("a", pontos=999, jogou=False)]
    tabela = player_stats_table(rows)

    assert tabela[0]["jogos"] == 1
    assert tabela[0]["pontos_total"] == 10


def test_ast_to_ratio_computed_from_totals():
    rows = [
        _player_row("a", assistencias=4, turnovers=2),
        _player_row("a", assistencias=6, turnovers=2),
    ]
    tabela = player_stats_table(rows)
    linha = next(r for r in tabela if r["player_id"] == "a")

    assert linha["ast_to_ratio"] == 10 / 4


def test_ast_to_ratio_is_none_when_no_turnovers_ever():
    rows = [_player_row("a", assistencias=5, turnovers=0)]
    tabela = player_stats_table(rows)

    assert tabela[0]["ast_to_ratio"] is None


def test_true_shooting_percentage_accounts_for_threes_and_free_throws():
    # 10 pontos vindos de: 2 arremessos de 2 convertidos (4 pts) + 2 de 3
    # convertidos (6 pts), em 4+3 tentativas de campo e 0 lances livres.
    # TS% = 10 / (2 * (7 + 0)) * 100 = 71.43%
    rows = [
        _player_row(
            "a",
            pontos=10,
            arremessos_2pt_tentados=4,
            arremessos_2pt_convertidos=2,
            arremessos_3pt_tentados=3,
            arremessos_3pt_convertidos=2,
        )
    ]
    tabela = player_stats_table(rows)

    assert round(tabela[0]["ts_pct"], 2) == 71.43


def test_true_shooting_percentage_zero_when_no_attempts():
    rows = [_player_row("a", pontos=0)]
    tabela = player_stats_table(rows)

    assert tabela[0]["ts_pct"] == 0.0


def test_tentativas_media_averages_all_shot_types_per_game():
    rows = [
        _player_row("a", arremessos_2pt_tentados=4, arremessos_3pt_tentados=2, lances_livres_tentados=2),
        _player_row("a", arremessos_2pt_tentados=2, arremessos_3pt_tentados=0, lances_livres_tentados=0),
    ]
    tabela = player_stats_table(rows)

    # total = (4+2+2) + (2+0+0) = 10 tentativas em 2 jogos -> média 5
    assert tabela[0]["tentativas_media"] == 5.0

import copy
import logging

from collector.parsers import parse_player_stats_logs


def test_parses_all_roster_rows_including_players_who_did_not_play(player_stats_logs_payload, known_game_id):
    rows = parse_player_stats_logs(player_stats_logs_payload, expected_game_id=known_game_id)

    assert len(rows) == 32
    did_not_play = [r for r in rows if r["jogou"] is False]
    played = [r for r in rows if r["jogou"] is True]
    assert len(did_not_play) > 0
    assert len(played) > 0


def test_minutes_played_converted_from_seconds_to_decimal_minutes(player_stats_logs_payload, known_game_id):
    rows = parse_player_stats_logs(player_stats_logs_payload, expected_game_id=known_game_id)

    full_game_players = [r for r in rows if r["minutos_jogados"] == 40.0]
    assert len(full_game_players) >= 1, "esperava ao menos um jogador com os 2400s (40min) completos"

    for row in rows:
        if row["jogou"]:
            assert 0 <= row["minutos_jogados"] <= 40.0
        else:
            assert row["minutos_jogados"] is None


def test_field_goals_and_three_pointers_are_separate_categories(player_stats_logs_payload, known_game_id):
    """field_goals_* = só 2 pontos; three_point_field_goals_* é categoria à parte
    (ver research.md #10) — soma reconstrói o placar do time exatamente."""
    rows = parse_player_stats_logs(player_stats_logs_payload, expected_game_id=known_game_id)

    team_id = rows[0]["time_id_na_partida"]
    team_rows = [r for r in rows if r["time_id_na_partida"] == team_id]

    pontos_reconstruidos = sum(
        r["arremessos_2pt_convertidos"] * 2 + r["arremessos_3pt_convertidos"] * 3 + r["lances_livres_convertidos"]
        for r in team_rows
    )
    pontos_oficiais = sum(r["pontos"] for r in team_rows)

    assert pontos_reconstruidos == pontos_oficiais


def test_stats_are_coerced_to_numeric_types(player_stats_logs_payload, known_game_id):
    rows = parse_player_stats_logs(player_stats_logs_payload, expected_game_id=known_game_id)
    row = rows[0]

    assert isinstance(row["pontos"], int)
    assert isinstance(row["eficiencia"], float)
    assert isinstance(row["plus_minus"], int)


def test_missing_count_field_defaults_to_zero_with_warning_not_exception(
    player_stats_logs_payload, known_game_id, caplog
):
    """Achado real (Camada 2, 2026-07-31): a mesa às vezes omite um campo de
    contagem inteiro quando o valor seria zero, mesmo para jogador que
    claramente jogou (campos centrais presentes). Por decisão do usuário,
    isso NÃO derruba o jogo inteiro — vira 0 com um aviso logado."""
    payload = copy.deepcopy(player_stats_logs_payload)
    del payload["data"][0]["stats"]["rebounds_offensive"]
    del payload["data"][0]["stats"]["assists"]

    with caplog.at_level(logging.WARNING, logger="collector.parsers"):
        rows = parse_player_stats_logs(payload, expected_game_id=known_game_id)

    row = rows[0]
    assert row["rebotes_ofensivos"] == 0
    assert row["assistencias"] == 0
    assert any("rebounds_offensive" in msg for msg in caplog.messages)
    assert any("assists" in msg for msg in caplog.messages)


def test_missing_core_field_still_raises_despite_lenient_count_fields(
    player_stats_logs_payload, known_game_id
):
    """Campos centrais (pontos, minutos, eficiência, plus/minus, game_played)
    continuam obrigatórios — a tolerância vale só para campos de contagem."""
    import pytest

    from collector.parsers import UnexpectedPayloadShape

    payload = copy.deepcopy(player_stats_logs_payload)
    del payload["data"][0]["stats"]["efficiency"]

    with pytest.raises(UnexpectedPayloadShape):
        parse_player_stats_logs(payload, expected_game_id=known_game_id)

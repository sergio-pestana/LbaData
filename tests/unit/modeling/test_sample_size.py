from modeling.sample_size import flag_low_confidence


def test_flags_below_default_threshold():
    result = flag_low_confidence(10.0, num_jogos=2)
    assert result == {"valor": 10.0, "num_jogos": 2, "baixa_confianca": True}


def test_does_not_flag_at_or_above_default_threshold():
    result = flag_low_confidence(10.0, num_jogos=3)
    assert result["baixa_confianca"] is False


def test_custom_threshold():
    result = flag_low_confidence(10.0, num_jogos=4, limiar=5)
    assert result["baixa_confianca"] is True

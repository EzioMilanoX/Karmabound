from karmabound.simulacao import simular, simular_com_combate


def test_reprodutivel():
    a, b = simular(300, seed=5), simular(300, seed=5)
    assert a.despertares == b.despertares


def test_calibracao_no_alvo():
    """Alvo do DESIGN.md: 1–2 Despertares por run, em média, com combate real."""
    res = simular_com_combate(800, seed=1, dificuldade="dificil")
    assert 1.0 <= res.media_transbordos <= 2.0
    assert sum(res.transbordos.values()) == res.runs


def test_modelo_simples_ainda_roda():
    res = simular(300, seed=1)
    assert sum(res.despertares.values()) == res.runs

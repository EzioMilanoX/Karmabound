import pytest

from karmabound.carma import Carma, ConfigCarma

CONFIG = ConfigCarma(
    maximo=100,
    por_giro={"cinza": 6, "sangue": 3, "maldito": 0, "divino": -40},
    por_dano_total=22,
    por_custo=6,
    pity_suave_inicio=60,
    pity_suave_multiplicador=3.0,
    pity_suave_raridades=("maldito", "divino"),
)
BASE = {"cinza": 60, "sangue": 28, "maldito": 10, "divino": 2}


def test_azar_dano_e_custo_enchem():
    c = Carma(CONFIG)
    c.registrar_giro("cinza")
    c.registrar_dano(0.5)
    c.registrar_custo()
    assert c.valor == pytest.approx(6 + 11 + 6)


def test_divino_consome_e_nao_fica_negativo():
    c = Carma(CONFIG, valor=10)
    c.registrar_giro("divino")
    assert c.valor == 0


def test_transborda_e_trava_ate_o_despertar():
    c = Carma(CONFIG, valor=98)
    c.registrar_giro("cinza")
    assert c.transbordando and c.valor == 100
    c.registrar_giro("divino")  # travado: a sorte não apaga um Despertar garantido
    assert c.transbordando
    c.despertar()
    assert c.valor == 0


def test_despertar_sem_transbordar_e_erro():
    with pytest.raises(RuntimeError):
        Carma(CONFIG, valor=50).despertar()


def test_pity_suave():
    assert Carma(CONFIG, valor=60).pesos(BASE) == BASE
    meio = Carma(CONFIG, valor=80).pesos(BASE)
    assert meio["divino"] == pytest.approx(4) and meio["cinza"] == 60
    assert Carma(CONFIG, valor=100).pesos(BASE)["maldito"] == pytest.approx(30)

import pytest

from karmabound.mesa import Mesa


@pytest.fixture
def mesa():
    return Mesa.padrao(seed=11)


def test_giro_comum_registra_carma(mesa):
    giro = mesa.girar("destino")
    assert len(giro.fatias) == 1 and not giro.despertar
    esperado = max(0.0, mesa.carma.config.por_giro[giro.fatias[0].raridade])
    assert mesa.carma.valor == pytest.approx(esperado)


def test_modo_escolha_entrega_as_opcoes(mesa):
    giro = mesa.girar("tecnicas")
    assert len(giro.fatias) == mesa.rodas["tecnicas"].opcoes


def test_despertar_garante_a_raridade_maxima_e_zera_o_carma(mesa):
    mesa.carma.valor = mesa.carma.config.maximo
    giro = mesa.girar("tecnicas")
    assert giro.despertar
    assert [f.raridade for f in giro.fatias] == [mesa.ordem[-1]]
    assert mesa.carma.valor == 0


def test_sem_permissao_nao_desperta(mesa):
    mesa.carma.valor = mesa.carma.config.maximo
    assert not mesa.girar("arco", permitir_despertar=False).despertar
    assert mesa.carma.transbordando  # travado, esperando a luta


def test_taxas_publicadas_e_atuais(mesa):
    publicadas = {r: pub for r, (pub, _) in mesa.taxas().items()}
    assert sum(publicadas.values()) == pytest.approx(100)
    assert all(pub == pytest.approx(agora) for pub, agora in mesa.taxas().values())
    mesa.carma.valor = 90  # dentro do pity suave
    pub, agora = mesa.taxas()[mesa.ordem[-1]]
    assert agora > pub
    assert sum(a for _, a in mesa.taxas().values()) == pytest.approx(100)

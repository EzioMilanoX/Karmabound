"""Os votos do menu (pacto.py): pontos fixos, ganhos, recompensas que se liberam."""

from collections import Counter

from karmabound import pacto
from karmabound.jornada import Jornada
from karmabound.legado import Legado
from karmabound.run import Contexto

CTX = Contexto.padrao("dificil")
CAT = CTX.catalogo


def test_toda_restricao_tem_uma_recompensa_que_so_ela_libera():
    assert set(CAT.recompensas) == set(CAT.restricoes)
    assert len(set(CAT.recompensas.values())) == len(CAT.restricoes)
    nas_rodas = {f.id for r in CTX.rodas.values() for f in r.fatias}
    assert not set(CAT.recompensas.values()) & nas_rodas  # fora das rodas até liberar


def test_uma_recompensa_liberada_entra_na_roda():
    item = CAT.recompensas["sem_descanso"]
    ctx = Contexto.padrao("dificil", desbloqueios=frozenset({item}))
    assert item in {f.id for r in ctx.rodas.values() for f in r.fatias}


def test_restricoes_dao_pontos_e_os_ganhos_cabem_neles():
    restricoes = ["sem_descanso", "corpo_ofertado"]
    pontos = pacto.pontos(CAT, restricoes)
    assert pontos > 0 and pacto.pontos(CAT, []) == 0
    ganhos = []
    while pacto.cabe(CAT, restricoes, ganhos, "forca"):
        ganhos.append("forca")
    assert ganhos and pacto.custo(CAT, ganhos) <= pontos


def test_o_voto_do_menu_e_jurado_antes_da_primeira_luta():
    escolha = {"restricoes": ["sem_descanso"], "ganhos": ["forca"]}
    j = Jornada.nova("dificil", seed=1, pacto=escolha)
    (voto,) = j.estado.votos.ativos
    assert [r.id for r in voto.restricoes] == ["sem_descanso"] and voto.duracao == "run"
    assert j.recompensas_cumpridas() == [CAT.recompensas["sem_descanso"]]


def test_vencer_com_o_voto_libera_a_recompensa():
    leg = Legado()
    item = CAT.recompensas["prazo"]
    f = leg.fechar_run(["Naruto"], 12, 3, True, Counter(), recompensas=[item])
    assert f.desbloqueados == [item] and item in leg.desbloqueios
    perdeu = Legado()
    perdeu.fechar_run(["Naruto"], 5, 1, False, Counter(), recompensas=[item])
    assert not perdeu.desbloqueios

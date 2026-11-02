import random

import pytest

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import Luta, Lutador, Tecnica, config_combate
from karmabound.rodas import carregar_balanceamento
from karmabound.simulacao import simular_com_combate

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
DIRETO = Tecnica("direto", "Direto", "ataque", dano=7, recarga=1, sutileza=2)
INVESTIDA = Tecnica(
    "investida", "Investida", "ataque", dano=10, recarga=2, sutileza=1, perigosa=True
)
GUARDA = Tecnica("guarda", "Guarda", "defesa", bloqueio=8, recarga=2)
REVIDE = Tecnica("revide", "Revide", "defesa", revide=6, recarga=3)
LAMINA = Tecnica(
    "lamina", "Lâmina", "ataque", dano=16, custo_vida=4, recarga=3, sutileza=3, perigosa=True
)
MARCA = Tecnica("marca", "Marca", "maldita", marca=3, recarga=4)
FORCA = Tecnica("forca", "Força", "maldita", fortalecer=3, recarga=99)
DUPLO = Tecnica("duplo", "Duplo", "ataque", dano=5, golpes=2, recarga=2)


def lutador(nome, tecnicas=(), vida=50, vel=1, perc=0, carma=None):
    return Lutador(nome, vida, vel, perc, list(tecnicas), carma=carma)


def carma():
    return Carma(ConfigCarma(100, {}, 20, 6, 60, 3.0, ()))


def luta(j, r, seed=0, surpresa=0.5):
    return Luta(j, r, BASICO, random.Random(seed), surpresa)


def sem_abertura(lt):
    """Gasta a abertura com um golpe que ninguém sente, para testar o meio da luta."""
    lt.abertura = False
    return lt


def test_mais_velocidade_comeca():
    j, r = lutador("J", vel=3), lutador("R", vel=1)
    assert luta(j, r).vez is j
    j, r = lutador("J", vel=1), lutador("R", vel=3)
    assert luta(j, r).vez is r


def test_ataque_surpresa_nao_percebido_causa_dano_extra():
    j, r = lutador("J", [DIRETO], vel=3), lutador("R", perc=0)
    acao = luta(j, r).resolver(DIRETO)
    assert acao.surpresa and not acao.reagiu
    assert r.vida == 50 - round(7 * 1.5)


def test_percepcao_alta_reage_a_surpresa_e_devolve_golpe():
    j, r = lutador("J", [DIRETO], vel=3), lutador("R", perc=2)
    acao = luta(j, r).resolver(DIRETO)
    assert acao.reagiu
    assert r.vida == 50 - 7 // 2
    assert j.vida == 50 - BASICO.dano


def test_percepcao_so_reage_a_golpe_perigoso_no_meio_da_luta():
    j, r = lutador("J", [DIRETO, INVESTIDA], vel=3), lutador("R", perc=3)
    lt = sem_abertura(luta(j, r))
    assert not lt.resolver(DIRETO).reagiu  # não é perigoso
    lt.vez = j
    assert lt.resolver(INVESTIDA).reagiu  # perigoso e Percepção 3 >= Sutileza 1


def test_sutileza_maior_que_percepcao_passa():
    j, r = lutador("J", [LAMINA], vel=3), lutador("R", perc=2)
    assert not sem_abertura(luta(j, r)).resolver(LAMINA).reagiu


def test_recarga_conta_turnos_do_proprio_lutador():
    j, r = lutador("J", [INVESTIDA], vel=3), lutador("R")
    lt = sem_abertura(luta(j, r))
    lt.resolver(INVESTIDA)  # recarga 2
    for _ in range(2):
        assert INVESTIDA not in lt.prontas(j)
        lt.turno_rival()
        lt.resolver(BASICO)
    assert INVESTIDA in lt.prontas(j)


def test_tecnica_em_recarga_e_recusada():
    j, r = lutador("J", [INVESTIDA], vel=3), lutador("R")
    lt = sem_abertura(luta(j, r))
    lt.resolver(INVESTIDA)
    lt.turno_rival()
    with pytest.raises(ValueError):
        lt.resolver(INVESTIDA)


def test_bloqueio_absorve_e_golpes_multiplos_o_furam():
    j, r = lutador("J", [DUPLO], vel=1), lutador("R", [GUARDA], vel=3)
    lt = sem_abertura(luta(j, r))
    lt.resolver(GUARDA)  # rival bloqueia 8
    lt.resolver(DUPLO)  # 5 + 5: o primeiro é absorvido, 2 de 5 do segundo também
    assert r.vida == 50 - 2


def test_revide_devolve_no_proximo_golpe():
    j, r = lutador("J", [DIRETO], vel=1), lutador("R", [REVIDE], vel=3)
    lt = sem_abertura(luta(j, r))
    lt.resolver(REVIDE)
    lt.resolver(DIRETO)
    assert j.vida == 50 - 6 and r.revide == 0


def test_custo_de_vida_e_custo_de_poder_enchem_o_carma():
    c = carma()
    j, r = lutador("J", [LAMINA], vel=3, carma=c), lutador("R")
    sem_abertura(luta(j, r)).resolver(LAMINA)
    assert j.vida == 46
    assert c.valor == pytest.approx(4 / 50 * 20 + 6)


def test_marca_fere_quem_usa_tecnica():
    j, r = lutador("J", [MARCA], vel=3), lutador("R")
    lt = sem_abertura(luta(j, r))
    lt.resolver(MARCA)
    lt.resolver(BASICO)  # agora é a vez do rival marcado
    assert r.vida == 50 - 3  # sofreu a marca ao agir; o Golpe dele acertou J
    assert j.vida == 50 - BASICO.dano


def test_fortalecer_soma_em_todo_golpe_da_luta():
    j, r = lutador("J", [FORCA], vel=3), lutador("R")
    lt = sem_abertura(luta(j, r))
    lt.resolver(FORCA)
    lt.turno_rival()
    vida = r.vida
    lt.resolver(BASICO)
    assert vida - r.vida == BASICO.dano + 3


def test_percepcao_decide_quanto_se_ve_da_intencao():
    r = lutador("R", [INVESTIDA], vel=1)
    for perc, esperado in [(0, None), (1, "ataque"), (2, "tecnica")]:
        j = lutador("J", vel=3, perc=perc)
        r.vida, r.recargas = 50, {}
        lt = luta(j, r)
        vista = lt.ver_intencao()
        if esperado == "tecnica":
            assert vista is lt.intencao_rival
        else:
            assert vista == esperado


def test_rival_cumpre_o_que_anunciou():
    j, r = lutador("J", vel=3), lutador("R", [INVESTIDA, GUARDA], vel=1)
    lt = luta(j, r, seed=3)
    for _ in range(6):
        if lt.acabou:
            break
        lt.resolver(BASICO)
        anunciada = lt.intencao_rival
        assert lt.turno_rival().tecnica == anunciada.id


def test_vida_persiste_entre_lutas_mas_o_resto_zera():
    j = lutador("J", [INVESTIDA], vel=3)
    j.vida, j.bloqueio, j.recargas = 20, 5, {"investida": 2}
    j.nova_luta()
    assert j.vida == 20 and j.bloqueio == 0 and not j.recargas


def test_modos_de_dificuldade():
    bal = carregar_balanceamento()
    assert config_combate(bal)["dificuldade"] == bal["combate"]["dificuldade_padrao"]
    facil, brutal = config_combate(bal, "acessivel"), config_combate(bal, "brutal")
    assert facil["jogador"]["vida"] > brutal["jogador"]["vida"]
    assert facil["rivais"]["vida_por_luta"] < brutal["rivais"]["vida_por_luta"]
    with pytest.raises(ValueError):
        config_combate(bal, "impossivel")


def test_modos_ficam_em_ordem_de_dificuldade():
    """Barato e grosseiro: o modo acessível tem que vencer bem mais que o brutal."""
    facil = simular_com_combate(400, seed=2, dificuldade="acessivel")
    brutal = simular_com_combate(400, seed=2, dificuldade="brutal")
    assert facil.vitorias > brutal.vitorias * 2

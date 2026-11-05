"""Quebra de guarda: pressão concentrada derruba a defesa de qualquer rival."""

import random

from karmabound.combate import (
    GUARDA_ESVAI,
    GUARDA_POR_GOLPE,
    HESITAR,
    POSTURA_CHEFE,
    Luta,
    Lutador,
    Tecnica,
    limiar_guarda,
)

BASICO = Tecnica("golpe_basico", "Golpe", "ataque", dano=4)
GUARDA = Tecnica("guarda", "Guarda", "defesa")
SOCO = Tecnica("soco", "Soco", "ataque", dano=3)


def _luta(dano=49, golpes=1, vida=100, chefe=False, rival_tecnicas=(GUARDA,)):
    t = Tecnica("marreta", "Marreta", "ataque", dano=dano, golpes=golpes)
    j = Lutador("Você", 100, 3, 0, [t])
    r = Lutador("R", vida, 1, 0, list(rival_tecnicas), chefe=chefe)
    lt = Luta(j, r, BASICO, random.Random(0))
    lt.abertura = False
    return lt, t


def test_o_limiar_e_metade_da_vida_e_o_do_chefe_maior():
    lt, _ = _luta(vida=100)
    assert limiar_guarda(lt.rival) == 50
    lt, _ = _luta(vida=100, chefe=True)
    assert limiar_guarda(lt.rival) == 70


def test_abaixo_do_limiar_o_medidor_so_enche():
    lt, t = _luta(dano=47)
    acao = lt.resolver(t)
    assert not acao.quebrou and lt.rival.guarda == 47 + GUARDA_POR_GOLPE


def test_passar_do_limiar_quebra_a_guarda_e_o_rival_perde_o_turno():
    lt, t = _luta(dano=49)
    r = lt.rival
    acao = lt.resolver(t)
    assert acao.quebrou == "R"
    assert r.quebrado and r.pular == 1 and r.guarda == 0
    assert lt.intencao_rival is HESITAR  # o anúncio é refeito: ele não age
    assert lt.turno_rival().tecnica == "hesitar"


def test_golpes_multiplos_quebram_mais():
    um, t1 = _luta(dano=20)
    um.resolver(t1)
    cinco, t5 = _luta(dano=4, golpes=5)
    cinco.resolver(t5)
    assert um.rival.vida == cinco.rival.vida  # o mesmo dano...
    assert cinco.rival.guarda > um.rival.guarda  # ...mas a guarda sofre mais


def test_guarda_quebrada_sofre_mais_ate_agir_de_novo():
    lt, t = _luta(dano=49, rival_tecnicas=(SOCO,))
    j, r = lt.jogador, lt.rival
    lt.resolver(t)  # quebra
    leve = Tecnica("leve", "Leve", "ataque", dano=8)
    j.tecnicas.append(leve)
    lt.turno_rival()  # o turno perdido: a guarda segue quebrada
    assert r.quebrado
    assert lt.resolver(leve).dano == 10  # +25%
    lt.turno_rival()  # ele age de novo: a guarda se recompõe
    assert not r.quebrado
    assert lt.resolver(leve).dano == 8


def test_o_medidor_esvazia_a_cada_turno_do_rival():
    lt, t = _luta(dano=30)
    lt.resolver(t)
    antes = lt.rival.guarda
    lt.turno_rival()
    assert lt.rival.guarda == antes - round(100 * GUARDA_ESVAI)


def test_a_quebra_do_chefe_nao_fura_a_postura():
    lt, t = _luta(dano=90, vida=100, chefe=True)
    r = lt.rival
    postura = round(100 * POSTURA_CHEFE)
    quebrou = ""
    for _ in range(3):  # 32 por ação (a postura segura em 30): quebra na terceira
        lt.vez = lt.jogador
        acao = lt.resolver(t)
        assert acao.dano <= postura
        quebrou = quebrou or acao.quebrou
    assert quebrou and r.quebrado
    r.vida = r.vida_max  # vida de sobra: só a postura limita
    lt.vez = lt.jogador
    assert lt.resolver(t).dano == postura  # quebrado, mas a postura ainda segura


def test_o_jogador_nao_tem_guarda():
    lt, _ = _luta(rival_tecnicas=(Tecnica("forte", "Forte", "ataque", dano=60),))
    lt.vez = lt.rival
    lt.turno_rival()
    assert lt.jogador.guarda == 0 and not lt.jogador.quebrado

"""Lutas contra um bando: até 3 rivais, cada um com um papel."""

import random

import pytest

from karmabound.caminho import carregar_caminho, montar_bando, tecnica_do_papel
from karmabound.combate import (
    Luta,
    Lutador,
    Tecnica,
    escolher_alvo_auto,
    escolher_jogador_auto,
    escolher_rival,
)

GOLPE = Tecnica("golpe", "Golpe", "ataque", dano=4)
SOCO = Tecnica("soco", "Soco", "ataque", dano=6)


def _jogador(vida=100, velocidade=5):
    return Lutador("Você", vida, velocidade, 0, [Tecnica("forte", "Forte", "ataque", dano=10)])


def _rival(nome, vida=30, velocidade=1, papel="", tecnicas=None):
    r = Lutador(nome, vida, velocidade, 0, list(tecnicas or [SOCO]), papel=papel, titulo=nome)
    return r


def _luta(rivais, jogador=None, seed=1):
    return Luta(jogador or _jogador(), rivais, GOLPE, random.Random(seed))


def test_um_rival_continua_sendo_um_duelo():
    r = _rival("R")
    luta = _luta(r)
    assert luta.rivais == [r] and luta.rival is r and luta.vivos == [r]


def test_de_um_a_tres_rivais():
    with pytest.raises(ValueError):
        _luta([_rival(f"R{i}") for i in range(4)])


def test_o_bando_age_em_sequencia_do_mais_rapido():
    lento, rapido = _rival("Lento", velocidade=1), _rival("Rapido", velocidade=3)
    luta = _luta([lento, rapido])
    assert luta.vez is luta.jogador  # você é o mais rápido
    luta.resolver(GOLPE)
    assert luta.vez is rapido
    luta.turno_rival()
    assert luta.vez is lento
    luta.turno_rival()
    assert luta.vez is luta.jogador
    assert luta.rodadas == 1


def test_o_turno_do_rival_nao_muda_o_alvo():
    a, b = _rival("A"), _rival("B")
    luta = _luta([a, b])
    luta.mirar(b)
    luta.resolver(GOLPE)
    while luta.vez is not luta.jogador:
        luta.turno_rival()
    assert luta.rival is b


def test_mirar_e_bater_em_quem_voce_escolheu():
    a, b = _rival("A"), _rival("B")
    luta = _luta([a, b])
    luta.mirar(b)
    luta.resolver(luta.jogador.tecnicas[0])
    assert a.vida == 30 and b.vida < 30


def test_o_alvo_caido_passa_a_mira_e_a_luta_so_acaba_com_todos():
    a, b = _rival("A", vida=5), _rival("B")
    luta = _luta([a, b])
    luta.mirar(a)
    luta.resolver(luta.jogador.tecnicas[0])
    assert not a.vivo and not luta.acabou
    assert luta.rival is b
    with pytest.raises(ValueError):
        luta.mirar(a)
    b.vida = 1
    while luta.vez is not luta.jogador:
        luta.turno_rival()
    luta.resolver(GOLPE)
    assert luta.acabou and luta.vencedor is luta.jogador


def test_quem_caiu_nao_age():
    a, b = _rival("A", vida=5), _rival("B", velocidade=2)
    luta = _luta([a, b])
    luta.mirar(a)
    luta.resolver(luta.jogador.tecnicas[0])
    assert luta.vez is b
    luta.turno_rival()
    assert luta.vez is luta.jogador


def test_cada_rival_anuncia_a_sua_acao():
    a = _rival("A", tecnicas=[SOCO])
    b = _rival("B", tecnicas=[Tecnica("chute", "Chute", "ataque", dano=9)])
    luta = _luta([a, b], jogador=Lutador("Você", 100, 5, 2, [SOCO]))
    assert luta.intencao_de(a).id == "soco"
    assert luta.intencao_de(b).id == "chute"
    assert luta.ver_intencao(b).id == "chute"


def test_guardiao_protege_o_mais_ferido():
    guardar = Tecnica("guardar", "Guardar", "defesa", recarga=2, proteger=8)
    lamina = _rival("Lâmina", papel="lamina")
    guardiao = _rival("Guardião", velocidade=0, papel="guardiao", tecnicas=[SOCO, guardar])
    lamina.vida = 10
    luta = _luta([lamina, guardiao])
    luta.vez = guardiao
    with luta.foco(guardiao):
        luta.intencao_rival = escolher_rival(luta)
    acao = luta.turno_rival()
    assert acao.tecnica == "guardar" and lamina.bloqueio == 8


def test_curandeiro_cura_o_aliado():
    bencao = Tecnica("bencao", "Bênção", "defesa", recarga=2, curar_aliado=10)
    lamina = _rival("Lâmina", papel="lamina")
    curandeiro = _rival("Curandeiro", papel="curandeiro", tecnicas=[SOCO, bencao])
    lamina.vida = 10
    luta = _luta([lamina, curandeiro])
    luta.vez = curandeiro
    with luta.foco(curandeiro):
        luta.intencao_rival = escolher_rival(luta)
    acao = luta.turno_rival()
    assert acao.tecnica == "bencao" and lamina.vida == 20


def test_comandante_inspira_o_bando():
    grito = Tecnica("grito", "Grito", "defesa", recarga=99, inspirar=2)
    a = _rival("A", papel="lamina")
    c = _rival("Comandante", papel="comandante", tecnicas=[SOCO, grito])
    luta = _luta([a, c])
    luta.vez = c
    with luta.foco(c):
        luta.intencao_rival = escolher_rival(luta)
    luta.turno_rival()
    assert a.bonus_dano == 2 and c.bonus_dano == 2


def test_tecnica_de_area_respinga_no_bando():
    explosao = Tecnica("explosao", "Explosão", "ataque", dano=20, area=0.5)
    jogador = Lutador("Você", 100, 5, 0, [explosao])
    a, b, c = _rival("A", vida=50), _rival("B", vida=50), _rival("C", vida=50)
    luta = _luta([a, b, c], jogador=jogador)
    luta.abertura = False  # sem a surpresa (o rival perceberia e levaria metade)
    luta.resolver(explosao)
    assert a.vida == 30 and b.vida == 40 and c.vida == 40


def test_mira_automatica_derruba_o_curandeiro_antes():
    lamina = _rival("Lâmina", papel="lamina")
    guardiao = _rival("Guardião", papel="guardiao")
    curandeiro = _rival("Curandeiro", papel="curandeiro")
    luta = _luta([lamina, guardiao, curandeiro])
    assert escolher_alvo_auto(luta) is curandeiro
    lamina.vida = 2  # cai com um Golpe: primeiro ele
    assert escolher_alvo_auto(luta) is lamina


def test_bando_inteiro_ate_o_fim_no_piloto():
    cam = carregar_caminho()
    rng = random.Random(3)
    for papeis in cam.grupos + cam.grupos_elite:
        tecnicas = [[SOCO] for _ in papeis]
        bando = montar_bando(cam, papeis, 40, tecnicas, rng, 2, (1, 3), (0, 2))
        assert len({r.nome for r in bando}) == len(bando)  # nomes únicos (o log usa o nome)
        jogador = Lutador("Você", 200, 2, 1, [Tecnica("forte", "Forte", "ataque", dano=12)])
        luta = Luta(jogador, bando, GOLPE, rng)
        for _ in range(400):
            if luta.acabou:
                break
            if luta.vez is jogador:
                luta.mirar(escolher_alvo_auto(luta))
                luta.resolver(escolher_jogador_auto(luta))
            else:
                luta.turno_rival()
        assert luta.acabou


def test_vida_do_bando_e_repartida_pelos_papeis():
    cam = carregar_caminho()
    papeis = ("lamina", "guardiao", "curandeiro")
    bando = montar_bando(cam, papeis, 50, [[SOCO]] * 3, random.Random(1), 1, (1, 3), (0, 2))
    total = sum(r.vida_max for r in bando)
    assert abs(total - 50 * cam.bando["fator_vida"]["3"]) <= 2
    guardiao = next(r for r in bando if r.papel == "guardiao")
    curandeiro = next(r for r in bando if r.papel == "curandeiro")
    assert guardiao.vida_max > curandeiro.vida_max
    assert any(t.proteger for t in guardiao.tecnicas)
    assert any(t.curar_aliado for t in curandeiro.tecnicas)


def test_tecnica_do_papel_cresce_com_o_capitulo():
    cam = carregar_caminho()
    xama = cam.papeis["xama"]
    assert tecnica_do_papel(xama, 40, 3).veneno > tecnica_do_papel(xama, 40, 1).veneno


def test_no_maximo_tres_invocacoes_em_campo():
    from karmabound.combate import MAX_INVOCACOES, invocar

    j = _jogador()
    for i in range(5):
        invocar(j, [3, i + 1, f"inv{i}"])
    assert len(j.invocacoes) == MAX_INVOCACOES == 3
    assert [x[2] for x in j.invocacoes] == ["inv2", "inv3", "inv4"]  # as mais antigas saíram


def test_acao_conta_o_que_a_tela_precisa():
    sapo = Tecnica("sapo", "Sapo", "ataque", invocar=5, invocar_turnos=3)
    jogador = Lutador("Você", 100, 5, 0, [sapo])
    a, b = _rival("A", vida=60), _rival("B", vida=60)
    luta = _luta([a, b], jogador=jogador)
    luta.mirar(b)
    acao = luta.resolver(sapo)
    assert acao.alvo == "B"
    while luta.vez is not jogador:
        luta.turno_rival()
    acao = luta.resolver(GOLPE)
    assert acao.invocadas == (("sapo", 5),)

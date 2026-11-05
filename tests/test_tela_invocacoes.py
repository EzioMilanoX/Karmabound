"""A tela de luta com invocações e clones em campo, o impacto do golpe e o acelerar."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from karmabound.combate import MAX_CLONES, MAX_INVOCACOES, invocar  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.run import escolher_porta  # noqa: E402
from karmabound.tela_luta import (  # noqa: E402
    DURACAO_PARTIR,
    DURACAO_POOF,
    LutaScene,
)


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()
        self.seguradas: set[str] = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas

    def is_action_held(self, acao):
        return acao in self.seguradas


class Nulo:
    """Um renderer que aceita tudo: o desenho roda inteiro sem janela."""

    def __getattr__(self, nome):
        return lambda *a, **k: None


def aperta(cena, e, *teclas, passo=1 / 30):
    e.apertadas = set(teclas)
    cena.update(None, passo)
    e.apertadas = set()


def anda(cena, segundos, passo=1 / 30):
    for _ in range(round(segundos / passo)):
        cena.update(None, passo)


def _luta(tipo="rival", papeis=(), seed=11):
    j = Jornada.nova("dificil", seed=seed)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    if j.fase == "caminho":
        escolher_porta(j.estado, j.ctx.caminho.porta(tipo, papeis=papeis))
        j._comecar_luta()
    return j


def _tela(j):
    e = Entrada()
    tela = LutaScene(j, e, lambda v: None, lambda: None)
    tela.entrada_ate = 0
    tela.relogio = 1.0
    tela.anim_ate = tela.proxima_rival = 0
    j.luta.vez = j.jogador  # ninguém age sozinho no meio do teste
    return tela, e


def _vivas(tela, dono):
    return [c for c in tela.criaturas if c.dono is dono and c.parte is None]


def _clones(tela, dono):
    return [c for c in tela.clones_em_campo if c.dono is dono and c.parte is None]


def _golpe(tela, e):
    """O jogador usa o Golpe (selo 1) no alvo."""
    tela.luta.vez = tela.j.jogador
    tela.anim_ate = tela.relogio
    tela.cursor = 0
    aperta(tela, e, "confirmar")


def test_a_criatura_aparece_e_some_com_a_invocacao():
    j = _luta()
    tela, _e = _tela(j)
    jog = j.jogador
    invocar(jog, [2, 5, "sapo_chefe"])
    anda(tela, 0.1)
    vivas = _vivas(tela, jog)
    assert len(vivas) == 1
    sapo = vivas[0]
    assert (sapo.origem, sapo.dano, sapo.turnos) == ("sapo_chefe", 5, 2)
    x, _y, _esc, lado = tela._casa(sapo)
    assert lado == 1 and abs(x - tela._centro(jog)[0]) < 200  # ao lado do jogador
    tela.render(None, Nulo())  # desenha a criatura (e os pontinhos dos turnos)
    jog.invocacoes[0][0] = 1  # um bote a menos: a mesma criatura, com menos turnos
    anda(tela, 0.1)
    assert _vivas(tela, jog) == [sapo] and sapo.turnos == 1
    jog.invocacoes.clear()  # o tempo dela acabou
    anda(tela, 0.1)
    assert sapo.parte is not None and not _vivas(tela, jog)
    tela.render(None, Nulo())  # desenha a partida
    anda(tela, DURACAO_PARTIR + 0.2)
    assert sapo not in tela.criaturas


def test_no_maximo_tres_em_campo_e_a_quarta_toma_o_lugar_da_mais_antiga():
    j = _luta()
    tela, _e = _tela(j)
    jog = j.jogador
    origens = ("sapo_chefe", "caes_divinos", "coruja_trovao", "o_indomavel")
    for i, origem in enumerate(origens):
        invocar(jog, [3, 2 + i, origem])
        anda(tela, 0.1)
    vivas = _vivas(tela, jog)
    assert len(vivas) == MAX_INVOCACOES == 3
    assert [c.origem for c in vivas] == list(origens[1:])
    assert sorted(c.lugar for c in vivas) == [0, 1, 2]  # cada uma no seu lugar
    sapo = next(c for c in tela.criaturas if c.origem == "sapo_chefe")
    assert sapo.parte is not None  # a mais antiga vai embora, dissolvendo
    assert next(c for c in vivas if c.origem == "o_indomavel").lugar == sapo.lugar
    tela.render(None, Nulo())


def test_as_invocacoes_do_rival_ficam_perto_dele_no_bando():
    j = _luta("bando", ("lamina", "guardiao", "curandeiro"))
    tela, _e = _tela(j)
    a, b, c = j.luta.rivais
    invocar(b, [3, 3, "levantem_se"])
    invocar(c, [3, 3, "caes_divinos"])
    anda(tela, 0.1)
    for dono in (b, c):
        criatura = _vivas(tela, dono)[0]
        x, _y, _esc, lado = tela._casa(criatura)
        assert lado == -1  # olha para o jogador
        perto = min(j.luta.rivais, key=lambda r: abs(tela._centro(r)[0] - x))
        assert perto is dono
    tela.render(None, Nulo())


def test_a_invocacao_da_o_bote_antes_do_golpe_do_dono():
    j = _luta()
    tela, e = _tela(j)
    jog, alvo = j.jogador, j.luta.rival
    alvo.vida = alvo.vida_max = 500  # o rival aguenta os botes
    invocar(jog, [3, 4, "caes_divinos"])
    anda(tela, 0.1)
    cao = _vivas(tela, jog)[0]
    _golpe(tela, e)
    acao = j.luta.log[-1]
    assert acao.invocadas and acao.invocadas[0][0] == "caes_divinos"
    assert cao.bote is not None and cao.bote[1] is alvo
    assert tela.golpe[1] > cao.bote[0]  # o golpe do dono espera a mordida
    assert tela._camada(cao) == "bote"
    tela.render(None, Nulo())


def test_os_clones_aparecem_e_somem_numa_nuvem():
    j = _luta()
    tela, _e = _tela(j)
    jog = j.jogador
    jog.clones = MAX_CLONES
    anda(tela, 0.1)
    assert len(_clones(tela, jog)) == MAX_CLONES
    tela.render(None, Nulo())  # 4 à vista e o "+1"
    nuvens = len(tela.nuvens)
    jog.clones = MAX_CLONES - 1  # absorveu um golpe
    anda(tela, 0.05)
    assert len(_clones(tela, jog)) == MAX_CLONES - 1
    assert len(tela.nuvens) == nuvens + 1  # estourou numa nuvem
    anda(tela, DURACAO_POOF + 0.1)
    assert len(tela.clones_em_campo) == MAX_CLONES - 1


def test_o_clone_que_absorve_um_golpe_de_verdade_some():
    j = _luta()
    tela, e = _tela(j)
    rival = j.luta.rival
    rival.vida = rival.vida_max = 999
    rival.clones = MAX_CLONES
    anda(tela, 0.1)
    for _ in range(20):
        antes = rival.clones
        _golpe(tela, e)
        anda(tela, 0.5)
        assert len(_clones(tela, rival)) == rival.clones  # a tela acompanha o motor
        if rival.clones < antes:
            break
    else:
        raise AssertionError("nenhum clone absorveu o golpe")
    assert any(n[2] >= tela.relogio - 1.0 for n in tela.nuvens)


def _ate_o_fim_da_animacao(tela, e, segurar=()):
    _golpe(tela, e)
    e.seguradas = set(segurar)
    quadros = 0
    while tela.relogio < tela.anim_ate:
        tela.update(None, 1 / 60)
        quadros += 1
    e.seguradas = set()
    return quadros


def test_segurar_acelera_a_animacao():
    normal = _ate_o_fim_da_animacao(*_tela(_luta()))
    tela, e = _tela(_luta())
    rapido = _ate_o_fim_da_animacao(tela, e, {"acelerar"})
    assert rapido * 2.5 <= normal
    tela2, e2 = _tela(_luta())
    com_enter = _ate_o_fim_da_animacao(tela2, e2, {"confirmar"})  # segurar Enter também
    assert com_enter * 2.5 <= normal
    # sem nada tocando e na vez do jogador, segurar não faz nada
    tela.anim_ate = tela.relogio
    tela.luta.vez = tela.j.jogador
    e.seguradas = {"acelerar"}
    tela.update(None, 1 / 60)
    assert not tela.acelerando


def test_golpe_forte_congela_a_cena_e_o_alvo_fica_branco():
    j = _luta()
    tela, e = _tela(j)
    alvo = j.luta.rival
    alvo.vida = alvo.vida_max = 200
    j.jogador.bonus_dano += 60
    _golpe(tela, e)
    assert tela.parada is not None and tela.flash is not None and tela.flash[0] is alvo
    for _ in range(120):
        tela.update(None, 1 / 120)
        if tela.congelado > 0:
            break
    assert tela.congelado > 0
    parado = tela.relogio
    tela.update(None, 1 / 120)
    assert tela.relogio == parado  # o hit-stop: a cena não anda
    clarao, cor = tela._clarao(alvo)
    assert clarao == 1.0 and cor[:3] == (255, 255, 255)
    tela.render(None, Nulo())
    anda(tela, 0.5)
    assert tela.relogio > parado

"""A tela de luta contra um bando: mirar, pular quem caiu, a vez de cada rival e a luta inteira."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound.combate import escolher_alvo_auto, escolher_jogador_auto  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.run import escolher_porta  # noqa: E402
from karmabound.tela_luta import LutaScene  # noqa: E402

TRIO = ("lamina", "guardiao", "curandeiro")


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas


def aperta(cena, e, *teclas, passo=1 / 30):
    e.apertadas = set(teclas)
    cena.update(None, passo)
    e.apertadas = set()


def _bando(papeis=TRIO, seed=11, tipo="bando"):
    j = Jornada.nova("dificil", seed=seed)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    escolher_porta(j.estado, j.ctx.caminho.porta(tipo, papeis=papeis))
    j._comecar_luta()
    return j


def _tela(j, fim=None):
    e = Entrada()
    dicas = []
    tela = LutaScene(j, e, fim or (lambda v: None), lambda: None, dicas.append)
    tela.entrada_ate = 0
    tela.relogio = 1.0
    tela.anim_ate = tela.proxima_rival = 0
    return tela, e, dicas


def test_o_bando_aparece_com_titulos_e_cada_um_no_seu_lugar():
    j = _bando()
    tela, _e, _d = _tela(j)
    rivais = j.luta.rivais
    assert tela.bando and len(rivais) == 3
    xs = [tela._centro(r)[0] for r in rivais]
    assert xs == sorted(xs) and len(set(xs)) == 3  # lado a lado, sem empilhar
    assert {tela._titulo(r) for r in rivais} == {"Lâmina", "Guardião", "Curandeiro"}
    for r in rivais:  # as técnicas de papel têm nome e kanji na tela
        for t in r.tecnicas:
            assert tela.kanji.get(t.id, "?") != "?", t.id
            assert tela._nome(t.id)


def test_trocar_alvo_com_cima_baixo_e_alvo():
    j = _bando()
    tela, e, _d = _tela(j)
    luta = j.luta
    tela.anim_ate = 999  # trocar de alvo não espera a animação
    a, b, c = luta.rivais
    assert luta.rival is a
    aperta(tela, e, "baixo")
    assert luta.rival is b
    aperta(tela, e, "alvo")
    assert luta.rival is c
    aperta(tela, e, "alvo")
    assert luta.rival is a  # dá a volta
    aperta(tela, e, "cima")
    assert luta.rival is c


def test_o_alvo_pula_quem_caiu():
    j = _bando()
    tela, e, _d = _tela(j)
    luta = j.luta
    tela.anim_ate = 999
    a, b, c = luta.rivais
    b.vida = 0
    aperta(tela, e, "alvo")
    assert luta.rival is c
    aperta(tela, e, "alvo")
    assert luta.rival is a
    a.vida = 0  # o próprio alvo cai: a mira vai para quem está de pé
    aperta(tela, e)
    assert luta.rival is c
    aperta(tela, e, "alvo")  # só um de pé: nada a trocar
    assert luta.rival is c


def test_a_dica_de_alvo_so_com_mais_de_um_de_pe():
    j = _bando(("lamina", "curandeiro"))
    tela, _e, _d = _tela(j)
    textos = []

    class Renderer:
        def __getattr__(self, nome):
            return lambda *a, **k: None

        def draw_text(self, x, y, texto, *a, **k):
            textos.append(texto)

    tela._rodape(Renderer())
    assert any("Tab" in t for t in textos)
    j.luta.rivais[1].vida = 0
    textos.clear()
    tela._rodape(Renderer())
    assert not any("Tab" in t for t in textos)


def test_o_turno_dos_rivais_passa_por_todos_e_mantem_o_alvo():
    j = _bando()
    tela, e, _d = _tela(j)
    luta = j.luta
    luta.vez = j.jogador
    alvo = luta.rivais[1]
    luta.mirar(alvo)
    tela.cursor = 0
    aperta(tela, e, "confirmar")  # o Golpe, no Guardião
    assert luta.log[-1].ator == j.jogador.nome
    feitas = len(luta.log)
    for _ in range(2000):
        if luta.vez is j.jogador or luta.acabou:
            break
        aperta(tela, e, passo=1 / 10)
        if alvo.vivo:
            assert luta.rival is alvo  # o turno do rival não rouba a mira do jogador
    atores = [a.ator for a in luta.log[feitas:]]
    vivos = [r.nome for r in luta.ordem_rivais if r.vivo]
    assert set(vivos) <= set(atores)
    ordem = list(dict.fromkeys(atores))  # sem repetir quem ganhou ação extra
    assert ordem == [n for n in (r.nome for r in luta.ordem_rivais) if n in ordem]
    assert j.jogador.nome not in atores


@pytest.mark.parametrize(
    ("papeis", "tipo", "seed"),
    [
        (TRIO, "bando", 11),
        (("comandante", "guardiao", "xama"), "elite", 4),
        (("lamina",) * 2, "bando", 7),
    ],
)
def test_a_luta_de_bando_vai_ate_o_fim_pelas_telas(papeis, tipo, seed):
    from karmabound.game import build_game

    loop = build_game(seed=1)
    j = _bando(papeis, seed=seed, tipo=tipo)
    j.jogador.vida = j.jogador.vida_max = 400  # para a luta passar por mortes no bando
    resultado = []
    tela, e, dicas = _tela(j, resultado.append)
    luta = j.luta
    for _ in range(20_000):
        if resultado:
            break
        teclas = set()
        if tela.modo == "fim" and tela.relogio >= tela.anim_ate:
            teclas = {"confirmar"}
        elif luta.vez is j.jogador and not luta.acabou and tela.relogio >= tela.anim_ate:
            querido = escolher_alvo_auto(luta)
            if querido is not luta.rival:
                teclas = {"alvo"}
            else:
                t = escolher_jogador_auto(luta)
                teclas = {f"tecnica_{tela.slots().index(t) + 1}"}
        aperta(tela, e, *teclas, passo=1 / 15)
        loop.renderer.begin_frame()
        tela.render(None, loop.renderer)
    loop.renderer.shutdown()
    assert resultado, "a luta de bando não terminou"
    assert resultado == [True]
    assert all(not r.vivo for r in luta.rivais)
    assert "bando" in dicas
    nomes = {r.nome for r in luta.rivais}
    assert any(a.ator in nomes for a in luta.log)  # os rivais agiram

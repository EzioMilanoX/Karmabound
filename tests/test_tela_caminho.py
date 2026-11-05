"""As telas do caminho: as três portas e a encruzilhada (cursor, confirmar, opção bloqueada)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound.game import build_game  # noqa: E402
from karmabound.jornada import Jornada  # noqa: E402
from karmabound.tela_caminho import CaminhoScene, EncruzilhadaScene  # noqa: E402

PASSO = 1 / 30


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao: str) -> bool:
        return acao in self.apertadas


@pytest.fixture(scope="module")
def renderer():
    loop = build_game(seed=1)
    yield loop.renderer
    loop.renderer.shutdown()


@pytest.fixture
def jornada():
    j = Jornada.nova("acessivel", seed=7)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    assert j.fase == "caminho" and j.oferta_caminho[0].tipo == "rival"
    return j


def montar(cena_cls, j, renderer):
    entrada = Entrada()
    concluiu = []
    cena = cena_cls(j, entrada, lambda: concluiu.append(True), lambda: None)

    def quadro(teclas=()):
        entrada.apertadas = set(teclas)
        cena.update(None, PASSO)
        entrada.apertadas = set()
        renderer.begin_frame()
        cena.render(None, renderer)

    return cena, quadro, concluiu


def evento(j, eid):
    return next(e for e in j.ctx.caminho.eventos if e.id == eid)


def test_as_portas_andam_com_o_cursor_e_desenham_todo_tipo(jornada, renderer):
    cam = jornada.ctx.caminho
    jornada.oferta_caminho = (
        cam.porta("bando", papeis=("lamina", "guardiao", "curandeiro")),
        cam.porta("evento", evento=evento(jornada, "fonte")),
        cam.porta("nemesis"),
    )
    cena, quadro, concluiu = montar(CaminhoScene, jornada, renderer)
    quadro()
    assert cena.cursor == 0
    quadro({"direita"})
    assert cena.cursor == 1
    quadro({"direita"})
    quadro({"direita"})  # dá a volta
    assert cena.cursor == 0
    quadro({"esquerda"})
    assert cena.cursor == 2 and not concluiu
    jornada.oferta_caminho = (cam.porta("rival"), cam.porta("elite", papeis=("comandante",)))
    cena.cursor = 1
    quadro()  # a elite com Comandante também desenha


def test_confirmar_a_porta_do_rival_comeca_a_luta(jornada, renderer):
    cena, quadro, concluiu = montar(CaminhoScene, jornada, renderer)
    assert jornada.oferta_caminho[0].tipo == "rival"
    quadro({"confirmar"})
    assert concluiu and jornada.fase == "luta" and jornada.luta is not None


def test_o_numero_escolhe_a_encruzilhada(jornada, renderer):
    cam = jornada.ctx.caminho
    jornada.oferta_caminho = (
        cam.porta("rival"),
        cam.porta("bando", papeis=("lamina", "xama")),
        cam.porta("evento", evento=evento(jornada, "forja")),
    )
    cena, quadro, concluiu = montar(CaminhoScene, jornada, renderer)
    quadro({"escolher_3"})
    assert concluiu and jornada.fase == "encruzilhada"
    assert jornada.encruzilhada.id == "forja"


def test_opcao_sem_carma_fica_apagada_e_nao_confirma(jornada, renderer):
    jornada.oferta_caminho = ()
    jornada.encruzilhada, jornada.fase = evento(jornada, "mercador"), "encruzilhada"
    jornada.carma.valor = 0  # a troca por Técnica custa 40 de Carma
    cena, quadro, concluiu = montar(EncruzilhadaScene, jornada, renderer)
    quadro()
    quadro({"baixo"})
    assert cena.cursor == 1 and not jornada.pode_escolher(1)
    quadro({"confirmar"})
    assert not concluiu and jornada.fase == "encruzilhada"
    assert cena.aviso == "Carma insuficiente"
    quadro({"escolher_2"})  # pelo número também não
    assert not concluiu and jornada.fase == "encruzilhada"
    quadro({"baixo"})  # mover apaga o aviso
    assert cena.cursor == 2 and cena.aviso == ""
    quadro({"cima"})
    jornada.carma.valor = 50  # agora cabe: a escolha leva ao giro de Técnica
    quadro({"confirmar"})
    assert concluiu and jornada.fase == "tecnica" and jornada.carma.valor == 10


def test_seguir_caminho_volta_as_portas(jornada, renderer):
    jornada.oferta_caminho = ()
    jornada.encruzilhada, jornada.fase = evento(jornada, "mercador"), "encruzilhada"
    n = jornada.estado.proxima_luta
    cena, quadro, concluiu = montar(EncruzilhadaScene, jornada, renderer)
    quadro({"escolher_3"})  # "Seguir caminho."
    assert concluiu and jornada.encruzilhada is None
    assert jornada.estado.proxima_luta == n + 1
    assert jornada.fase in ("caminho", "luta")

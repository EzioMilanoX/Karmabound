"""Jogar de controle: toda ação tem um botão, e toda escolha anda pelo cursor."""

import json
from pathlib import Path

from karmabound.combate import Tecnica
from karmabound.jornada import Jornada
from karmabound.tela_menus import SubstituirScene
from karmabound.tela_roleta import RoletaScene

RAIZ = Path(__file__).resolve().parent.parent


class Entrada:
    def __init__(self):
        self.apertadas = set()

    def is_action_pressed(self, acao):
        return acao in self.apertadas


def aperta(cena, e, *teclas):
    e.apertadas = set(teclas)
    cena.update(None, 1 / 30)
    e.apertadas = set()


def test_toda_acao_essencial_tem_botao_de_controle():
    controles = json.loads((RAIZ / "karmabound" / "data" / "controles.json").read_text("utf-8"))
    for acao in (
        "esquerda",
        "direita",
        "cima",
        "baixo",
        "confirmar",
        "cancelar",
        "sair",
        "despertar",
        "girar",
    ):
        codigos = controles[acao] if isinstance(controles[acao], list) else [controles[acao]]
        assert any(c.startswith("PAD") for c in codigos), acao


def _cheia():
    j = Jornada.nova("dificil", seed=5)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    while len(j.jogador.tecnicas) < 4:
        fatia = next(
            f
            for f in j.ctx.tecnicas.values()
            if f.combate and f.id not in {t.id for t in j.jogador.tecnicas}
        )
        j.jogador.tecnicas.append(Tecnica.de_fatia(fatia))
    j.pendente = next(
        f
        for f in j.ctx.tecnicas.values()
        if f.combate and f.id not in {t.id for t in j.jogador.tecnicas}
    )
    j.fase = "substituir"
    return j


def test_troca_de_tecnica_pelo_cursor():
    j = _cheia()
    e = Entrada()
    fim = []
    tela = SubstituirScene(j, e, lambda: fim.append(1), lambda: None)
    sai = j.jogador.tecnicas[1]
    aperta(tela, e, "baixo")
    aperta(tela, e, "confirmar")
    assert fim and sai not in j.jogador.tecnicas


def test_escolher_uma_de_tres_pelo_cursor():
    j = Jornada.nova("dificil", seed=6)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    e = Entrada()
    escolhida = []
    tela = RoletaScene(
        j.estado.mesa,
        e,
        lambda: None,
        "tecnicas",
        lambda: j.estado.mesa.girar("tecnicas"),
        escolhida.append,
        jornada=j,
    )
    aperta(tela, e, "girar")
    for _ in range(int(6 * 30)):
        tela.update(None, 1 / 30)
    assert tela.estado == "escolhendo"
    aperta(tela, e, "direita")
    aperta(tela, e, "confirmar")
    assert tela.estado == "resultado" and tela.escolhida == 1


def test_sacrificio_do_contrato_pelo_cursor():
    from karmabound.tela_luta import LutaScene

    j = Jornada.nova("dificil", seed=7)
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    contrato = Tecnica.de_fatia(j.ctx.tecnicas["contrato"])
    j.jogador.tecnicas.append(contrato)
    luta = j.luta
    luta.vez = j.jogador
    e = Entrada()
    tela = LutaScene(j, e, lambda v: None, lambda: None)
    tela.relogio = tela.anim_ate = 0
    tela.entrada_ate = 0
    slots = tela.slots()
    tela.cursor = slots.index(contrato)
    tela.anim_ate = -1
    aperta(tela, e, "confirmar")  # escolhe o Contrato: pede o sacrifício
    assert tela.modo == "sacrificio"
    tela.cursor = 1  # o Golpe Direto
    alvo = slots[1]
    aperta(tela, e, "confirmar")
    assert alvo not in j.jogador.tecnicas


def test_o_jogo_carrega_os_botoes_do_controle():
    import os

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    from karmabound.game import build_game

    loop = build_game(seed=1)  # a engine resolve PAD_* sem erro, mesmo sem controle conectado
    loop.renderer.shutdown()

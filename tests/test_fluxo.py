"""O jogo inteiro, sem janela: do título ao fim da run, apertando teclas como uma pessoa.

Cada quadro passa por update e render de verdade, então uma tela que quebra ao
desenhar algum estado raro (Contrato, Altar, Despertar) quebra aqui.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from karmabound.combate import escolher_jogador_auto  # noqa: E402
from karmabound.game import build_game  # noqa: E402
from karmabound.tela_caminho import CaminhoScene, EncruzilhadaScene  # noqa: E402
from karmabound.tela_luta import LutaScene  # noqa: E402
from karmabound.tela_menus import (  # noqa: E402
    AliadoScene,
    AltarScene,
    FimScene,
    FusaoScene,
    SubstituirScene,
    TituloScene,
    TreinoScene,
)
from karmabound.tela_roleta import RoletaScene  # noqa: E402

PASSO = 1 / 30


class Entrada:
    def __init__(self):
        self.apertadas: set[str] = set()

    def is_action_pressed(self, acao: str) -> bool:
        return acao in self.apertadas


def luta_dom(cena):
    return cena.j.jogador.tecnica_dom


def decidir(cena) -> set[str]:
    """Que tecla uma pessoa apertaria agora."""
    if isinstance(cena, TituloScene):
        return {"confirmar"}
    if isinstance(cena, (FusaoScene, AliadoScene)):  # o anúncio: Enter mostra, Enter segue
        return {"confirmar"}
    if isinstance(cena, RoletaScene):
        return {
            "parado": {"girar"},
            "escolhendo": {"escolher_1"},
            "resultado": {"confirmar"},
        }.get(cena.estado, set())
    if isinstance(cena, LutaScene):
        if cena.relogio < cena.anim_ate:
            return set()
        if cena.modo == "fim":
            return {"confirmar"}
        if cena.modo == "sacrificio":
            alvos = [
                i
                for i, t in enumerate(cena.slots())
                if t is not None and i > 0 and t is not cena.contrato and t is not luta_dom(cena)
            ]
            return {f"tecnica_{alvos[0] + 1}"} if alvos else {"cancelar"}
        luta = cena.luta
        if luta.acabou or luta.vez is not luta.jogador:
            return set()
        t = escolher_jogador_auto(luta)
        return {f"tecnica_{cena.slots().index(t) + 1}"}
    if isinstance(cena, SubstituirScene):
        return {"tecnica_1"}
    if isinstance(cena, TreinoScene):
        return {"confirmar"}
    if isinstance(cena, CaminhoScene):
        # a encruzilhada quando houver (passa pela outra tela); senão o Rival (porta 1)
        tipos = [p.tipo for p in cena.j.oferta_caminho]
        return {f"escolher_{tipos.index('evento') + 1}" if "evento" in tipos else "confirmar"}
    if isinstance(cena, EncruzilhadaScene):
        j = cena.j
        cabe = next(i for i in range(len(j.encruzilhada.opcoes)) if j.pode_escolher(i))
        return {f"escolher_{cabe + 1}"}
    if isinstance(cena, AltarScene):
        if cena.estado == "escolher":
            cena.cursor = cena.linhas.index("recusar")
            return {"confirmar"}
        return set()
    return set()


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_uma_run_inteira_pelas_telas(seed):
    loop = build_game(seed=seed)
    entrada = Entrada()
    loop._input_provider = entrada
    loop.fluxo.titulo()
    vistas = set()
    for _ in range(40_000):
        cena = loop.current_scene
        vistas.add(type(cena).__name__)
        if isinstance(cena, FimScene):
            break
        entrada.apertadas = decidir(cena)
        cena.update(None, PASSO)
        entrada.apertadas = set()
        loop.renderer.begin_frame()
        loop.current_scene.render(None, loop.renderer)
    else:
        pytest.fail(f"a run não terminou; parou em {type(loop.current_scene).__name__}")
    j = loop.fluxo.jornada
    assert j.fase in ("vitoria", "derrota")
    assert {"TituloScene", "RoletaScene", "LutaScene", "FimScene"} <= vistas
    if j.estado.lutas_vencidas:
        assert "TreinoScene" in vistas
        assert "CaminhoScene" in vistas
    assert loop.fluxo.legado.memoria > 0 or not j.estado.lutas_vencidas  # o Legado registrou
    loop.renderer.shutdown()


def test_altar_desenha_todos_os_estados():
    from karmabound.jornada import Jornada

    loop = build_game(seed=1)
    j = Jornada.nova("acessivel", seed=5)
    j.amostras_altar = 10
    j.girar_linhagem()
    j.girar_destino()
    j.girar_arco()
    j.estado.altar_pendente = True  # o capítulo acabou
    j._proxima_luta()
    entrada = Entrada()
    concluiu = []
    cena = AltarScene(j, entrada, lambda: concluiu.append(True), lambda: None)

    def quadro(teclas=()):
        entrada.apertadas = set(teclas)
        cena.update(None, PASSO)
        entrada.apertadas = set()
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)

    quadro()
    quadro()  # mede
    assert cena.estado == "escolher" and cena.pesos
    cena.cursor = 0
    quadro({"confirmar"})  # marca a 1ª restrição
    cena.cursor = cena.linhas.index("pesar")
    quadro({"confirmar"})
    quadro()
    quadro()  # mede o voto
    assert cena.estado == "comprar" and cena.proposta is not None
    quadro({"cancelar"})
    assert cena.estado == "escolher"
    loop.renderer.shutdown()

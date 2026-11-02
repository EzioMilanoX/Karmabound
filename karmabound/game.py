"""Composição: a OuroborosEngine com o fluxo da run por cima.

O `Fluxo` olha a fase da `Jornada` e põe a tela certa no topo da pilha; cada
tela, ao terminar, chama de volta `Fluxo.passo`. Nenhuma regra mora aqui.
"""

from __future__ import annotations

from pathlib import Path

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop

from karmabound.grimorio import Grimorio
from karmabound.jornada import Jornada
from karmabound.mesa import Mesa
from karmabound.rodas import DADOS
from karmabound.tela_grimorio import GrimorioScene
from karmabound.tela_luta import LutaScene
from karmabound.tela_menus import AltarScene, FimScene, SubstituirScene, TituloScene
from karmabound.tela_roleta import RoletaScene
from karmabound.visual import ALTURA, FONTE_PINCEL, LARGURA

FONTES = Path(__file__).resolve().parent.parent / "assets" / "fonts"

TITULOS_RODA = {
    "destino": "Seu destino",
    "arco": "O arco do capítulo",
    "tecnicas": "Uma técnica nova",
    "reliquias": "Uma relíquia",
}


def _montar_loop() -> GameLoop:
    config = EngineConfig(
        window_width=LARGURA,
        window_height=ALTURA,
        window_title="Karmabound",
        entity_capacity=8,  # o jogo não usa entidades; o World só precisa existir
        difficulty_path=str(DADOS / "balanceamento.json"),
        input_bindings_path=str(DADOS / "controles.json"),
    )
    loop = CompositionRoot(config).build()
    loop.renderer.load_font(FONTE_PINCEL, str(FONTES / "YujiSyuku-Regular.ttf"))
    return loop


class Fluxo:
    def __init__(self, loop: GameLoop, seed: int | None = None) -> None:
        self.loop = loop
        self.seed = seed
        self.jornada: Jornada | None = None
        self.grimorio = Grimorio.padrao()

    @property
    def entrada(self):
        return self.loop.input_provider

    def _cena(self, cena) -> None:
        self.loop.reset_scenes(cena)

    def titulo(self) -> None:
        self.jornada = None
        self._cena(TituloScene(self.entrada, self.comecar, self.loop.stop, self.abrir_grimorio))

    def abrir_grimorio(self) -> None:
        self._cena(GrimorioScene(self.grimorio, self.entrada, self.titulo, self.loop.stop))

    def comecar(self, modo: str) -> None:
        self.jornada = Jornada.nova(modo, self.seed)
        self.jornada.grimorio = self.grimorio
        self.passo()

    def _roleta(self, roda: str, girar, depois) -> None:
        j = self.jornada
        titulo = TITULOS_RODA[roda]
        if roda == "arco":
            titulo = f"Capítulo {j.capitulo}: {titulo.lower()}"
        self._cena(
            RoletaScene(
                j.estado.mesa,
                self.entrada,
                self.loop.stop,
                roda_fixa=roda,
                girar=girar,
                ao_concluir=depois,
                titulo=titulo,
                jornada=j,
            )
        )

    def passo(self, *_args) -> None:
        """Mostra a tela da fase atual da Jornada."""
        j = self.jornada
        fase = j.fase
        if fase == "destino":
            self._roleta("destino", j.girar_destino, self.passo)
        elif fase == "arco":
            self._roleta("arco", j.girar_arco, self.passo)
        elif fase == "luta":
            self._cena(LutaScene(j, self.entrada, self._fim_da_luta, self.loop.stop))
        elif fase == "tecnica":
            self._roleta("tecnicas", j.girar_tecnica, self._tecnica_escolhida)
        elif fase == "substituir":
            self._cena(SubstituirScene(j, self.entrada, self.passo, self.loop.stop))
        elif fase == "altar":
            self._cena(AltarScene(j, self.entrada, self.passo, self.loop.stop))
        elif fase == "reliquia":
            self._roleta("reliquias", j.girar_reliquia, self.passo)
        else:  # vitoria | derrota
            self._cena(FimScene(j, self.entrada, self.titulo, self.loop.stop))

    def _fim_da_luta(self, _venceu: bool) -> None:
        self.jornada.terminar_luta()
        self.passo()

    def _tecnica_escolhida(self, indice: int) -> None:
        self.jornada.escolher_tecnica(indice)
        self.passo()


def build_game(seed: int | None = None, roleta: bool = False) -> GameLoop:
    """O jogo completo (título → run). `roleta=True`: só a caixa de areia da roleta."""
    loop = _montar_loop()
    if roleta:
        loop.reset_scenes(RoletaScene(Mesa.padrao(seed), loop.input_provider, ao_sair=loop.stop))
    else:
        fluxo = Fluxo(loop, seed)
        loop.fluxo = fluxo  # para testes e ferramentas chegarem ao fluxo
        fluxo.titulo()
    return loop


def run(headless: bool = False, roleta: bool = False) -> None:
    """Abre o jogo. headless=True desenha um quadro e sai (para testes)."""
    loop = build_game(roleta=roleta)
    if headless:
        loop.tick_once(1 / 60)
        loop.renderer.shutdown()
        return
    try:
        loop.run()
    finally:
        loop.renderer.shutdown()

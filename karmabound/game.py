"""Composição: a OuroborosEngine com o fluxo da run por cima.

O `Fluxo` olha a fase da `Jornada` e põe a tela certa no topo da pilha; cada
tela, ao terminar, chama de volta `Fluxo.passo`. Nenhuma regra mora aqui.

Por cima das telas da run, o Fluxo empilha a pausa (Esc), as opções, a quebra de
um voto e as dicas da primeira run; cada uma desempilha ao fechar.
"""

from __future__ import annotations

from pathlib import Path

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop

from karmabound import opcoes
from karmabound.grimorio import Grimorio
from karmabound.jornada import Jornada
from karmabound.mesa import Mesa
from karmabound.rodas import DADOS
from karmabound.som import SOM
from karmabound.tela_grimorio import GrimorioScene
from karmabound.tela_luta import LutaScene
from karmabound.tela_menus import AltarScene, FimScene, SubstituirScene, TituloScene
from karmabound.tela_pausa import DicaScene, OpcoesScene, PausaScene, VotosScene
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
    escolhas = opcoes.configurar()
    SOM.configurar(loop.audio_engine)
    if escolhas.tela_cheia:
        try:
            loop.renderer.set_fullscreen(True)
        except Exception:
            escolhas.tela_cheia = False
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
        self._cena(
            TituloScene(
                self.entrada,
                self.comecar,
                self.loop.stop,
                self.abrir_grimorio,
                ao_opcoes=lambda: self.abrir_opcoes(self.loop.current_scene),
            )
        )

    def abrir_grimorio(self) -> None:
        self._cena(GrimorioScene(self.grimorio, self.entrada, self.titulo, self.titulo))

    # ------------------------------------------------------------------ por cima das telas

    def _fechar(self) -> None:
        self.loop.pop_scene()

    def pausar(self) -> None:
        """Esc numa tela da run: a pausa por cima dela."""
        baixo = self.loop.current_scene
        self.loop.push_scene(
            PausaScene(baixo, self.jornada, self.entrada, self._fechar, self.loop.stop, self)
        )

    def abrir_opcoes(self, baixo) -> None:
        self.loop.push_scene(
            OpcoesScene(baixo, self.entrada, self._fechar, self.loop.stop, self.loop.renderer)
        )

    def abrir_votos(self, baixo) -> None:
        self.loop.push_scene(
            VotosScene(baixo, self.jornada, self.entrada, self._fechar, self.loop.stop, self.passo)
        )

    def dica(self, dica_id: str) -> None:
        """A dica da primeira vez de cada sistema (uma vez só, e só com as dicas ligadas)."""
        if opcoes.OPCOES.mostrar_dica(dica_id):
            baixo = self.loop.current_scene
            self.loop.push_scene(
                DicaScene(baixo, dica_id, self.entrada, self._fechar, self.loop.stop)
            )

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
        self.loop.current_scene.ao_sair = self.pausar

    def passo(self, *_args) -> None:
        """Mostra a tela da fase atual da Jornada."""
        j = self.jornada
        fase = j.fase
        if fase == "destino":
            self._roleta("destino", j.girar_destino, self.passo)
        elif fase == "arco":
            self._roleta("arco", j.girar_arco, self.passo)
        elif fase == "luta":
            self._cena(LutaScene(j, self.entrada, self._fim_da_luta, self.pausar, self.dica))
        elif fase == "tecnica":
            self._roleta("tecnicas", j.girar_tecnica, self._tecnica_escolhida)
        elif fase == "substituir":
            self._cena(SubstituirScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "altar":
            self._cena(AltarScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "reliquia":
            self._roleta("reliquias", j.girar_reliquia, self.passo)
        else:  # vitoria | derrota
            self._cena(FimScene(j, self.entrada, self.titulo, self.loop.stop))
            return
        dica = {
            "destino": "roleta",
            "arco": "arco",
            "luta": "luta",
            "tecnica": "tecnicas",
            "substituir": "espacos",
            "altar": "altar",
            "reliquia": "reliquia",
        }[fase]
        self.dica(dica)

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

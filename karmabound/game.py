"""Composição: monta a OuroborosEngine com a tela da roleta por cima."""

from __future__ import annotations

from pathlib import Path

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop

from karmabound.mesa import Mesa
from karmabound.rodas import DADOS
from karmabound.tela_roleta import ALTURA, FONTE_PINCEL, LARGURA, RoletaScene

FONTES = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def build_game(seed: int | None = None) -> GameLoop:
    config = EngineConfig(
        window_width=LARGURA,
        window_height=ALTURA,
        window_title="Karmabound",
        entity_capacity=8,  # a roleta não usa entidades; o World só precisa existir
        difficulty_path=str(DADOS / "balanceamento.json"),
        input_bindings_path=str(DADOS / "controles.json"),
    )
    loop = CompositionRoot(config).build()
    loop.renderer.load_font(FONTE_PINCEL, str(FONTES / "YujiSyuku-Regular.ttf"))
    loop.reset_scenes(RoletaScene(Mesa.padrao(seed), loop.input_provider, ao_sair=loop.stop))
    return loop


def run(headless: bool = False) -> None:
    """Abre a roleta. headless=True desenha um quadro e sai (para testes)."""
    loop = build_game()
    if headless:
        loop.tick_once(1 / 60)
        loop.renderer.shutdown()
        return
    try:
        loop.run()
    finally:
        loop.renderer.shutdown()

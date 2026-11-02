"""Renderiza os estados da roleta em PNG, sem janela: python tools/capturar_telas.py [pasta]

Padrão: docs/telas/ (as imagens de referência do visual, versionadas com o projeto).

Serve para revisar o visual sem jogar até cada estado. Seed fixa: as imagens
saem iguais a cada execução enquanto o código não mudar.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from karmabound.game import build_game  # noqa: E402
from karmabound.tela_roleta import DURACAO_QUEBRA, RoletaScene  # noqa: E402


def capturar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    loop = build_game(seed=3)
    cena: RoletaScene = loop.current_scene
    carma = cena.mesa.carma
    salvos: list[Path] = []

    def foto(nome: str) -> None:
        loop.renderer.begin_frame()
        cena.render(None, loop.renderer)
        caminho = destino / f"{nome}.png"
        pygame.image.save(pygame.display.get_surface(), str(caminho))
        salvos.append(caminho)

    def avancar(segundos: float) -> None:
        passo = 1 / 60
        for _ in range(int(segundos / passo)):
            cena.update(None, passo)

    foto("01_parado")

    cena._comecar_giro()
    avancar(0.9)
    foto("02_girando")
    avancar(3)
    foto("03_resultado")

    cena.i_roda = 1  # Técnicas: gira 3, escolhe 1
    cena._ir("parado")
    cena._comecar_giro()
    avancar(4)
    foto("04_escolhendo")
    cena.escolhida, cena.aceso = 0, cena.alvos[0]
    cena._ir("resultado")
    foto("05_tecnica_escolhida")

    cena.i_roda = 0
    cena._ir("parado")
    cena.giro = None
    carma.valor = 80
    cena.carma_visual = 80
    foto("06_carma_pity_suave")
    carma.valor = carma.config.maximo
    cena.carma_visual = carma.valor
    foto("07_carma_transbordando")

    cena._comecar_giro()  # vira o Despertar
    avancar(DURACAO_QUEBRA * 0.15)
    foto("08_quebra_inicio")
    avancar(DURACAO_QUEBRA * 0.45)
    foto("09_quebra_meio")
    avancar(5)
    foto("10_despertar_resultado")

    loop.renderer.shutdown()
    return salvos


if __name__ == "__main__":
    padrao = Path(__file__).resolve().parent.parent / "docs" / "telas"
    pasta = Path(sys.argv[1]) if len(sys.argv) > 1 else padrao
    for p in capturar(pasta):
        print(p)

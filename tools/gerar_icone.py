"""Desenha o ícone do jogo: python tools/gerar_icone.py

O kanji 業 (Carma) em dourado, na fonte de pincel, sobre laca escura com um ensō.
Sai assets/karmabound.ico (16 a 256 px) e assets/karmabound.png.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
TAM = 256


def desenhar() -> pygame.Surface:
    pygame.init()
    s = pygame.Surface((TAM, TAM), pygame.SRCALPHA)
    pygame.draw.rect(s, (20, 18, 16, 255), (0, 0, TAM, TAM), border_radius=44)
    centro = TAM / 2
    for k in range(60):  # o ensō: um traço que engrossa e afina
        a0 = math.radians(110 + k * 5.4)
        a1 = math.radians(110 + (k + 1) * 5.4)
        largura = int(4 + 9 * math.sin(math.pi * k / 60))
        p0 = (centro + math.cos(a0) * 104, centro - math.sin(a0) * 104)
        p1 = (centro + math.cos(a1) * 104, centro - math.sin(a1) * 104)
        pygame.draw.line(s, (196, 30, 36, 255), p0, p1, largura)
    fonte = pygame.font.Font(str(RAIZ / "assets" / "fonts" / "YujiSyuku-Regular.ttf"), 150)
    kanji = fonte.render("業", True, (233, 196, 106))
    s.blit(kanji, kanji.get_rect(center=(centro, centro + 6)))
    return s


def gerar() -> Path:
    png = RAIZ / "assets" / "karmabound.png"
    pygame.image.save(desenhar(), str(png))
    ico = RAIZ / "assets" / "karmabound.ico"
    Image.open(png).save(
        ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    return ico


if __name__ == "__main__":
    print(gerar())

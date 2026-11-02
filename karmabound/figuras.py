"""Silhuetas de tinta: lutadores desenhados com polígonos, sem arte.

Uma figura de hakama com espada, em pinceladas: o corpo sólido e duas
passadas deslocadas com pouca opacidade, que dão a borda irregular de pincel.
Rosto não há — é silhueta —, então a mesma figura serve de frente e de costas.
"""

from __future__ import annotations

import math

from ouroboros.interfaces.renderer import IRenderer

from karmabound.visual import Cor, alpha, mistura


def _poligono(r: IRenderer, pontos, cor: Cor, x: float, y: float, e: float) -> None:
    r.draw_ui_polygon([(x + px * e, y + py * e) for px, py in pontos], cor)


# Coordenadas da figura em unidades, com (0, 0) nos pés; y cresce para baixo.
_CABECA = (0, -112, 13)
_TORSO = [(-26, -96), (26, -96), (19, -52), (-19, -52)]
_HAKAMA = [(-19, -54), (19, -54), (34, 0), (6, 0), (0, -26), (-6, 0), (-34, 0)]
_BRACO_ESQ = [(-26, -94), (-18, -90), (-30, -50), (-38, -54)]
_BRACO_DIR = [(26, -94), (18, -90), (22, -50), (32, -50)]
_FAIXA = [(-21, -58), (21, -58), (20, -50), (-20, -50)]


def desenhar_lutador(
    r: IRenderer,
    x: float,
    y: float,
    escala: float,
    cor: Cor,
    contorno: Cor,
    espada: bool = True,
    guarda: float = 0.0,
    clarao: float = 0.0,
    clarao_cor: Cor = (255, 255, 255, 255),
) -> None:
    """Desenha a figura com os pés em (x, y).

    `guarda` (0–1) ergue a espada à frente do corpo; `clarao` (0–1) tinge a figura
    com `clarao_cor` (golpe recebido, Despertar).
    """
    e = escala
    corpo = mistura(cor, clarao_cor, clarao) if clarao > 0 else cor
    # sombra no chão: uma pincelada achatada
    r.draw_ui_polygon(
        [
            (x - 46 * e, y + 2 * e),
            (x + 46 * e, y + 2 * e),
            (x + 30 * e, y + 8 * e),
            (x - 34 * e, y + 7 * e),
        ],
        alpha(contorno, 40),
    )
    for dx, dy, a in ((-1.6, 0.8, 70), (1.4, -1.0, 60)):  # passadas de pincel deslocadas
        borda = alpha(contorno, a)
        for forma in (_TORSO, _HAKAMA, _BRACO_ESQ, _BRACO_DIR):
            _poligono(r, forma, borda, x + dx, y + dy, e)
        r.draw_ui_circle(x + dx, y + (_CABECA[1]) * e + dy, (_CABECA[2] + 1.5) * e, borda)
    for forma in (_HAKAMA, _TORSO, _BRACO_ESQ, _BRACO_DIR):
        _poligono(r, forma, corpo, x, y, e)
    _poligono(r, _FAIXA, mistura(corpo, contorno, 0.35), x, y, e)
    r.draw_ui_circle(x, y + _CABECA[1] * e, _CABECA[2] * e, corpo)
    # cabelo preso: um traço de pincel atrás da cabeça
    r.draw_ui_line(x + 6 * e, y - 122 * e, x + 20 * e, y - 128 * e, corpo, max(2, round(4 * e)))
    if espada:
        # a lâmina sai da mão direita; com guarda, sobe para a frente do peito
        ang = math.radians(-60 - 70 * guarda)
        mx, my = x + 28 * e, y - 50 * e
        comp = 92 * e
        fx, fy = mx + math.cos(ang) * comp, my + math.sin(ang) * comp
        r.draw_ui_line(
            mx, my, fx, fy, mistura(contorno, (255, 255, 255, 255), 0.25), max(2, round(3 * e))
        )
        r.draw_ui_line(
            mx - 6 * e, my + 3 * e, mx + 6 * e, my - 3 * e, contorno, max(2, round(4 * e))
        )

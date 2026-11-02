"""Silhuetas de tinta: lutadores desenhados com polígonos, sem arte.

Uma figura em pinceladas: o corpo sólido e duas passadas deslocadas com pouca
opacidade, que dão a borda irregular de pincel. Rosto não há — é silhueta —,
então a mesma figura serve de frente e de costas.

Estilos (os rivais variam; você é sempre o espadachim):
    espadachim  hakama e espada
    monge       manto longo, cajado com argolas e rosário
    ninja       cachecol ao vento e duas lâminas curtas
    oni         chifres, ombros largos e o kanabō
    colosso     o chefe: quatro braços, chifres em coroa, capa e uma lâmina enorme
"""

from __future__ import annotations

import math

from ouroboros.interfaces.renderer import IRenderer

from karmabound.visual import Cor, alpha, mistura

ESTILOS = ("espadachim", "monge", "ninja", "oni")
BRANCO = (255, 255, 255, 255)


def _poligono(r: IRenderer, pontos, cor: Cor, x: float, y: float, e: float) -> None:
    r.draw_ui_polygon([(x + px * e, y + py * e) for px, py in pontos], cor)


# Coordenadas da figura em unidades, com (0, 0) nos pés; y cresce para baixo.
_CABECA = (0, -112, 13)
_TORSO = [(-26, -96), (26, -96), (19, -52), (-19, -52)]
_HAKAMA = [(-19, -54), (19, -54), (34, 0), (6, 0), (0, -26), (-6, 0), (-34, 0)]
_BRACO_ESQ = [(-26, -94), (-18, -90), (-30, -50), (-38, -54)]
_BRACO_DIR = [(26, -94), (18, -90), (22, -50), (32, -50)]
_FAIXA = [(-21, -58), (21, -58), (20, -50), (-20, -50)]

_MANTO = [(-22, -56), (22, -56), (30, 0), (-30, 0)]  # monge: sem divisão de pernas
_TORSO_LARGO = [(-36, -98), (36, -98), (24, -50), (-24, -50)]  # oni e colosso
_BRACO_ESQ_LARGO = [(-36, -96), (-26, -92), (-38, -46), (-50, -52)]
_BRACO_DIR_LARGO = [(36, -96), (26, -92), (30, -46), (44, -46)]
_BRACOS_DE_BAIXO = (  # colosso: o segundo par, saindo da cintura
    [(-24, -74), (-18, -68), (-46, -40), (-52, -48)],
    [(24, -74), (18, -68), (46, -40), (52, -48)],
)
_CAPA = [(-30, -98), (30, -98), (48, 2), (-48, 2)]


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
    clarao_cor: Cor = BRANCO,
    estilo: str = "espadachim",
    tempo: float = 0.0,
) -> None:
    """Desenha a figura com os pés em (x, y).

    `guarda` (0–1) ergue a arma à frente do corpo; `clarao` (0–1) tinge a figura
    com `clarao_cor` (golpe recebido, Despertar); `tempo` anima tecido e cabelo.
    """
    e = escala
    corpo = mistura(cor, clarao_cor, clarao) if clarao > 0 else cor
    largo = estilo in ("oni", "colosso")
    torso = _TORSO_LARGO if largo else _TORSO
    bracos = [_BRACO_ESQ_LARGO, _BRACO_DIR_LARGO] if largo else [_BRACO_ESQ, _BRACO_DIR]
    if estilo == "colosso":
        bracos += list(_BRACOS_DE_BAIXO)
    pernas = _MANTO if estilo == "monge" else _HAKAMA
    formas = [torso, pernas, *bracos]

    # sombra no chão: uma pincelada achatada
    sombra = 1.4 if largo else 1.0
    r.draw_ui_polygon(
        [
            (x - 46 * e * sombra, y + 2 * e),
            (x + 46 * e * sombra, y + 2 * e),
            (x + 30 * e * sombra, y + 8 * e),
            (x - 34 * e * sombra, y + 7 * e),
        ],
        alpha(contorno, 40),
    )
    if estilo == "colosso":  # a capa vai atrás de tudo, balançando
        onda = math.sin(tempo * 1.7) * 5
        capa = [(px + (onda if py > -40 else 0), py) for px, py in _CAPA]
        _poligono(r, capa, mistura(corpo, (0, 0, 0, 255), 0.45), x, y, e)
    if estilo == "ninja":  # o cachecol ao vento, atrás da cabeça
        for k in range(2):
            pontos = []
            for i in range(7):
                px = -6 - i * 9
                py = -100 + i * 2 + math.sin(tempo * 6 + i * 0.8 + k) * (2 + i)
                pontos.append((x + px * e, y + (py + k * 5) * e))
            for a, b in zip(pontos, pontos[1:], strict=False):
                r.draw_ui_line(
                    a[0], a[1], b[0], b[1], mistura(corpo, BRANCO, 0.15), max(2, round(5 * e))
                )

    for dx, dy, a in ((-1.6, 0.8, 70), (1.4, -1.0, 60)):  # passadas de pincel deslocadas
        borda = alpha(contorno, a)
        for forma in formas:
            _poligono(r, forma, borda, x + dx, y + dy, e)
        r.draw_ui_circle(x + dx, y + (_CABECA[1]) * e + dy, (_CABECA[2] + 1.5) * e, borda)
    for forma in (pernas, torso, *bracos):
        _poligono(r, forma, corpo, x, y, e)
    if estilo != "monge":
        faixa = [(px * (1.3 if largo else 1), py) for px, py in _FAIXA]
        _poligono(r, faixa, mistura(corpo, contorno, 0.35), x, y, e)
    r.draw_ui_circle(x, y + _CABECA[1] * e, _CABECA[2] * e, corpo)

    if estilo == "espadachim":  # cabelo preso: um traço de pincel atrás da cabeça
        r.draw_ui_line(x + 6 * e, y - 122 * e, x + 20 * e, y - 128 * e, corpo, max(2, round(4 * e)))
    elif estilo == "ninja":  # a bandana
        r.draw_ui_line(
            x - 13 * e, y - 116 * e, x + 13 * e, y - 116 * e, contorno, max(2, round(3 * e))
        )
    elif estilo in ("oni", "colosso"):
        chifres = ((-8, -1), (8, 1)) if estilo == "oni" else ((-10, -1), (0, 0), (10, 1))
        for cx, lado in chifres:
            base_y = -122
            ponta = (cx + lado * 7, base_y - (18 if cx else 24))
            _poligono(r, [(cx - 4, base_y), (cx + 4, base_y), ponta], contorno, x, y, e)
    if estilo == "monge":  # o rosário no peito
        for i in range(9):
            a = math.pi * (0.15 + 0.7 * i / 8)
            r.draw_ui_circle(
                x + math.cos(a) * 15 * e, y + (-96 + math.sin(a) * 18) * e, 2.6 * e, contorno
            )

    if not espada:
        return
    mx, my = x + (32 if largo else 28) * e, y - 50 * e
    aço = mistura(contorno, BRANCO, 0.25)
    if estilo == "espadachim":
        # a lâmina sai da mão direita; com guarda, sobe para a frente do peito
        ang = math.radians(-60 - 70 * guarda)
        comp = 92 * e
        fx, fy = mx + math.cos(ang) * comp, my + math.sin(ang) * comp
        r.draw_ui_line(mx, my, fx, fy, aço, max(2, round(3 * e)))
        r.draw_ui_line(
            mx - 6 * e, my + 3 * e, mx + 6 * e, my - 3 * e, contorno, max(2, round(4 * e))
        )
    elif estilo == "monge":  # o shakujō, em pé ao lado
        topo = y - 150 * e
        r.draw_ui_line(mx + 4 * e, y, mx + 4 * e, topo, contorno, max(2, round(3 * e)))
        r.draw_ui_circle(mx + 4 * e, topo, 9 * e, contorno, max(1, round(2 * e)))
        for k in (-1, 1):
            r.draw_ui_circle(mx + (4 + k * 6) * e, topo + 8 * e, 3 * e, contorno, 1)
    elif estilo == "ninja":  # duas lâminas curtas, em guarda baixa
        for lado, (hx, hy) in ((-1, (x - 34 * e, y - 52 * e)), (1, (mx, my))):
            ang = math.radians(-90 + lado * (40 - 30 * guarda))
            r.draw_ui_line(
                hx,
                hy,
                hx + math.cos(ang) * 30 * e,
                hy + math.sin(ang) * 30 * e,
                aço,
                max(2, round(3 * e)),
            )
    elif estilo == "oni":  # o kanabō: um porrete grosso com cravos
        ang = math.radians(-70 - 50 * guarda)
        comp = 84 * e
        fx, fy = mx + math.cos(ang) * comp, my + math.sin(ang) * comp
        r.draw_ui_line(mx, my, fx, fy, contorno, max(4, round(9 * e)))
        for k in range(4):
            t = 0.45 + 0.15 * k
            px, py = mx + (fx - mx) * t, my + (fy - my) * t
            r.draw_ui_circle(px, py, 3.4 * e, aço)
    elif estilo == "colosso":  # uma lâmina enorme, erguida
        ang = math.radians(-80 - 30 * guarda)
        comp = 140 * e
        fx, fy = mx + math.cos(ang) * comp, my + math.sin(ang) * comp
        nx, ny = -math.sin(ang) * 7 * e, math.cos(ang) * 7 * e
        r.draw_ui_polygon([(mx + nx, my + ny), (fx, fy), (mx - nx, my - ny)], aço)
        r.draw_ui_line(
            mx - 10 * e, my + 4 * e, mx + 10 * e, my - 4 * e, contorno, max(3, round(5 * e))
        )

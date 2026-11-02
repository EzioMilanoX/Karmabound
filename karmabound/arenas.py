"""Arenas: o cenário de cada Arco, em tinta, desenhado só com primitivas.

Cada Arco homenageia um lugar (o Monte Myōboku, o Eclipse, Shibuya...). O
cenário fica atrás de tudo e com pouca opacidade: a luta é o que se lê. Tudo
é determinístico (senos, sem sorteio), então o mesmo quadro sai igual em
qualquer máquina e nas capturas.
"""

from __future__ import annotations

import math

from ouroboros.interfaces.renderer import IRenderer

from karmabound.visual import (
    ALTURA,
    FONTE_PINCEL,
    FUNDO,
    LARGURA,
    SANGUE_VIVO,
    TINTA,
    Cor,
    alpha,
    mistura,
)

HORIZONTE = 300  # onde o céu encontra o chão, logo abaixo do rival


def _ceu(r: IRenderer, topo: Cor, base: Cor, y0: float = 0, y1: float = HORIZONTE) -> None:
    faixas = 18
    altura = (y1 - y0) / faixas
    for i in range(faixas):
        r.draw_ui_rect(0, y0 + i * altura, LARGURA, altura + 1, mistura(topo, base, i / faixas))


def _serra(x0: float, x1: float, base: float, altura: float, freq: float, fase: float):
    """Contorno de montanha: soma de senos, fechado embaixo."""
    pontos = [(x0, base)]
    passos = 48
    for i in range(passos + 1):
        x = x0 + (x1 - x0) * i / passos
        y = base - altura * (
            0.55 + 0.3 * math.sin(x * freq + fase) + 0.15 * math.sin(x * freq * 2.7 + fase * 1.9)
        )
        pontos.append((x, y))
    pontos.append((x1, base))
    return pontos


def _particulas(r, relogio, n, cor, sobe: bool, tam=2.0, vel=30.0, deriva=12.0, semente=0):
    """Brasas, cinzas, pétalas: posições por seno, sem estado."""
    for i in range(n):
        s = i * 12.9898 + semente
        x0 = (math.sin(s) * 0.5 + 0.5) * LARGURA
        fase = (math.sin(s * 1.7) * 0.5 + 0.5) * ALTURA
        y = (fase + relogio * vel * (0.6 + 0.4 * math.sin(s * 3.1))) % (ALTURA + 40) - 20
        if sobe:
            y = ALTURA - y
        x = x0 + math.sin(relogio * 0.8 + s) * deriva
        r.draw_ui_circle(x, y, tam * (0.6 + 0.4 * math.sin(s * 5.3) ** 2), cor)


def _chao(r: IRenderer, cor: Cor) -> None:
    r.draw_ui_rect(0, HORIZONTE, LARGURA, ALTURA - HORIZONTE, cor)
    for k in range(5):  # pinceladas horizontais do chão
        y = HORIZONTE + 18 + k * 26
        r.draw_ui_line(60 + k * 37, y, LARGURA - 90 + k * 11, y, alpha(TINTA, 7), 2)


# ----------------------------------------------------------------------- arenas


def _montanha(r: IRenderer, t: float) -> None:
    """Treino no Monte Myōboku: montanhas em camadas, névoa e uma cachoeira."""
    _ceu(r, (24, 30, 28, 255), (42, 50, 44, 255))
    for k, (alt, cor, freq) in enumerate(
        (
            (190, (38, 46, 41, 255), 0.006),
            (150, (31, 38, 34, 255), 0.011),
            (95, (25, 30, 27, 255), 0.019),
        )
    ):
        r.draw_ui_polygon(_serra(-20, LARGURA + 20, HORIZONTE + 6, alt, freq, k * 1.7), cor)
    for k in range(6):  # a cachoeira: fios que descem
        x = 812 + k * 3
        desl = (t * 90 + k * 23) % 40
        for y in range(120 + int(desl), HORIZONTE, 40):
            r.draw_ui_line(x, y, x, y + 22, alpha(TINTA, 30), 1)
    for k in range(3):  # névoa que passa
        x = (t * (8 + 4 * k) + k * 340) % (LARGURA + 400) - 200
        r.draw_ui_rect(x, 210 + k * 34, 380, 16, alpha(TINTA, 9))
    _chao(r, (26, 29, 26, 255))
    _particulas(r, t, 14, alpha((150, 190, 150, 255), 60), sobe=False, tam=2.4, vel=18, deriva=30)


def _torneio(r: IRenderer, t: float) -> None:
    """Torneio de Artes Marciais: o ringue de pedra, a plateia e os estandartes."""
    _ceu(r, (22, 20, 18, 255), (34, 30, 26, 255))
    for fileira in range(4):  # a plateia: cabeças em arquibancada
        y = 150 + fileira * 30
        for i in range(34):
            x = 14 + i * 28 + (fileira % 2) * 14
            if 330 < x < 630 and fileira < 3:
                continue  # o rival fica no meio
            balanco = math.sin(t * 3 + i * 0.7 + fileira) * 2
            r.draw_ui_circle(x, y + balanco, 9, alpha(TINTA, 14 + fileira * 4))
    for x in (110, 850):  # estandartes
        r.draw_ui_line(x, 60, x, HORIZONTE, alpha(TINTA, 50), 3)
        onda = math.sin(t * 2 + x) * 6
        r.draw_ui_polygon(
            [(x, 70), (x + 46 + onda, 76), (x + 44 + onda, 190), (x, 184)],
            alpha(SANGUE_VIVO, 46),
        )
        r.draw_text(x + 22, 120, "闘", 30, alpha(TINTA, 70), anchor="center", font_id=FONTE_PINCEL)
    _chao(r, (30, 28, 25, 255))
    for k in range(9):  # lajotas em perspectiva
        xb = -200 + k * 170
        r.draw_ui_line(480 + (xb - 480) * 0.35, HORIZONTE, xb, ALTURA, alpha(TINTA, 12), 1)
    r.draw_ui_line(0, HORIZONTE, LARGURA, HORIZONTE, alpha(TINTA, 40), 2)


def _eclipse(r: IRenderer, t: float) -> None:
    """O Eclipse: céu de sangue, o sol negro e a coroa vermelha pulsando."""
    _ceu(r, (34, 8, 10, 255), (70, 18, 20, 255))
    cx, cy, raio = 480, 196, 118
    pulso = 0.5 + 0.5 * math.sin(t * 1.6)
    for k in range(5):
        r.draw_ui_circle(cx, cy, raio + 12 + k * 10, alpha(SANGUE_VIVO, 26 - 4 * k + 8 * pulso))
    for k in range(28):  # raios da coroa
        a = 2 * math.pi * k / 28 + t * 0.05
        comp = raio + 28 + 22 * math.sin(k * 2.3 + t * 2)
        r.draw_ui_line(
            cx + math.cos(a) * (raio + 4),
            cy + math.sin(a) * (raio + 4),
            cx + math.cos(a) * comp,
            cy + math.sin(a) * comp,
            alpha((255, 120, 90, 255), 50),
            2,
        )
    r.draw_ui_circle(cx, cy, raio, (8, 4, 4, 255))
    r.draw_ui_circle(cx, cy, raio, alpha((255, 90, 70, 255), 120), 2)
    for lado in (-1, 1):  # mãos que se erguem do chão (a multidão do sacrifício)
        for i in range(5):
            x = 480 + lado * (300 + i * 34)
            h = 40 + 26 * math.sin(i * 1.9)
            r.draw_ui_line(
                x, HORIZONTE, x + lado * 6, HORIZONTE - h, alpha((10, 4, 4, 255), 220), 5
            )
    _chao(r, (26, 10, 10, 255))
    _particulas(r, t, 30, alpha((120, 30, 30, 255), 120), sobe=False, tam=2.0, vel=24)


def _invasao(r: IRenderer, t: float) -> None:
    """Invasão de Konoha: a vila em chamas, telhados recortados contra o fogo."""
    _ceu(r, (26, 14, 12, 255), (92, 38, 18, 255))
    for k in range(7):  # fumaça subindo em colunas
        x = 90 + k * 132
        for j in range(5):
            y = HORIZONTE - 60 - ((t * 14 + j * 46 + k * 17) % 230)
            r.draw_ui_circle(
                x + math.sin(t + j + k) * 10, y, 18 + j * 5, alpha((20, 16, 14, 255), 60)
            )
    brilho = 0.5 + 0.5 * math.sin(t * 7) * math.sin(t * 3.3)
    r.draw_ui_rect(0, HORIZONTE - 50, LARGURA, 50, alpha((230, 110, 40, 255), 30 + 25 * brilho))
    x = -10
    i = 0
    while x < LARGURA:  # telhados: blocos com beiral curvo
        largura = 70 + 40 * (math.sin(i * 2.1) * 0.5 + 0.5)
        altura = 40 + 50 * (math.sin(i * 1.3) * 0.5 + 0.5)
        topo = HORIZONTE - altura
        r.draw_ui_rect(x + 8, topo, largura - 16, altura, (14, 10, 9, 255))
        r.draw_ui_polygon(
            [(x - 4, topo + 6), (x + largura / 2, topo - 18), (x + largura + 4, topo + 6)],
            (14, 10, 9, 255),
        )
        x += largura
        i += 1
    _chao(r, (22, 14, 12, 255))
    _particulas(r, t, 34, alpha((255, 150, 60, 255), 150), sobe=True, tam=1.8, vel=46, deriva=20)


def _shibuya(r: IRenderer, t: float) -> None:
    """Incidente de Shibuya: a cidade sob o Véu, janelas e chuva."""
    _ceu(r, (12, 10, 20, 255), (30, 22, 44, 255))
    r.draw_ui_arc(
        480, 600, 640, math.radians(18), math.radians(162), alpha((140, 90, 220, 255), 34), 6
    )
    x, i = 0, 0
    while x < LARGURA:  # prédios
        largura = 46 + 50 * (math.sin(i * 3.7) * 0.5 + 0.5)
        altura = 80 + 170 * (math.sin(i * 1.9 + 1) * 0.5 + 0.5)
        topo = HORIZONTE - altura
        r.draw_ui_rect(x, topo, largura - 4, altura, (10, 9, 16, 255))
        for jy in range(int(topo) + 10, HORIZONTE - 8, 16):
            for jx in range(int(x) + 6, int(x + largura) - 10, 12):
                aceso = math.sin(jx * 0.37 + jy * 0.91) > 0.55
                if aceso:
                    cor = (255, 214, 120, 255) if (jx + jy) % 3 else (180, 130, 255, 255)
                    r.draw_ui_rect(jx, jy, 5, 7, alpha(cor, 70))
        x += largura
        i += 1
    for k in range(60):  # chuva
        s = k * 7.31
        xc = (math.sin(s) * 0.5 + 0.5) * LARGURA
        yc = ((math.sin(s * 1.3) * 0.5 + 0.5) * ALTURA + t * 520) % ALTURA
        r.draw_ui_line(xc, yc, xc - 6, yc + 18, alpha((170, 160, 210, 255), 36), 1)
    _chao(r, (18, 15, 24, 255))
    r.draw_ui_rect(0, HORIZONTE, LARGURA, 60, alpha((140, 90, 220, 255), 14))


def _marineford(r: IRenderer, t: float) -> None:
    """Marineford: o mar, os navios no horizonte e o cadafalso ao fundo."""
    _ceu(r, (22, 26, 32, 255), (46, 54, 62, 255), 0, HORIZONTE - 60)
    mar = HORIZONTE - 60
    _ceu(r, (30, 40, 50, 255), (20, 26, 32, 255), mar, HORIZONTE)
    for k in range(6):  # ondas
        y = mar + 8 + k * 9
        pontos = [
            (x, y + 2.5 * math.sin(x * 0.03 + t * (1.2 + k * 0.3) + k))
            for x in range(0, LARGURA + 20, 20)
        ]
        for a, b in zip(pontos, pontos[1:], strict=False):
            r.draw_ui_line(a[0], a[1], b[0], b[1], alpha(TINTA, 22), 1)
    for k, x in enumerate((90, 230, 760, 880)):  # navios
        balanco = math.sin(t * 1.1 + k) * 2
        y = mar - 2 + balanco
        r.draw_ui_polygon(
            [(x - 34, y), (x + 34, y), (x + 24, y + 12), (x - 24, y + 12)], (14, 16, 20, 255)
        )
        r.draw_ui_line(x, y, x, y - 56, (14, 16, 20, 255), 3)
        r.draw_ui_polygon([(x + 2, y - 52), (x + 26, y - 40), (x + 2, y - 26)], alpha(TINTA, 40))
    # o cadafalso, atrás do rival
    base = mar
    r.draw_ui_rect(340, base - 26, 280, 26, (16, 18, 22, 255))
    for x in (360, 600):
        r.draw_ui_line(x, base - 26, x, base - 160, (16, 18, 22, 255), 6)
    r.draw_ui_line(350, base - 150, 610, base - 150, (16, 18, 22, 255), 6)
    _chao(r, (28, 30, 32, 255))
    r.draw_ui_line(0, HORIZONTE, LARGURA, HORIZONTE, alpha(TINTA, 30), 2)


ARENAS = {
    "treino_na_montanha": _montanha,
    "torneio_regular": _torneio,
    "lua_de_sangue": _eclipse,
    "invasao": _invasao,
    "maldicao_coletiva": _shibuya,
    "arco_do_juizo": _marineford,
}


def desenhar_arena(r: IRenderer, arco: str | None, relogio: float) -> None:
    """O cenário do Arco `arco` (sem Arco: só a laca) e um véu que segura o contraste."""
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
    desenho = ARENAS.get(arco or "")
    if desenho is None:
        return
    desenho(r, relogio)
    r.draw_ui_rect(0, HORIZONTE + 40, LARGURA, ALTURA - HORIZONTE - 40, alpha(FUNDO, 150))

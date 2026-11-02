"""Arenas: o cenário de cada Arco, em tinta, com profundidade.

Cada Arco homenageia um lugar (o Monte Myoboku, o Eclipse, Shibuya...). O
cenário é feito de **camadas**: céu, longe, meio, chão — e um **primeiro plano**
que a tela desenha *na frente* dos lutadores (só nas bordas, para não cobrir a
interface). Uma câmera que deriva devagar desloca cada camada conforme a
distância (parallax), e o `abalo` de um golpe treme a cena. Há luz (brilhos) e
névoa no horizonte. Tudo é determinístico (senos, sem sorteio): o mesmo quadro
sai igual em qualquer máquina e nas capturas.
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
CEU, LONGE, MEIO, CHAO, FRENTE = 0.0, 0.25, 0.55, 1.0, 1.7  # profundidades do parallax


class _Camada:
    """O renderer deslocado: a mesma cena, vista de uma câmera que se moveu."""

    def __init__(self, r: IRenderer, dx: float, dy: float) -> None:
        self.r, self.dx, self.dy = r, dx, dy

    def draw_ui_rect(self, x, y, w, h, cor):
        self.r.draw_ui_rect(x + self.dx, y + self.dy, w, h, cor)

    def draw_ui_line(self, x1, y1, x2, y2, cor, largura=1):
        self.r.draw_ui_line(x1 + self.dx, y1 + self.dy, x2 + self.dx, y2 + self.dy, cor, largura)

    def draw_ui_circle(self, x, y, raio, cor, largura=0):
        self.r.draw_ui_circle(x + self.dx, y + self.dy, raio, cor, largura)

    def draw_ui_arc(self, x, y, raio, a0, a1, cor, largura=1):
        self.r.draw_ui_arc(x + self.dx, y + self.dy, raio, a0, a1, cor, largura)

    def draw_ui_polygon(self, pontos, cor, largura=0):
        self.r.draw_ui_polygon([(x + self.dx, y + self.dy) for x, y in pontos], cor, largura)

    def draw_text(self, x, y, texto, tam, cor, anchor="topleft", font_id=None):
        self.r.draw_text(x + self.dx, y + self.dy, texto, tam, cor, anchor=anchor, font_id=font_id)


class _Camera:
    def __init__(self, r: IRenderer, t: float, abalo: float) -> None:
        self.r = r
        self.x = math.sin(t * 0.13) * 9 + abalo
        self.y = math.sin(t * 0.09) * 2 + abalo * 0.3

    def __call__(self, profundidade: float) -> _Camada:
        return _Camada(self.r, self.x * profundidade, self.y * profundidade)


# ----------------------------------------------------------------------- utilidades


def _ceu(r, topo: Cor, base: Cor, y0: float = 0, y1: float = HORIZONTE) -> None:
    faixas = 18
    altura = (y1 - y0) / faixas
    for i in range(faixas):
        r.draw_ui_rect(
            -60, y0 + i * altura, LARGURA + 120, altura + 1, mistura(topo, base, i / faixas)
        )


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


def _brilho(r, x: float, y: float, raio: float, cor: Cor, forca: float = 1.0) -> None:
    """Luz: círculos concêntricos que somem para fora."""
    for k in range(7):
        r.draw_ui_circle(x, y, raio * (1 - k / 8), alpha(cor, (6 + 5 * k) * forca))


def _nevoa(r, t: float, y: float, cor: Cor, forca: float = 1.0, vel: float = 8.0) -> None:
    """Faixas de névoa passando devagar no horizonte."""
    for k in range(4):
        x = (t * (vel + 3 * k) + k * 290) % (LARGURA + 500) - 300
        r.draw_ui_rect(x, y + k * 11 - 18, 420 + 60 * k, 10, alpha(cor, (10 - k) * forca))


def _chao(r, cor: Cor) -> None:
    r.draw_ui_rect(-60, HORIZONTE, LARGURA + 120, ALTURA - HORIZONTE, cor)
    for k in range(5):  # pinceladas horizontais do chão
        y = HORIZONTE + 18 + k * 26
        r.draw_ui_line(60 + k * 37, y, LARGURA - 90 + k * 11, y, alpha(TINTA, 7), 2)


def _galho(r, x, y, ang, comp, cor, espessura, nivel=3) -> None:
    """Um galho que se divide: árvores, raízes, cristais."""
    a = math.radians(ang)
    x2, y2 = x + math.cos(a) * comp, y + math.sin(a) * comp
    r.draw_ui_line(x, y, x2, y2, cor, max(1, round(espessura)))
    if nivel > 0:
        for d in (-24, 21):
            _galho(r, x2, y2, ang + d, comp * 0.68, cor, espessura * 0.62, nivel - 1)


# ----------------------------------------------------------------------- as arenas


def _montanha(r, t, cam) -> None:
    """Treino no Monte Myoboku: montanhas em camadas, névoa e uma cachoeira."""
    _ceu(cam(CEU), (24, 30, 28, 255), (42, 50, 44, 255))
    _brilho(cam(CEU), 760, 90, 120, (200, 230, 200, 255), 0.6)
    camadas = (
        (190, (38, 46, 41, 255), 0.006, LONGE),
        (150, (31, 38, 34, 255), 0.011, MEIO),
        (95, (25, 30, 27, 255), 0.019, MEIO + 0.2),
    )
    for k, (alt, cor, freq, prof) in enumerate(camadas):
        c = cam(prof)
        c.draw_ui_polygon(_serra(-60, LARGURA + 60, HORIZONTE + 6, alt, freq, k * 1.7), cor)
        if k == 0:
            _nevoa(c, t, HORIZONTE - 90, TINTA, 1.2, 5)
    c = cam(MEIO)
    for k in range(6):  # a cachoeira: fios que descem
        x = 812 + k * 3
        desl = (t * 90 + k * 23) % 40
        for y in range(120 + int(desl), HORIZONTE, 40):
            c.draw_ui_line(x, y, x, y + 22, alpha(TINTA, 30), 1)
    _nevoa(cam(MEIO), t, HORIZONTE - 30, TINTA, 1.3)
    _chao(cam(CHAO), (26, 29, 26, 255))
    _particulas(r, t, 14, alpha((150, 190, 150, 255), 60), sobe=False, tam=2.4, vel=18, deriva=30)


def _frente_montanha(r, t, cam) -> None:
    c = cam(FRENTE)
    for lado, x0 in ((1, -20), (-1, LARGURA + 20)):  # galhos de pinheiro pendendo nos cantos
        _galho(
            c, x0, 10, 90 - lado * 55 + math.sin(t * 0.8) * 2, 90, alpha((18, 24, 20, 255), 230), 7
        )
    _particulas(
        r, t, 5, alpha((170, 210, 170, 255), 70), sobe=False, tam=5, vel=24, deriva=50, semente=7
    )


def _torneio(r, t, cam) -> None:
    """Torneio de Artes Marciais: o ringue de pedra, a plateia e os estandartes."""
    _ceu(cam(CEU), (22, 20, 18, 255), (34, 30, 26, 255))
    _brilho(cam(CEU), 480, 40, 260, (255, 220, 160, 255), 0.5)  # a luz do estádio
    c = cam(LONGE)
    for fileira in range(4):  # a plateia: cabeças em arquibancada
        y = 150 + fileira * 30
        for i in range(36):
            x = -10 + i * 28 + (fileira % 2) * 14
            if 330 < x < 630 and fileira < 3:
                continue  # o rival fica no meio
            balanco = math.sin(t * 3 + i * 0.7 + fileira) * 2
            c.draw_ui_circle(x, y + balanco, 9, alpha(TINTA, 14 + fileira * 4))
    c = cam(MEIO)
    for x in (110, 850):  # estandartes
        c.draw_ui_line(x, 60, x, HORIZONTE, alpha(TINTA, 50), 3)
        onda = math.sin(t * 2 + x) * 6
        c.draw_ui_polygon(
            [(x, 70), (x + 46 + onda, 76), (x + 44 + onda, 190), (x, 184)], alpha(SANGUE_VIVO, 46)
        )
        c.draw_text(x + 22, 120, "闘", 30, alpha(TINTA, 70), anchor="center", font_id=FONTE_PINCEL)
    c = cam(CHAO)
    _chao(c, (30, 28, 25, 255))
    for k in range(10):  # lajotas em perspectiva
        xb = -260 + k * 170
        c.draw_ui_line(480 + (xb - 480) * 0.35, HORIZONTE, xb, ALTURA, alpha(TINTA, 12), 1)
    c.draw_ui_line(-60, HORIZONTE, LARGURA + 60, HORIZONTE, alpha(TINTA, 40), 2)


def _frente_torneio(r, t, cam) -> None:
    c = cam(FRENTE)
    for x in (-10, LARGURA - 34):  # os postes do ringue, bem perto
        c.draw_ui_rect(x, 0, 44, 250, (14, 12, 11, 235))
        c.draw_ui_line(x + 44 if x < 0 else x, 70, x + 44 if x < 0 else x, 240, alpha(TINTA, 30), 2)


def _eclipse(r, t, cam) -> None:
    """O Eclipse: céu de sangue, o sol negro e a coroa vermelha pulsando."""
    _ceu(cam(CEU), (34, 8, 10, 255), (70, 18, 20, 255))
    c = cam(LONGE * 0.5)
    cx, cy, raio = 480, 196, 118
    pulso = 0.5 + 0.5 * math.sin(t * 1.6)
    _brilho(c, cx, cy, raio * 2.4, (255, 90, 70, 255), 0.6 + 0.3 * pulso)
    for k in range(5):
        c.draw_ui_circle(cx, cy, raio + 12 + k * 10, alpha(SANGUE_VIVO, 26 - 4 * k + 8 * pulso))
    for k in range(28):  # raios da coroa
        a = 2 * math.pi * k / 28 + t * 0.05
        comp = raio + 28 + 22 * math.sin(k * 2.3 + t * 2)
        c.draw_ui_line(
            cx + math.cos(a) * (raio + 4),
            cy + math.sin(a) * (raio + 4),
            cx + math.cos(a) * comp,
            cy + math.sin(a) * comp,
            alpha((255, 120, 90, 255), 50),
            2,
        )
    c.draw_ui_circle(cx, cy, raio, (8, 4, 4, 255))
    c.draw_ui_circle(cx, cy, raio, alpha((255, 90, 70, 255), 120), 2)
    c = cam(MEIO)
    c.draw_ui_polygon(_serra(-60, LARGURA + 60, HORIZONTE + 4, 50, 0.013, 2.0), (20, 6, 6, 255))
    for lado in (-1, 1):  # mãos que se erguem do chão (a multidão do sacrifício)
        for i in range(6):
            x = 480 + lado * (290 + i * 34)
            h = 40 + 26 * math.sin(i * 1.9)
            c.draw_ui_line(
                x, HORIZONTE, x + lado * 6, HORIZONTE - h, alpha((10, 4, 4, 255), 220), 5
            )
    _chao(cam(CHAO), (26, 10, 10, 255))
    _nevoa(cam(CHAO), t, HORIZONTE + 10, SANGUE_VIVO, 0.8)
    _particulas(r, t, 30, alpha((120, 30, 30, 255), 120), sobe=False, tam=2.0, vel=24)


def _frente_eclipse(r, t, cam) -> None:
    c = cam(FRENTE)
    for lado, x0 in ((1, -30), (-1, LARGURA + 30)):  # galhos mortos nos cantos
        _galho(c, x0, 40, 90 - lado * 70, 110, (8, 3, 3, 240), 8)
    _particulas(
        r, t, 6, alpha((150, 40, 40, 255), 90), sobe=False, tam=5, vel=30, deriva=40, semente=3
    )


def _invasao(r, t, cam) -> None:
    """Invasão de Konoha: a vila em chamas, telhados recortados contra o fogo."""
    _ceu(cam(CEU), (26, 14, 12, 255), (92, 38, 18, 255))
    c = cam(LONGE)
    for k in range(8):  # fumaça subindo em colunas
        x = 40 + k * 132
        for j in range(5):
            y = HORIZONTE - 60 - ((t * 14 + j * 46 + k * 17) % 230)
            c.draw_ui_circle(
                x + math.sin(t + j + k) * 10, y, 18 + j * 5, alpha((20, 16, 14, 255), 60)
            )
    brilho = 0.5 + 0.5 * math.sin(t * 7) * math.sin(t * 3.3)
    _brilho(cam(LONGE), 300, HORIZONTE - 20, 260, (255, 140, 50, 255), 0.7 + 0.4 * brilho)
    _brilho(cam(LONGE), 760, HORIZONTE - 30, 200, (255, 120, 40, 255), 0.6 + 0.4 * (1 - brilho))
    c = cam(MEIO)
    x, i = -60.0, 0
    while x < LARGURA + 60:  # telhados: blocos com beiral curvo
        largura = 70 + 40 * (math.sin(i * 2.1) * 0.5 + 0.5)
        altura = 40 + 50 * (math.sin(i * 1.3) * 0.5 + 0.5)
        topo = HORIZONTE - altura
        c.draw_ui_rect(x + 8, topo, largura - 16, altura, (14, 10, 9, 255))
        c.draw_ui_polygon(
            [(x - 4, topo + 6), (x + largura / 2, topo - 18), (x + largura + 4, topo + 6)],
            (14, 10, 9, 255),
        )
        if i % 3 == 0:  # uma janela acesa pelo fogo
            c.draw_ui_rect(
                x + largura / 2 - 5, topo + 14, 10, 12, alpha((255, 150, 60, 255), 90 + 60 * brilho)
            )
        x += largura
        i += 1
    _chao(cam(CHAO), (22, 14, 12, 255))
    _particulas(r, t, 34, alpha((255, 150, 60, 255), 150), sobe=True, tam=1.8, vel=46, deriva=20)


def _frente_invasao(r, t, cam) -> None:
    c = cam(FRENTE)
    for x0, lado in ((0, 1), (LARGURA, -1)):  # vigas caídas, queimando nas pontas
        c.draw_ui_polygon(
            [(x0, 0), (x0 + lado * 70, 0), (x0 + lado * 20, 190), (x0, 200)], (12, 8, 7, 240)
        )
        _brilho(c, x0 + lado * 30, 140, 40, (255, 140, 50, 255), 0.8)
    _particulas(
        r, t, 8, alpha((255, 170, 80, 255), 140), sobe=True, tam=3.5, vel=60, deriva=30, semente=5
    )


def _shibuya(r, t, cam) -> None:
    """Incidente de Shibuya: a cidade sob o Véu, janelas e chuva."""
    _ceu(cam(CEU), (12, 10, 20, 255), (30, 22, 44, 255))
    cam(CEU).draw_ui_arc(
        480, 600, 640, math.radians(18), math.radians(162), alpha((140, 90, 220, 255), 34), 6
    )
    for prof, base_alt, escala, cor in (
        (LONGE, 140, 0.7, (16, 14, 24, 255)),
        (MEIO, 80, 1.0, (10, 9, 16, 255)),
    ):
        c = cam(prof)
        x, i = -60.0, int(prof * 10)
        while x < LARGURA + 60:  # prédios em duas camadas
            largura = (46 + 50 * (math.sin(i * 3.7) * 0.5 + 0.5)) * escala
            altura = base_alt + 170 * escala * (math.sin(i * 1.9 + 1) * 0.5 + 0.5)
            topo = HORIZONTE - altura
            c.draw_ui_rect(x, topo, largura - 4, altura, cor)
            if prof == MEIO:
                for jy in range(int(topo) + 10, HORIZONTE - 8, 16):
                    for jx in range(int(x) + 6, int(x + largura) - 10, 12):
                        if math.sin(jx * 0.37 + jy * 0.91) > 0.55:
                            janela = (255, 214, 120, 255) if (jx + jy) % 3 else (180, 130, 255, 255)
                            c.draw_ui_rect(jx, jy, 5, 7, alpha(janela, 70))
            x += largura
            i += 1
    _nevoa(cam(MEIO), t, HORIZONTE - 20, (140, 90, 220, 255), 1.3)
    _chao(cam(CHAO), (18, 15, 24, 255))
    cam(CHAO).draw_ui_rect(-60, HORIZONTE, LARGURA + 120, 60, alpha((140, 90, 220, 255), 14))
    for k in range(60):  # chuva
        s = k * 7.31
        xc = (math.sin(s) * 0.5 + 0.5) * LARGURA
        yc = ((math.sin(s * 1.3) * 0.5 + 0.5) * ALTURA + t * 520) % ALTURA
        r.draw_ui_line(xc, yc, xc - 6, yc + 18, alpha((170, 160, 210, 255), 36), 1)


def _frente_shibuya(r, t, cam) -> None:
    c = cam(FRENTE)
    c.draw_ui_rect(LARGURA - 40, 0, 14, 300, (8, 7, 12, 240))  # um poste
    _brilho(c, LARGURA - 33, 40, 70, (255, 214, 120, 255), 0.9)
    for k in range(14):  # chuva grossa, perto da câmera
        s = k * 3.17
        xc = (math.sin(s) * 0.5 + 0.5) * LARGURA
        yc = ((math.sin(s * 1.9) * 0.5 + 0.5) * ALTURA + t * 900) % ALTURA
        r.draw_ui_line(xc, yc, xc - 10, yc + 34, alpha((190, 180, 230, 255), 50), 2)


def _marineford(r, t, cam) -> None:
    """Marineford: o mar, os navios no horizonte e o cadafalso ao fundo."""
    mar = HORIZONTE - 60
    _ceu(cam(CEU), (22, 26, 32, 255), (46, 54, 62, 255), 0, mar)
    _brilho(cam(CEU), 220, 70, 160, (220, 230, 240, 255), 0.5)
    c = cam(LONGE)
    _ceu(c, (30, 40, 50, 255), (20, 26, 32, 255), mar, HORIZONTE)
    for k in range(6):  # ondas
        y = mar + 8 + k * 9
        pontos = [
            (x, y + 2.5 * math.sin(x * 0.03 + t * (1.2 + k * 0.3) + k))
            for x in range(-60, LARGURA + 80, 20)
        ]
        for a, b in zip(pontos, pontos[1:], strict=False):
            c.draw_ui_line(a[0], a[1], b[0], b[1], alpha(TINTA, 22), 1)
    for k, x in enumerate((90, 230, 760, 880)):  # navios
        y = mar - 2 + math.sin(t * 1.1 + k) * 2
        c.draw_ui_polygon(
            [(x - 34, y), (x + 34, y), (x + 24, y + 12), (x - 24, y + 12)], (14, 16, 20, 255)
        )
        c.draw_ui_line(x, y, x, y - 56, (14, 16, 20, 255), 3)
        c.draw_ui_polygon([(x + 2, y - 52), (x + 26, y - 40), (x + 2, y - 26)], alpha(TINTA, 40))
    c = cam(MEIO)  # o cadafalso, atrás do rival
    c.draw_ui_rect(340, mar - 26, 280, 26, (16, 18, 22, 255))
    for x in (360, 600):
        c.draw_ui_line(x, mar - 26, x, mar - 160, (16, 18, 22, 255), 6)
    c.draw_ui_line(350, mar - 150, 610, mar - 150, (16, 18, 22, 255), 6)
    _nevoa(cam(MEIO), t, mar + 20, TINTA, 1.0)
    _chao(cam(CHAO), (28, 30, 32, 255))
    cam(CHAO).draw_ui_line(-60, HORIZONTE, LARGURA + 60, HORIZONTE, alpha(TINTA, 30), 2)


def _frente_marineford(r, t, cam) -> None:
    c = cam(FRENTE)
    for k in range(3):  # cordas do cadafalso balançando
        x = 30 + k * 18
        c.draw_ui_line(
            x, 0, x + math.sin(t * 1.2 + k) * 8, 160 + k * 20, alpha((40, 34, 28, 255), 220), 3
        )
    _particulas(
        r, t, 6, alpha((220, 230, 240, 255), 60), sobe=True, tam=4, vel=40, deriva=60, semente=9
    )


def _torre(r, t, cam) -> None:
    """Torre Celestial: a luta no alto, entre pilares, com as nuvens lá embaixo."""
    _ceu(cam(CEU), (34, 42, 58, 255), (74, 82, 96, 255))
    _brilho(cam(CEU), 480, 120, 300, (255, 230, 190, 255), 0.6)
    c = cam(LONGE)
    for k in range(5):  # o mar de nuvens, abaixo da torre
        y = HORIZONTE - 70 + k * 14
        for i in range(9):
            x = ((i * 150 + t * (6 + k * 2)) % (LARGURA + 300)) - 150
            c.draw_ui_circle(
                x, y, 46 + 10 * math.sin(i + k), alpha((200, 206, 216, 255), 26 + k * 4)
            )
    c = cam(MEIO)
    for x in (130, 830):  # pilares com janelas altas
        c.draw_ui_rect(x - 40, 0, 80, HORIZONTE, (24, 26, 34, 255))
        for y in range(30, HORIZONTE - 40, 70):
            c.draw_ui_rect(x - 12, y, 24, 44, alpha((255, 226, 170, 255), 40))
        c.draw_text(
            x, HORIZONTE - 30, "階", 22, alpha(TINTA, 60), anchor="center", font_id=FONTE_PINCEL
        )
    c = cam(CHAO)
    _chao(c, (30, 32, 38, 255))
    for k in range(9):  # o piso de lajes, quadrado, em perspectiva
        xb = -260 + k * 185
        c.draw_ui_line(480 + (xb - 480) * 0.3, HORIZONTE, xb, ALTURA, alpha(TINTA, 14), 1)
    for k in range(4):
        y = HORIZONTE + 30 + k * k * 18
        c.draw_ui_line(-60, y, LARGURA + 60, y, alpha(TINTA, 12), 1)


def _frente_torre(r, t, cam) -> None:
    c = cam(FRENTE)
    for x0 in (-30, LARGURA - 40):  # o batente das janelas, bem perto
        c.draw_ui_rect(x0, 0, 70, ALTURA * 0.45, (16, 17, 22, 240))
    _particulas(
        r, t, 5, alpha((220, 226, 236, 255), 50), sobe=False, tam=6, vel=14, deriva=80, semente=11
    )


def _floresta(r, t, cam) -> None:
    """Floresta da Morte: árvores gigantes, raízes, e luz que mal passa pela copa."""
    _ceu(cam(CEU), (10, 16, 12, 255), (26, 38, 28, 255))
    for prof, n, cor, larg in ((LONGE, 9, (18, 26, 20, 255), 30), (MEIO, 6, (12, 18, 14, 255), 60)):
        c = cam(prof)
        for i in range(n):  # troncos em duas camadas, com raízes
            x = -40 + i * (LARGURA + 80) / (n - 1) + math.sin(i * 2.7) * 30
            if prof == MEIO and 330 < x < 630:
                continue  # o rival fica no meio
            c.draw_ui_polygon(
                [
                    (x - larg * 0.4, -10),
                    (x + larg * 0.4, -10),
                    (x + larg * 0.6, HORIZONTE),
                    (x - larg * 0.6, HORIZONTE),
                ],
                cor,
            )
            for lado in (-1, 1):
                _galho(c, x, HORIZONTE - 10, 90 + lado * 50, larg * 0.9, cor, larg * 0.18, 1)
    c = cam(LONGE)
    for k in range(4):  # feixes de luz atravessando a copa
        x = 180 + k * 190 + math.sin(t * 0.2 + k) * 10
        c.draw_ui_polygon(
            [(x, 0), (x + 40, 0), (x + 150, HORIZONTE), (x + 90, HORIZONTE)],
            alpha((200, 230, 160, 255), 12),
        )
    _nevoa(cam(MEIO), t, HORIZONTE - 10, (160, 200, 150, 255), 1.2, 4)
    _chao(cam(CHAO), (16, 22, 16, 255))
    _particulas(
        r, t, 16, alpha((190, 230, 120, 255), 120), sobe=True, tam=1.6, vel=10, deriva=40, semente=2
    )


def _frente_floresta(r, t, cam) -> None:
    c = cam(FRENTE)
    for x0, lado in ((-20, 1), (LARGURA + 20, -1)):  # cipós e folhas pendendo
        for k in range(4):
            x = x0 + lado * k * 26
            fim = 120 + k * 40 + math.sin(t * 0.9 + k) * 6
            c.draw_ui_line(x, 0, x + math.sin(t * 0.7 + k) * 6, fim, (10, 16, 11, 240), 4)
            c.draw_ui_circle(x, fim, 10, (12, 20, 13, 240))


def _hueco(r, t, cam) -> None:
    """Hueco Mundo: o deserto branco sob a lua, e as torres de Las Noches ao longe."""
    _ceu(cam(CEU), (4, 4, 8, 255), (14, 14, 22, 255))
    c = cam(CEU)
    _brilho(c, 760, 90, 140, (230, 230, 240, 255), 0.7)
    c.draw_ui_arc(
        760, 90, 34, math.radians(110), math.radians(290), (232, 232, 240, 255), 10
    )  # a lua crescente
    c = cam(LONGE)
    c.draw_ui_arc(
        300,
        HORIZONTE - 20,
        120,
        math.radians(0),
        math.radians(180),
        alpha((200, 200, 210, 255), 50),
        4,
    )  # a cúpula
    for x in (190, 240, 360, 410):
        c.draw_ui_rect(x, HORIZONTE - 150 - (x % 30), 10, 130, alpha((190, 190, 200, 255), 50))
    c = cam(MEIO)
    c.draw_ui_polygon(_serra(-60, LARGURA + 60, HORIZONTE + 6, 40, 0.01, 0.7), (150, 150, 160, 255))
    for x in (120, 820):  # árvores de quartzo
        _galho(c, x, HORIZONTE, -90, 70, alpha((220, 220, 230, 255), 160), 5)
    _chao(cam(CHAO), (120, 120, 130, 255))
    cam(CHAO).draw_ui_rect(
        -60, HORIZONTE, LARGURA + 120, ALTURA - HORIZONTE, alpha((8, 8, 12, 255), 150)
    )
    _nevoa(cam(CHAO), t, HORIZONTE + 6, (220, 220, 230, 255), 1.4, 14)


def _frente_hueco(r, t, cam) -> None:
    c = cam(FRENTE)
    for k in range(10):  # areia levada pelo vento
        x = ((t * 120 + k * 97) % (LARGURA + 200)) - 100
        y = 30 + k * 26
        c.draw_ui_line(x, y, x + 60, y + 4, alpha((220, 220, 230, 255), 40), 2)
    c.draw_ui_polygon(
        [(-20, 0), (60, 0), (20, 60), (-20, 80)], alpha((210, 206, 196, 255), 200)
    )  # um osso


def _torneio_poder(r, t, cam) -> None:
    """Torneio do Poder: a arena flutuando no vazio, entre estrelas e pedaços de pedra."""
    _ceu(cam(CEU), (10, 6, 22, 255), (34, 20, 60, 255))
    c = cam(CEU)
    for i in range(70):  # estrelas
        s = i * 9.13
        x = (math.sin(s) * 0.5 + 0.5) * LARGURA
        y = (math.sin(s * 1.7) * 0.5 + 0.5) * HORIZONTE
        c.draw_ui_circle(x, y, 1 + (i % 3) * 0.5, alpha(TINTA, 60 + 60 * math.sin(t * 2 + i) ** 2))
    _brilho(c, 480, 150, 320, (170, 120, 255, 255), 0.6)
    c = cam(LONGE)
    for k, (x, y) in enumerate(
        ((160, 120), (330, 70), (650, 90), (820, 150))
    ):  # pilares partidos flutuando
        y += math.sin(t * 0.7 + k) * 6
        c.draw_ui_polygon(
            [(x - 14, y - 50), (x + 14, y - 44), (x + 12, y + 30), (x - 12, y + 26)],
            (40, 30, 66, 255),
        )
    c = cam(CHAO)
    c.draw_ui_polygon(
        [(-60, ALTURA), (110, HORIZONTE), (850, HORIZONTE), (LARGURA + 60, ALTURA)],
        (40, 34, 58, 255),
    )
    c.draw_ui_line(110, HORIZONTE, 850, HORIZONTE, alpha((200, 170, 255, 255), 80), 3)
    for k in range(6):
        xb = 110 + k * 148
        c.draw_ui_line(
            xb, HORIZONTE, -60 + (xb - 110) * (LARGURA + 120) / 740, ALTURA, alpha(TINTA, 14), 1
        )
    _particulas(
        r, t, 20, alpha((200, 170, 255, 255), 90), sobe=True, tam=1.6, vel=30, deriva=20, semente=4
    )


def _frente_torneio_poder(r, t, cam) -> None:
    c = cam(FRENTE)
    for k, (x, y, tam) in enumerate(((40, 70, 34), (LARGURA - 50, 120, 26), (90, 200, 18))):
        y += math.sin(t * 0.9 + k * 2) * 10
        c.draw_ui_polygon(
            [
                (x - tam, y),
                (x, y - tam * 0.8),
                (x + tam, y - 4),
                (x + tam * 0.6, y + tam * 0.7),
                (x - tam * 0.5, y + tam * 0.6),
            ],
            (26, 20, 42, 245),
        )


ARENAS = {
    "treino_na_montanha": (_montanha, _frente_montanha),
    "torneio_regular": (_torneio, _frente_torneio),
    "lua_de_sangue": (_eclipse, _frente_eclipse),
    "invasao": (_invasao, _frente_invasao),
    "maldicao_coletiva": (_shibuya, _frente_shibuya),
    "arco_do_juizo": (_marineford, _frente_marineford),
    "torre_celestial": (_torre, _frente_torre),
    "floresta_da_morte": (_floresta, _frente_floresta),
    "hueco_mundo": (_hueco, _frente_hueco),
    "torneio_do_poder": (_torneio_poder, _frente_torneio_poder),
}


def _corvos(r, t: float) -> None:
    """Corvos cruzando o céu, devagar."""
    for k in range(4):
        x = ((t * (16 + 5 * k) + k * 260) % (LARGURA + 200)) - 100
        y = 50 + k * 34 + math.sin(t * 1.3 + k) * 8
        bate = math.sin(t * 9 + k * 2) * 6
        cor = alpha((6, 5, 5, 255), 200)
        r.draw_ui_line(x - 10, y - bate, x, y, cor, 2)
        r.draw_ui_line(x, y, x + 10, y - bate, cor, 2)


def _espadas_fincadas(r) -> None:
    """Restos de quem lutou aqui antes: lâminas quebradas fincadas no chão."""
    for k, (x, ang, comp) in enumerate(
        ((70, -78, 40), (230, -96, 30), (700, -84, 46), (880, -100, 34))
    ):
        y = HORIZONTE + 6 + (k % 2) * 8
        a = math.radians(ang)
        r.draw_ui_line(
            x, y, x + math.cos(a) * comp, y + math.sin(a) * comp, alpha((90, 86, 82, 255), 140), 3
        )
        r.draw_ui_line(
            x - 6, y - comp * 0.25, x + 6, y - comp * 0.25 - 2, alpha((40, 36, 34, 255), 160), 3
        )


def desenhar_arena(r: IRenderer, arco: str | None, relogio: float, abalo: float = 0.0) -> None:
    """O cenário do Arco `arco` (sem Arco: só a laca) e um véu que segura o contraste.

    `abalo`: deslocamento do tremor de um golpe (px), que a câmera soma.
    """
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
    par = ARENAS.get(arco or "")
    if par is None:
        return
    cam = _Camera(r, relogio, abalo)
    par[0](r, relogio, cam)
    _corvos(cam(LONGE), relogio)
    _espadas_fincadas(cam(CHAO))
    r.draw_ui_rect(0, 0, LARGURA, HORIZONTE, alpha((0, 0, 0, 255), 55))  # o céu mais escuro
    r.draw_ui_rect(0, HORIZONTE + 40, LARGURA, ALTURA - HORIZONTE - 40, alpha(FUNDO, 170))


def desenhar_frente(r: IRenderer, arco: str | None, relogio: float, abalo: float = 0.0) -> None:
    """O primeiro plano do Arco, na frente dos lutadores (só nas bordas da tela)."""
    par = ARENAS.get(arco or "")
    if par is not None:
        par[1](r, relogio, _Camera(r, relogio, abalo))

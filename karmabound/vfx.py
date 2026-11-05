"""Efeitos de tinta: cada habilidade tem o seu, em homenagem à origem.

Um efeito é uma função pura do progresso `k` (0 → 1): desenha o quadro e não
guarda estado. A tela de luta escolhe o efeito pelo id da técnica e o toca entre
o centro de quem age e o de quem recebe. Os de tela cheia (Domínio, The World,
Tsukuyomi, o Corte do Mundo) cobrem a arena inteira.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from ouroboros.interfaces.renderer import IRenderer

from karmabound.figuras import desenhar_lutador
from karmabound.visual import (
    ALTURA,
    FONTE_PINCEL,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    VERDE_JADE,
    Cor,
    alpha,
    ease_out,
    mistura,
)

AZUL_CHAKRA = (150, 205, 255, 255)
ROXO = (157, 92, 224, 255)
AMARELO = (255, 232, 130, 255)
BRANCO = (255, 255, 255, 255)
PRETO = (6, 5, 5, 255)
SEPIA = (150, 120, 80, 255)

Ponto = tuple[float, float]


def _lerp(a: Ponto, b: Ponto, t: float) -> Ponto:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _sino(k: float) -> float:
    """0 → 1 → 0: entra e sai."""
    return math.sin(max(0.0, min(1.0, k)) * math.pi)


def _ruido(i: float) -> float:
    return math.sin(i * 12.9898) * 0.5


def _raio(r: IRenderer, a: Ponto, b: Ponto, cor: Cor, largura: int, semente: float) -> None:
    """Um relâmpago em zigue-zague de a até b."""
    passos = 9
    nx, ny = -(b[1] - a[1]), b[0] - a[0]
    norma = math.hypot(nx, ny) or 1
    nx, ny = nx / norma, ny / norma
    anterior = a
    for i in range(1, passos + 1):
        t = i / passos
        desvio = 0 if i == passos else _ruido(semente + i) * 46
        p = (a[0] + (b[0] - a[0]) * t + nx * desvio, a[1] + (b[1] - a[1]) * t + ny * desvio)
        r.draw_ui_line(anterior[0], anterior[1], p[0], p[1], cor, largura)
        anterior = p


def _corrente(r: IRenderer, a: Ponto, b: Ponto, cor: Cor) -> None:
    dist = math.hypot(b[0] - a[0], b[1] - a[1])
    elos = max(2, int(dist / 16))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for i in range(elos):
        cx, cy = _lerp(a, b, (i + 0.5) / elos)
        if i % 2 == 0:
            dx, dy = math.cos(ang) * 8, math.sin(ang) * 8
            r.draw_ui_line(cx - dx, cy - dy, cx + dx, cy + dy, cor, 5)
        else:
            r.draw_ui_circle(cx, cy, 6, cor, 2)


# ----------------------------------------------------------------------- efeitos


def _impacto(r, a, b, k, t, forte):
    """O Golpe: um borrão de tinta que se abre no alvo."""
    x, y = b
    abre = 1 - (1 - k) ** 2
    for i in range(10):
        ang = i * 2 * math.pi / 10 + 0.3
        r.draw_ui_line(
            x + math.cos(ang) * 14 * abre,
            y + math.sin(ang) * 14 * abre,
            x + math.cos(ang) * (26 + 22 * abre),
            y + math.sin(ang) * (26 + 22 * abre),
            alpha(TINTA, 200 * (1 - k)),
            3,
        )
    r.draw_ui_circle(x, y, 10 + 40 * abre, alpha(TINTA, 160 * (1 - k)), 3)


def _punho(r, a, b, k, t, forte):
    """Gomu Gomu no Pistol: o braço estica até o alvo e volta."""
    p = _lerp(a, b, _sino(k) * 0.92)
    r.draw_ui_line(a[0], a[1], p[0], p[1], alpha(TINTA, 210), 9)
    r.draw_ui_circle(p[0], p[1], 15, TINTA)
    if k > 0.4:
        _impacto(r, a, b, (k - 0.4) / 0.6, t, forte)


def _guarda(r, a, b, k, t, forte):
    """Ken: um ensō que se fecha em volta de quem defende."""
    fim = math.radians(100 + 360 * min(1.0, k * 1.6))
    r.draw_ui_arc(a[0], a[1], 70, math.radians(100), fim, alpha(VERDE_JADE, 200 * (1 - k * 0.6)), 6)


def _investida(r, a, b, k, t, forte):
    """Dynamic Entry: linhas de velocidade no caminho."""
    for i in range(7):
        d = (i - 3) * 9
        q0 = _lerp(a, b, max(0.0, k - 0.35))
        q1 = _lerp(a, b, k)
        r.draw_ui_line(q0[0] + d, q0[1] - d, q1[0] + d, q1[1] - d, alpha(TINTA, 120 * (1 - k)), 2)
    if k > 0.5:
        _impacto(r, a, b, (k - 0.5) / 0.5, t, forte)


def _corte_x(r, a, b, k, t, forte):
    """Nitōryū: dois cortes em cruz."""
    x, y = b
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1))):
        prog = max(0.0, min(1.0, (k - i * 0.25) / 0.4))
        if prog <= 0:
            continue
        x0, y0 = x + sx * 60, y + sy * 60
        x1 = x0 + (-sx * 120) * prog
        y1 = y0 + (-sy * 120) * prog
        r.draw_ui_line(x0, y0, x1, y1, alpha(BRANCO, 230 * (1 - k * 0.7)), 4)
        r.draw_ui_line(x0 + 3, y0, x1 + 3, y1, alpha(SANGUE_VIVO, 140 * (1 - k)), 2)


def _rotacao(r, a, b, k, t, forte):
    """Kaiten: uma cúpula que gira em volta de quem defende."""
    for i in range(4):
        raio = 50 + i * 9
        ini = t * 9 + i * 1.3
        r.draw_ui_arc(a[0], a[1], raio, ini, ini + 2.6, alpha(AZUL_CHAKRA, 170 * _sino(k)), 3)


def _sangue(r, a, b, k, t, forte):
    """Manipulação de Sangue: jatos vermelhos até o alvo."""
    for i in range(3):
        d = (i - 1) * 14
        p = _lerp(a, b, min(1.0, k * 1.5))
        r.draw_ui_line(a[0] + d, a[1], p[0] + d, p[1], alpha(SANGUE_VIVO, 220 * (1 - k * 0.5)), 4)
    for i in range(8):
        ang = i * 0.8 + k * 3
        r.draw_ui_circle(
            b[0] + math.cos(ang) * 40 * k,
            b[1] + math.sin(ang) * 40 * k,
            4,
            alpha(SANGUE_VIVO, 200 * (1 - k)),
        )


def _selo(r, a, b, k, t, forte):
    """Selo Amaldiçoado: três vírgulas roxas que se fecham no alvo."""
    raio = 80 * (1 - k) + 14
    for i in range(3):
        ang = t * 4 + i * 2 * math.pi / 3
        x, y = b[0] + math.cos(ang) * raio, b[1] + math.sin(ang) * raio
        r.draw_ui_circle(x, y, 8, alpha(ROXO, 230))
        r.draw_ui_arc(x, y, 12, ang + 1.5, ang + 3.6, alpha(ROXO, 230), 3)


def _demonio(r, a, b, k, t, forte):
    """Contrato: o demônio abre a bocarra sobre o alvo e cobra o preço."""
    x, y = b
    s = _sino(k)
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(PRETO, 120 * s))
    for lado in (-1, 1):
        r.draw_ui_circle(x + lado * 50, y - 70, 14 * s, alpha(SANGUE_VIVO, 255))
        r.draw_ui_circle(x + lado * 50, y - 70, 4 * s, alpha(AMARELO, 255))
    fecha = min(1.0, k * 2)
    for i in range(9):  # dentes
        px = x - 96 + i * 24
        r.draw_ui_polygon(
            [
                (px, y - 40 + 30 * fecha),
                (px + 24, y - 40 + 30 * fecha),
                (px + 12, y - 10 + 30 * fecha),
            ],
            alpha(TINTA, 220 * s),
        )
        r.draw_ui_polygon(
            [
                (px, y + 60 - 30 * fecha),
                (px + 24, y + 60 - 30 * fecha),
                (px + 12, y + 30 - 30 * fecha),
            ],
            alpha(TINTA, 220 * s),
        )


def _repulsao(r, a, b, k, t, forte):
    """Shinra Tensei: anéis que empurram tudo para longe de quem usa."""
    for i in range(4):
        raio = (k * 1.3 - i * 0.12) * 520
        if raio > 0:
            r.draw_ui_circle(a[0], a[1], raio, alpha(OURO, 160 * (1 - k)), 4)
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(OURO, 50 * (1 - k)))


def _olho(r, a, b, k, t, forte):
    """Sharingan: o olho vermelho se abre e as vírgulas giram."""
    x, y = a[0], a[1] - 90
    s = _sino(k)
    r.draw_ui_circle(x, y, 34 * s, alpha(SANGUE_VIVO, 230))
    r.draw_ui_circle(x, y, 10 * s, alpha(PRETO, 255))
    r.draw_ui_circle(x, y, 22 * s, alpha(PRETO, 200), 2)
    for i in range(3):
        ang = t * 5 + i * 2 * math.pi / 3
        r.draw_ui_circle(x + math.cos(ang) * 22 * s, y + math.sin(ang) * 22 * s, 5 * s, PRETO)
    if k > 0.5:
        _impacto(r, a, b, (k - 0.5) / 0.5, t, forte)


def _dominio(r, a, b, k, t, forte):
    """Expansão de Domínio: o espaço se fecha num santuário."""
    raio = 900 * min(1.0, k * 1.8)
    r.draw_ui_circle(a[0], a[1], raio, alpha((24, 6, 16, 255), 190 * _sino(k * 0.9 + 0.1)))
    r.draw_ui_circle(a[0], a[1], raio, alpha(SANGUE_VIVO, 200 * (1 - k)), 4)
    if k > 0.35:  # o portal do santuário
        v = alpha(SANGUE_VIVO, 200 * (1 - k))
        cx, cy = LARGURA / 2, 180
        r.draw_ui_line(cx - 150, cy - 40, cx + 150, cy - 40, v, 10)
        r.draw_ui_line(cx - 120, cy - 10, cx + 120, cy - 10, v, 6)
        r.draw_ui_line(cx - 100, cy - 40, cx - 100, cy + 150, v, 8)
        r.draw_ui_line(cx + 100, cy - 40, cx + 100, cy + 150, v, 8)
        r.draw_text(cx, cy + 50, "領域展開", 34, v, anchor="center", font_id=FONTE_PINCEL)


def _tempo(r, a, b, k, t, forte):
    """The World: o tempo para — tudo em sépia e o relógio andando para trás."""
    s = _sino(k)
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(SEPIA, 110 * s))
    cx, cy = LARGURA / 2, ALTURA / 2 - 40
    r.draw_ui_circle(cx, cy, 120 * s, alpha(TINTA, 150 * s), 3)
    for i in range(12):
        ang = i * math.pi / 6
        r.draw_ui_line(
            cx + math.cos(ang) * 104 * s,
            cy + math.sin(ang) * 104 * s,
            cx + math.cos(ang) * 118 * s,
            cy + math.sin(ang) * 118 * s,
            alpha(TINTA, 180 * s),
            2,
        )
    ponteiro = -math.pi / 2 - k * math.pi * 2
    r.draw_ui_line(
        cx,
        cy,
        cx + math.cos(ponteiro) * 96 * s,
        cy + math.sin(ponteiro) * 96 * s,
        alpha(TINTA, 220 * s),
        4,
    )
    r.draw_text(
        cx, cy - 160, "時よ止まれ", 28, alpha(TINTA, 220 * s), anchor="center", font_id=FONTE_PINCEL
    )


def _trovao(r, a, b, k, t, forte):
    """Hekireki Issen: um raio — e o corte já aconteceu."""
    if k < 0.12:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(AMARELO, 120 * (1 - k / 0.12)))
    semente = math.floor(t * 30)
    _raio(r, a, b, alpha(AMARELO, 255 * (1 - k)), 5, semente)
    _raio(r, a, b, alpha(BRANCO, 200 * (1 - k)), 2, semente + 3)


def _clones(r, a, b, k, t, forte):
    """Kage Bunshin: três sombras cercam o alvo e golpeiam."""
    for i, (dx, atraso) in enumerate(((-110, 0.0), (110, 0.15), (0, 0.3))):
        prog = max(0.0, min(1.0, (k - atraso) / 0.55))
        if prog <= 0:
            continue
        x = b[0] + dx * (1 - prog * 0.6)
        y = b[1] + 80 - (20 if i == 2 else 0)
        desenhar_lutador(
            r, x, y, 0.62, alpha(TINTA, 120 * _sino(prog)), alpha(BRANCO, 90 * _sino(prog)), tempo=t
        )
    if k > 0.6:
        _impacto(r, a, b, (k - 0.6) / 0.4, t, forte)


def _cura(r, a, b, k, t, forte):
    """Ninjutsu Médico: luz verde subindo das mãos."""
    for i in range(14):
        s = i * 1.7
        x = a[0] + math.sin(s * 3.1) * 50
        y = a[1] + 40 - ((k * 120 + i * 13) % 120)
        r.draw_ui_circle(x, y, 3 + 2 * math.sin(s) ** 2, alpha(VERDE_JADE, 220 * (1 - k)))
    r.draw_ui_circle(a[0], a[1], 60, alpha(VERDE_JADE, 60 * _sino(k)))


def _espiral(r, a, b, k, t, forte):
    """Rasengan: a esfera que gira nas mãos e explode no alvo."""
    p = _lerp(a, b, min(1.0, k * 1.6))
    raio = 20 + 10 * min(1.0, k * 2)
    r.draw_ui_circle(p[0], p[1], raio + 10, alpha(AZUL_CHAKRA, 70))
    r.draw_ui_circle(p[0], p[1], raio, alpha(AZUL_CHAKRA, 220))
    for i in range(5):
        ini = t * 14 + i * 1.25
        r.draw_ui_arc(p[0], p[1], raio - 4 - i * 2, ini, ini + 1.6, alpha(BRANCO, 220), 2)
    if k > 0.62:
        q = (k - 0.62) / 0.38
        r.draw_ui_circle(b[0], b[1], 30 + 90 * q, alpha(AZUL_CHAKRA, 200 * (1 - q)), 5)


def _clarao_negro(r, a, b, k, t, forte):
    """Kokusen: faíscas negras com borda vermelha. No crítico, o mundo pisca."""
    if forte and k < 0.25:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(PRETO, 200 * (1 - k / 0.25)))
    semente = math.floor(t * 24)
    for i in range(5 if forte else 3):
        ang = i * 1.3 + semente
        fim = (b[0] + math.cos(ang) * 110, b[1] + math.sin(ang) * 90)
        _raio(r, b, fim, alpha(SANGUE_VIVO, 230 * (1 - k)), 7, semente + i)
        _raio(r, b, fim, alpha(PRETO, 255 * (1 - k)), 3, semente + i)


def _presa(r, a, b, k, t, forte):
    """Getsuga Tenshō: uma lua crescente de energia negra corta o ar."""
    p = _lerp(a, b, min(1.0, k * 1.3))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    r.draw_ui_arc(
        p[0], p[1], 60, -ang - 1.3, -ang + 1.3, alpha(SANGUE_VIVO, 230 * (1 - k * 0.6)), 14
    )
    r.draw_ui_arc(p[0], p[1], 56, -ang - 1.2, -ang + 1.2, alpha(PRETO, 255 * (1 - k * 0.6)), 8)


def _correntes(r, a, b, k, t, forte):
    """A Corrente do Julgamento: elos dourados prendem o alvo."""
    p = _lerp(a, b, min(1.0, k * 1.8))
    _corrente(r, a, p, alpha(OURO, 230 * (1 - max(0.0, k - 0.7) / 0.3)))
    if k > 0.55:
        q = (k - 0.55) / 0.45
        r.draw_ui_circle(b[0], b[1], 46, alpha(OURO, 200 * (1 - q)), 4)
        r.draw_text(
            b[0],
            b[1] - 80,
            "鎖",
            34,
            alpha(OURO, 255 * (1 - q)),
            anchor="center",
            font_id=FONTE_PINCEL,
        )


def _esfera(r, a, b, k, t, forte):
    """Genki Dama: a esfera cresce no alto com a energia de todos, e cai."""
    topo = (a[0] + 60, max(90, min(a[1] - 230, 230)))  # no alto, sem sair da tela
    if k < 0.55:
        raio = 20 + 90 * (k / 0.55)
        p = topo
    else:
        q = (k - 0.55) / 0.45
        raio = 110
        p = _lerp(topo, b, q)
    for i in range(10):  # a energia subindo para a esfera
        s = i * 2.3
        x0 = (math.sin(s) * 0.5 + 0.5) * LARGURA
        r.draw_ui_line(
            x0, ALTURA, *_lerp((x0, ALTURA), p, min(1.0, k * 2)), alpha(AZUL_CHAKRA, 60), 1
        )
    r.draw_ui_circle(p[0], p[1], raio + 14, alpha(AZUL_CHAKRA, 60))
    r.draw_ui_circle(p[0], p[1], raio, alpha(AZUL_CHAKRA, 170))
    r.draw_ui_circle(p[0], p[1], raio * 0.6, alpha(BRANCO, 120))


def _ilusao(r, a, b, k, t, forte):
    """Tsukuyomi: o mundo fica vermelho sob uma lua negra."""
    s = _sino(k)
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha((90, 0, 0, 255), 170 * s))
    cx, cy = LARGURA / 2, 150
    r.draw_ui_circle(cx, cy, 90 * s, alpha(PRETO, 255))
    r.draw_ui_circle(cx, cy, 90 * s, alpha(SANGUE_VIVO, 230), 3)
    for i in range(3):
        ang = -t * 2 + i * 2 * math.pi / 3
        r.draw_ui_circle(
            cx + math.cos(ang) * 50 * s,
            cy + math.sin(ang) * 50 * s,
            10 * s,
            alpha(SANGUE_VIVO, 230),
        )
    r.draw_text(
        cx, cy + 130, "月読", 32, alpha(TINTA, 230 * s), anchor="center", font_id=FONTE_PINCEL
    )


def _corte_mundo(r, a, b, k, t, forte):
    """O corte que divide o mundo: uma linha atravessa a tela, e a tela se parte."""
    x0, y0, x1, y1 = -40, ALTURA * 0.2, LARGURA + 40, ALTURA * 0.55
    if k < 0.3:
        prog = k / 0.3
        r.draw_ui_line(x0, y0, x0 + (x1 - x0) * prog, y0 + (y1 - y0) * prog, alpha(BRANCO, 255), 2)
        return
    q = (k - 0.3) / 0.7
    if q < 0.15:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(BRANCO, 230 * (1 - q / 0.15)))
    abre = 10 + 16 * _sino(q)
    r.draw_ui_polygon(
        [(x0, y0 - abre / 2), (x1, y1 - abre / 2), (x1, y1 + abre / 2), (x0, y0 + abre / 2)],
        alpha(PRETO, 255 * (1 - q * 0.8)),
    )
    r.draw_ui_line(x0, y0 - abre / 2, x1, y1 - abre / 2, alpha(BRANCO, 230 * (1 - q)), 2)
    r.draw_ui_line(x0, y0 + abre / 2, x1, y1 + abre / 2, alpha(BRANCO, 230 * (1 - q)), 2)


def _fogo(r, a, b, k, t, forte):
    """Katon: uma bola de fogo que voa e se abre em labaredas."""
    p = _lerp(a, b, min(1.0, k * 1.4))
    cores = ((255, 120, 40, 255), (255, 190, 80, 255), AMARELO)
    for i in range(3):
        raio = (34 - i * 9) * (0.6 + 0.4 * _sino(k))
        r.draw_ui_circle(p[0], p[1], raio, alpha(cores[i], 200 * (1 - k * 0.6)))
    if k > 0.6:
        abre = (k - 0.6) / 0.4
        for i in range(12):
            ang = -math.pi / 2 + (i - 6) * 0.22
            alto = 40 + 50 * abre * (0.6 + 0.4 * math.sin(t * 11 + i))
            r.draw_ui_line(
                b[0] + (i - 6) * 8,
                b[1] + 30,
                b[0] + math.cos(ang) * 30,
                b[1] - alto,
                alpha((255, 140, 40, 255), 190 * (1 - abre)),
                4,
            )


def _gelo(r, a, b, k, t, forte):
    """Hyorinmaru: cristais de gelo que crescem em volta do alvo."""
    cresce = min(1.0, k * 1.8)
    for i in range(8):
        ang = i * 2 * math.pi / 8 + 0.2
        comp = 30 + 40 * cresce * (0.7 + 0.3 * math.sin(i * 2.3))
        base = (b[0] + math.cos(ang) * 10, b[1] + math.sin(ang) * 10)
        ponta = (b[0] + math.cos(ang) * comp, b[1] + math.sin(ang) * comp)
        lado = (math.cos(ang + math.pi / 2) * 7, math.sin(ang + math.pi / 2) * 7)
        r.draw_ui_polygon(
            [(base[0] + lado[0], base[1] + lado[1]), ponta, (base[0] - lado[0], base[1] - lado[1])],
            alpha((190, 230, 255, 255), 210 * (1 - k * 0.5)),
        )
    r.draw_ui_circle(b[0], b[1], 50 * cresce, alpha(BRANCO, 90 * (1 - k)), 2)


def _veneno(r, a, b, k, t, forte):
    """Kikaichu: gotas verdes que caem e borbulham no alvo."""
    for i in range(10):
        fase = (k * 1.6 + i * 0.13) % 1.0
        x = b[0] + (i - 5) * 11 + math.sin(t * 5 + i) * 4
        y = b[1] - 60 + 90 * fase
        r.draw_ui_circle(x, y, 4 + 3 * math.sin(i), alpha((120, 200, 90, 255), 220 * (1 - k)))
    r.draw_ui_circle(b[0], b[1] + 30, 30 * _sino(k), alpha((90, 160, 60, 255), 120 * (1 - k)), 3)


def _vento(r, a, b, k, t, forte):
    """Kamaitachi: arcos de vento cortante que atravessam o alvo."""
    for i in range(4):
        prog = max(0.0, min(1.0, k * 1.6 - i * 0.15))
        if prog <= 0:
            continue
        c = _lerp(a, b, prog)
        ini = math.atan2(b[1] - a[1], b[0] - a[0]) - 1.1 + i * 0.2
        cor = alpha(BRANCO, 200 * (1 - prog * 0.6))
        r.draw_ui_arc(c[0], c[1], 40 + i * 10, ini, ini + 2.2, cor, 3)


def _explosao(r, a, b, k, t, forte):
    """Kibaku Fuda: o pavio corre e a tinta explode."""
    if k < 0.45:
        p = _lerp(a, b, k / 0.45)
        r.draw_ui_line(a[0], a[1], p[0], p[1], alpha(SEPIA, 180), 2)
        r.draw_ui_circle(p[0], p[1], 5, AMARELO)
        return
    abre = (k - 0.45) / 0.55
    cores = ((255, 230, 150, 255), (255, 140, 40, 255), PRETO)
    for i, cor in enumerate(cores):
        raio = (30 + 80 * abre) * (1 - i * 0.25)
        r.draw_ui_circle(b[0], b[1], raio, alpha(cor, 200 * (1 - abre)), 0 if i < 2 else 3)
    for i in range(14):
        ang = i * 2 * math.pi / 14
        r.draw_ui_line(
            b[0] + math.cos(ang) * 30 * abre,
            b[1] + math.sin(ang) * 30 * abre,
            b[0] + math.cos(ang) * 110 * abre,
            b[1] + math.sin(ang) * 110 * abre,
            alpha(TINTA, 200 * (1 - abre)),
            3,
        )


# ----------------------------------------------------------------------- fusões e assinaturas

VERMELHO_VIVO = (255, 70, 60, 255)
LARANJA = (255, 140, 40, 255)
ROSA = (255, 170, 200, 255)


def _faixa(r: IRenderer, a: Ponto, b: Ponto, largura: float, cor: Cor) -> None:
    """Um feixe reto de a até b com essa largura."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    nx, ny = -math.sin(ang) * largura / 2, math.cos(ang) * largura / 2
    r.draw_ui_polygon(
        [
            (a[0] + nx, a[1] + ny),
            (b[0] + nx, b[1] + ny),
            (b[0] - nx, b[1] - ny),
            (a[0] - nx, a[1] - ny),
        ],
        cor,
    )


def _feixe(r, a, b, k, t, forte):
    """Kaioken Kamehameha: a onda carrega nas mãos, em brasa, e sai num feixe que atravessa."""
    if k < 0.35:
        c = k / 0.35
        raio = 8 + 26 * c
        r.draw_ui_circle(a[0], a[1], raio + 16, alpha(VERMELHO_VIVO, 80 * c))
        r.draw_ui_circle(a[0], a[1], raio, alpha(AZUL_CHAKRA, 230))
        r.draw_ui_circle(a[0], a[1], raio * 0.5, alpha(BRANCO, 240))
        for i in range(12):  # o ki sugado para as mãos
            ang = i * 0.52 + i * i * 0.1
            d = 30 + 90 * (1 - ((t * 2.2 + i * 0.083) % 1.0))
            px, py = a[0] + math.cos(ang) * d, a[1] + math.sin(ang) * d
            r.draw_ui_circle(px, py, 2.5, alpha(VERMELHO_VIVO, 210))
        return
    q = (k - 0.35) / 0.65
    some = 1 - max(0.0, (q - 0.6) / 0.4)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    fim = (b[0] + math.cos(ang) * 900, b[1] + math.sin(ang) * 900)
    ponta = _lerp(a, fim, min(1.0, q * 3))
    vibra = 0.85 + 0.15 * math.sin(t * 50)
    for largura, cor, op in ((58, VERMELHO_VIVO, 110), (36, AZUL_CHAKRA, 210), (14, BRANCO, 255)):
        _faixa(r, a, ponta, largura * vibra * some, alpha(cor, op * some))
    r.draw_ui_circle(a[0], a[1], 36 * some, alpha(BRANCO, 220 * some))
    if q > 0.18:
        u = min(1.0, (q - 0.18) / 0.5)
        r.draw_ui_circle(b[0], b[1], 40 + 70 * u, alpha(BRANCO, 200 * (1 - u)), 5)


def _raio_na_mao(r, a, b, k, t, forte):
    """Raikiri: o raio estala na mão, e a mão atravessa o alvo num risco só."""
    semente = math.floor(t * 30)
    if k < 0.45:
        c = k / 0.45
        r.draw_ui_circle(a[0], a[1] + 20, 14 + 10 * c, alpha(AZUL_CHAKRA, 230))
        r.draw_ui_circle(a[0], a[1] + 20, 7, alpha(BRANCO, 255))
        for i in range(6):
            ang = i * 1.05 + _ruido(semente + i) * 2
            fim = (a[0] + math.cos(ang) * 60 * c, a[1] + 20 + math.sin(ang) * 60 * c)
            _raio(r, (a[0], a[1] + 20), fim, alpha(BRANCO, 220), 2, semente + i * 3)
        if int(t * 40) % 2:
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(AZUL_CHAKRA, 18))
        return
    q = (k - 0.45) / 0.55
    p = _lerp(a, b, min(1.0, q * 2.5))
    _raio(r, a, p, alpha(AZUL_CHAKRA, 255 * (1 - q)), 6, semente)
    _raio(r, a, p, alpha(BRANCO, 230 * (1 - q)), 2, semente + 5)
    r.draw_ui_circle(p[0], p[1], 18 * (1 - q) + 6, alpha(BRANCO, 240 * (1 - q)))
    if q > 0.35:
        u = (q - 0.35) / 0.65
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        dx, dy = math.cos(ang) * 120, math.sin(ang) * 120
        cor = alpha(BRANCO, 255 * (1 - u))
        r.draw_ui_line(b[0] - dx, b[1] - dy, b[0] + dx * (1 + u), b[1] + dy * (1 + u), cor, 4)


def _punho_gigante(r, a, b, k, t, forte):
    """King Kong Gun: o punho inflado, duro de Haki, do tamanho de um homem."""
    p = _lerp(a, b, ease_out(min(1.0, k / 0.45)))
    escala = 0.6 + 0.4 * min(1.0, k / 0.3)
    preto, rubro = (18, 12, 14, 255), (150, 30, 34, 255)
    r.draw_ui_line(a[0], a[1], p[0], p[1], alpha(rubro, 220), 26)
    r.draw_ui_circle(p[0], p[1], 64 * escala, alpha(preto, 245))
    r.draw_ui_circle(p[0], p[1], 64 * escala, alpha(rubro, 230), 4)
    sentido = 1 if b[1] >= a[1] else -1
    for i in range(4):  # os nós dos dedos, de frente para o alvo
        nx = p[0] + (i - 1.5) * 26 * escala
        ny = p[1] + sentido * 40 * escala
        r.draw_ui_circle(nx, ny, 15 * escala, alpha(preto, 255))
        r.draw_ui_circle(nx, ny, 15 * escala, alpha(rubro, 200), 2)
    if k > 0.45:
        u = (k - 0.45) / 0.55
        for i in range(3):
            raio = (60 + 150 * u) * (1 - i * 0.22)
            r.draw_ui_circle(b[0], b[1], raio, alpha(TINTA, 200 * (1 - u)), 5 - i)
        for i in range(12):  # o chão que voa
            ang = i * math.pi / 6 + 0.2
            d = 40 + 160 * u
            r.draw_ui_circle(
                b[0] + math.cos(ang) * d,
                b[1] + math.sin(ang) * d * 0.6 + 120 * u * u,
                4 + 3 * abs(_ruido(i)),
                alpha(SEPIA, 230 * (1 - u)),
            )


def _trovao_flamejante(r, a, b, k, t, forte):
    """Honoikazuchi no Kami: um passo de trovão e um dragão de fogo no rastro."""
    if k < 0.1:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(LARANJA, 110 * (1 - k / 0.1)))
    semente = math.floor(t * 30)
    _raio(r, a, b, alpha(LARANJA, 255 * (1 - k)), 7, semente)
    _raio(r, a, b, alpha(AMARELO, 230 * (1 - k)), 2, semente + 4)
    for i in range(16):  # o corpo do dragão: chamas ao longo do caminho, ondulando
        s = i / 15
        c = _lerp(a, b, s)
        onda = math.sin(s * 9 + t * 12) * 34 * (1 - s * 0.4)
        ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
        x, y = c[0] + math.cos(ang) * onda, c[1] + math.sin(ang) * onda
        vida = max(0.0, 1 - k * 1.2 - (1 - s) * 0.3)
        r.draw_ui_circle(x, y, (14 - 6 * s) * (0.6 + vida), alpha(LARANJA, 200 * vida))
        r.draw_ui_circle(x, y, (7 - 3 * s) * (0.6 + vida), alpha(AMARELO, 230 * vida))
    if k > 0.3:
        _corte_x(r, a, b, (k - 0.3) / 0.7, t, forte)


def _vermelho(r, a, b, k, t, forte):
    """Técnica Reversa: Vermelho. A esfera rubra nasce na ponta do dedo e empurra tudo."""
    if k < 0.3:
        c = k / 0.3
        r.draw_ui_circle(a[0], a[1], 10 + 18 * c, alpha(VERMELHO_VIVO, 240))
        r.draw_ui_circle(a[0], a[1], 26 + 30 * c, alpha(VERMELHO_VIVO, 60), 3)
        return
    q = (k - 0.3) / 0.7
    p = _lerp(a, b, min(1.0, q * 3))
    r.draw_ui_circle(p[0], p[1], 26 * (1 - q * 0.5), alpha(VERMELHO_VIVO, 240 * (1 - q)))
    if q > 0.3:
        u = (q - 0.3) / 0.7
        for i in range(4):
            raio = (u * 1.4 - i * 0.14) * 420
            if raio > 0:
                r.draw_ui_circle(b[0], b[1], raio, alpha(VERMELHO_VIVO, 180 * (1 - u)), 5)
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(VERMELHO_VIVO, 50 * (1 - u)))


def _espirais(r, a, b, k, t, forte):
    """Rasen Tarengan: três clones, três esferas, uma depois da outra."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
    for i, desvio in enumerate((-90, 90, 0)):
        prog = max(0.0, min(1.0, (k - i * 0.15) / 0.55))
        if prog <= 0:
            continue
        inicio = (a[0] + math.cos(ang) * desvio, a[1] + math.sin(ang) * desvio)
        if prog < 1:
            _espiral(r, inicio, b, prog * 0.62, t + i, forte)
        else:
            u = min(1.0, (k - i * 0.15 - 0.55) / 0.3)
            r.draw_ui_circle(b[0], b[1], 30 + 90 * u, alpha(AZUL_CHAKRA, 200 * (1 - u)), 5)


def _transmutacao(r, a, b, k, t, forte):
    """Transmutação sem círculo: as palmas se juntam, o raio azul corre pelo chão e a
    pedra sobe em lanças debaixo do alvo."""
    if k < 0.2:
        c = k / 0.2
        r.draw_ui_line(a[0] - 40 * (1 - c), a[1], a[0], a[1], alpha(TINTA, 230), 4)
        r.draw_ui_line(a[0] + 40 * (1 - c), a[1], a[0], a[1], alpha(TINTA, 230), 4)
        if c > 0.8:
            r.draw_ui_circle(a[0], a[1], 30, alpha(BRANCO, 220))
        return
    chao_a, chao_b = (a[0], a[1] + 70), (b[0], b[1] + 70)
    q = (k - 0.2) / 0.8
    semente = math.floor(t * 24)
    p = _lerp(chao_a, chao_b, min(1.0, q * 2.2))
    _raio(r, chao_a, p, alpha(AZUL_CHAKRA, 230 * (1 - q * 0.6)), 3, semente)
    _raio(r, chao_a, p, alpha(BRANCO, 200 * (1 - q * 0.6)), 1, semente + 2)
    if q > 0.45:
        u = (q - 0.45) / 0.55
        sobe = ease_out(min(1.0, u * 2.2))
        pedra = (140, 120, 100, 255)
        for i, (dx, alto) in enumerate(((-36, 90), (0, 130), (34, 100), (-62, 60), (60, 70))):
            base = chao_b[0] + dx
            topo = chao_b[1] - alto * sobe
            r.draw_ui_polygon(
                [(base - 12, chao_b[1]), (base + 12, chao_b[1]), (base + 2 * _ruido(i), topo)],
                alpha(pedra, 240 * (1 - max(0.0, u - 0.7) / 0.3)),
            )


def desenhar_roda(r: IRenderer, x: float, y: float, raio: float, giro: float, cor: Cor) -> None:
    """A roda de oito raios do general (a que gira quando ele se adapta)."""
    larg = max(1, round(raio / 10))
    for i in range(8):
        ang = giro + i * math.pi / 4
        c, s = math.cos(ang), math.sin(ang)
        r.draw_ui_line(
            x + c * raio * 0.22, y + s * raio * 0.22, x + c * raio, y + s * raio, cor, larg
        )
        r.draw_ui_circle(x + c * raio * 1.14, y + s * raio * 1.14, raio * 0.13, cor)
    r.draw_ui_circle(x, y, raio * 0.8, cor, larg + 1)
    r.draw_ui_circle(x, y, raio * 0.2, cor)


def _roda_dharma(r, a, b, k, t, forte):
    """O General da Roda: a roda surge no alto, gira uma casa, e o general desce."""
    s = _sino(min(1.0, k * 1.15))
    giro = math.pi / 4 * ease_out(max(0.0, min(1.0, (k - 0.35) / 0.2)))
    cx, cy = a[0], a[1] - 130
    r.draw_ui_circle(cx, cy, 70 * s, alpha(OURO, 50 * s))
    desenhar_roda(r, cx, cy, 56 * s, giro, alpha(OURO, 240 * s))
    if k > 0.5:  # a luz que desce até o chão
        u = (k - 0.5) / 0.5
        _faixa(r, (cx, cy), (cx, a[1] + 80), 40 * (1 - u), alpha(OURO, 120 * (1 - u)))


def _rachaduras(r: IRenderer, x: float, y: float, k: float, cor: Cor, n: int = 9) -> None:
    """Riscos de vidro que se abrem a partir de (x, y), com anéis entre eles."""
    alcance = 720 * ease_out(min(1.0, k))
    pontas = []
    for i in range(n):
        ang = i * 2 * math.pi / n + _ruido(i * 3.3) * 0.5
        anterior = (x, y)
        trilha = []
        for passo in range(1, 6):
            d = alcance * passo / 5
            desvio = _ruido(i * 7 + passo) * 0.3
            p = (x + math.cos(ang + desvio) * d, y + math.sin(ang + desvio) * d)
            r.draw_ui_line(anterior[0], anterior[1], p[0], p[1], cor, 2)
            trilha.append(p)
            anterior = p
        pontas.append(trilha)
    for anel in (0, 1):  # os anéis ligam os riscos (o vidro estrelado)
        for i in range(n):
            p, q = pontas[i][anel], pontas[(i + 1) % n][anel]
            r.draw_ui_line(p[0], p[1], q[0], q[1], alpha(cor, cor[3] * 0.6), 1)


def vidro_quebrando(r: IRenderer, x: float, y: float, k: float) -> None:
    """Kyoka Suigetsu: o que você viu era um espelho. Ele racha a partir de (x, y), os
    cacos caem e o nome da ilusão aparece."""
    if not 0 <= k < 1:
        return
    vidro = (210, 230, 255, 255)
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(vidro, 60 * (1 - k)))
    if k < 0.55:
        _rachaduras(r, x, y, k / 0.3, alpha(BRANCO, 230))
    if k > 0.3:
        u = (k - 0.3) / 0.7
        for i in range(22):
            ang = i * 2 * math.pi / 22 + _ruido(i) * 0.8
            d = 60 + 280 * abs(_ruido(i * 1.7))
            cx = x + math.cos(ang) * d + _ruido(i * 2.3) * 40 * u
            cy = y + math.sin(ang) * d * 0.6 + 520 * u * u
            tam = 10 + 12 * abs(_ruido(i * 5.1))
            giro = ang + u * 5 * _ruido(i * 3)
            pts = [
                (cx + math.cos(giro + j * 2.2) * tam, cy + math.sin(giro + j * 2.2) * tam)
                for j in range(3)
            ]
            r.draw_ui_polygon(pts, alpha(vidro, 200 * (1 - u)))
            r.draw_ui_polygon(pts, alpha(BRANCO, 230 * (1 - u)), 1)
    brilho = 255 * _sino(min(1.0, k * 1.4))
    r.draw_text(
        LARGURA / 2,
        210,
        "鏡花水月",
        46,
        alpha(vidro, brilho),
        anchor="center",
        font_id=FONTE_PINCEL,
    )


def _espelho(r, a, b, k, t, forte):
    """Flor no Espelho: a lâmina reflete, o mundo vira espelho e se quebra no alvo."""
    if k < 0.3:
        c = k / 0.3
        r.draw_ui_line(a[0], a[1] - 60, a[0], a[1] + 50, alpha(BRANCO, 240 * c), 4)
        r.draw_ui_circle(a[0], a[1] - 60, 12 * c, alpha(BRANCO, 200))
        return
    q = (k - 0.3) / 0.7
    _rachaduras(r, b[0], b[1], q / 0.5, alpha((210, 230, 255, 255), 230 * (1 - q)), 7)
    for i in range(10):  # as pétalas da flor que nunca existiu
        fase = (q + i * 0.1) % 1.0
        px = b[0] + math.sin(i * 2.1 + q * 4) * 90
        py = b[1] - 100 + fase * 200
        r.draw_ui_circle(px, py, 4, alpha(ROSA, 230 * (1 - q)))


# ----------------------------------------------------------------------- a luta: cinema


def _suave(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _estrela(r: IRenderer, x: float, y: float, tam: float, cor: Cor, giro: float = 0.0) -> None:
    pts = []
    for i in range(10):
        raio = tam if i % 2 == 0 else tam * 0.45
        ang = giro - math.pi / 2 + i * math.pi / 5
        pts.append((x + math.cos(ang) * raio, y + math.sin(ang) * raio))
    r.draw_ui_polygon(pts, cor)


def cut_in(
    r: IRenderer,
    k: float,
    kanji: str,
    nome: str,
    origem: str = "",
    rotulo: str = "",
    rival: bool = False,
    estilo: str = "espadachim",
    relogio: float = 0.0,
) -> None:
    """O cut-in de técnica: uma faixa diagonal atravessa a tela com o kanji gigante, o
    nome, a origem e a silhueta de quem usa, em pose. O seu vem da esquerda, em ouro;
    o do rival, da direita, cor de sangue. `k` 0–1: entra, segura e corta para fora."""
    if not 0 <= k < 1:
        return
    entra = _suave(k / 0.16)
    sai = _suave((k - 0.8) / 0.2)
    lado = -1 if rival else 1
    cor = SANGUE_VIVO if rival else OURO
    fundo = (54, 6, 10, 240) if rival else (12, 10, 9, 240)
    vis = 1 - sai
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(PRETO, 140 * entra * vis))

    def yc(x: float) -> float:  # o meio da faixa: sobe para o lado de onde ela não veio
        return 318 + lado * (LARGURA / 2 - x) * 0.18

    meia = 96 * (1 - sai * 0.92)
    desliza = -lado * (1 - entra) * 1100
    x0, x1 = -80 + desliza, LARGURA + 80 + desliza
    r.draw_ui_polygon(
        [(x0, yc(x0) - meia), (x1, yc(x1) - meia), (x1, yc(x1) + meia), (x0, yc(x0) + meia)],
        alpha(fundo, fundo[3] * vis + 15 * sai),
    )
    for borda, larg in ((meia, 4), (meia + 9, 1)):
        for s in (-1, 1):
            r.draw_ui_line(
                x0, yc(x0) + s * borda, x1, yc(x1) + s * borda, alpha(cor, 230 * vis), larg
            )
    for i in range(18):  # o vento da faixa: riscos que correm no sentido dela
        v = (_ruido(i * 3.7) * 2) * meia * 0.9
        comp = 90 + 140 * abs(_ruido(i * 1.3))
        xs = ((i * 151 + relogio * 2200) % 1400) - 220
        xs = xs if lado > 0 else LARGURA - xs
        xa, xb = xs + desliza, xs + desliza - lado * comp
        r.draw_ui_line(xa, yc(xa) + v, xb, yc(xb) + v, alpha(TINTA, 60 * vis), 2)
    # a silhueta em pose, saindo da faixa
    xf = (770 if not rival else 190) + desliza
    desenhar_lutador(
        r,
        xf,
        yc(xf) + meia - 6,
        1.8 * (1 - sai * 0.2),
        alpha(PRETO, 255 * vis),
        alpha(cor, 235 * vis),
        estilo=estilo,
        tempo=relogio,
        ataque=0.9,
        respiro=0.0,
    )
    xk = (220 if not rival else 740) + desliza
    tam = 150 + 8 * round(5 * (1 - entra))  # o kanji chega grande e assenta
    a_txt = 255 * entra * vis
    r.draw_text(xk + 7, yc(xk) + 5, kanji, tam, alpha(cor, a_txt * 0.6), "center", FONTE_PINCEL)
    r.draw_text(xk, yc(xk), kanji, tam, alpha(TINTA, a_txt), "center", FONTE_PINCEL)
    xn = (318 if not rival else 642) + desliza
    ancora = "topleft" if not rival else "topright"
    tam_nome = 38 if len(nome) <= 18 else max(26, round(38 * 18 / len(nome)))
    y_nome = yc(xn) - 30
    if rotulo:
        r.draw_text(xn, y_nome - 24, rotulo, 16, alpha(cor, a_txt * 0.9), ancora, FONTE_PINCEL)
    r.draw_text(xn, y_nome, nome, tam_nome, alpha(TINTA, a_txt), ancora, FONTE_PINCEL)
    if origem:
        y_or = y_nome + tam_nome + 8
        r.draw_text(xn, y_or, f"※ {origem}", 15, alpha(TINTA, a_txt * 0.6), ancora, FONTE_PINCEL)
    if sai > 0:  # a saída: a faixa vira um corte de luz
        r.draw_ui_line(x0, yc(x0), x1, yc(x1), alpha(BRANCO, 255 * vis), 3)


def linhas_de_velocidade(
    r: IRenderer, x: float, y: float, k: float, relogio: float, cor: Cor = TINTA
) -> None:
    """As linhas de foco do anime: riscos das bordas para o alvo (golpes rápidos)."""
    if not 0 <= k < 1:
        return
    s = _sino(k)
    semente = math.floor(relogio * 24)
    for i in range(32):
        ang = i * 2 * math.pi / 32 + _ruido(semente + i) * 0.12
        d0 = 250 + 140 * abs(_ruido(semente * 1.3 + i * 7))
        c, sn = math.cos(ang), math.sin(ang)
        r.draw_ui_line(
            x + c * d0,
            y + sn * d0,
            x + c * 800,
            y + sn * 800,
            alpha(cor, 75 * s),
            3 if i % 3 else 2,
        )


def perigo(r: IRenderer, relogio: float, forca: float = 1.0) -> None:
    """O aviso de perigo: as bordas da tela pulsam em vermelho (só nas bordas: o meio e
    as barras ficam livres)."""
    pulso = 0.5 + 0.5 * math.sin(relogio * 5.5)
    a = forca * (0.4 + 0.6 * pulso)
    for larg, op in ((14, 40), (7, 55), (3, 120)):
        cor = alpha(SANGUE_VIVO, op * a)
        r.draw_ui_rect(0, 0, LARGURA, larg, cor)
        r.draw_ui_rect(0, ALTURA - larg, LARGURA, larg, cor)
        r.draw_ui_rect(0, 0, larg, ALTURA, cor)
        r.draw_ui_rect(LARGURA - larg, 0, larg, ALTURA, cor)
    linha = alpha(SANGUE_VIVO, 230 * a)
    m, c = 10, 46  # os cantos: colchetes vermelhos
    for cx, cy, sx, sy in (
        (m, m, 1, 1),
        (LARGURA - m, m, -1, 1),
        (m, ALTURA - m, 1, -1),
        (LARGURA - m, ALTURA - m, -1, -1),
    ):
        r.draw_ui_line(cx, cy, cx + sx * c, cy, linha, 3)
        r.draw_ui_line(cx, cy, cx, cy + sy * c, linha, 3)


def brilho_perigo(r: IRenderer, x: float, y: float, raio: float, relogio: float) -> None:
    """O rival que prepara o golpe perigoso: um halo vermelho que pulsa atrás dele."""
    pulso = 0.5 + 0.5 * math.sin(relogio * 5.5)
    r.draw_ui_circle(x, y, raio * (1.05 + 0.08 * pulso), alpha(SANGUE_VIVO, 18 + 22 * pulso))
    giro = relogio * 1.6
    r.draw_ui_arc(x, y, raio * 1.12, giro, giro + 2.2, alpha(SANGUE_VIVO, 120 + 80 * pulso), 3)
    r.draw_ui_arc(
        x, y, raio * 1.12, giro + 3.1, giro + 5.3, alpha(SANGUE_VIVO, 120 + 80 * pulso), 3
    )


def estilhaco(r: IRenderer, x: float, y: float, k: float, escala: float = 1.0) -> None:
    """A guarda quebrando: riscos que se abrem e cacos que voam e caem."""
    if not 0 <= k < 1:
        return
    if k < 0.35:
        _rachaduras(r, x, y, k / 0.35 * 0.2, alpha(BRANCO, 240 * (1 - k / 0.35)), 7)
    r.draw_ui_circle(x, y, (30 + 110 * ease_out(k)) * escala, alpha(BRANCO, 220 * (1 - k)), 3)
    for i in range(16):
        ang = i * 2 * math.pi / 16 + _ruido(i) * 0.6
        v = (110 + 100 * abs(_ruido(i * 3.1))) * escala
        d = v * ease_out(k)
        cx = x + math.cos(ang) * d
        cy = y + math.sin(ang) * d + 170 * k * k * escala
        tam = (8 + 7 * abs(_ruido(i * 5))) * escala * (1 - k * 0.4)
        giro = ang + k * 7 * _ruido(i * 7)
        pts = [
            (cx + math.cos(giro + j * 2.3) * tam, cy + math.sin(giro + j * 2.3) * tam)
            for j in range(3)
        ]
        cor = (200, 220, 255, 255) if i % 3 else BRANCO
        r.draw_ui_polygon(pts, alpha(cor, 235 * (1 - k)))


def tonto(r: IRenderer, x: float, y: float, relogio: float, escala: float = 1.0) -> None:
    """Tonto (guarda quebrada): estrelinhas girando em volta da cabeça e um redemoinho."""
    for i in range(3):
        ang = relogio * 4 + i * 2 * math.pi / 3
        sx = x + math.cos(ang) * 28 * escala
        sy = y + math.sin(ang) * 9 * escala
        frente = math.sin(ang) > 0
        _estrela(
            r,
            sx,
            sy,
            (7 if frente else 5) * escala,
            alpha(AMARELO, 245 if frente else 140),
            relogio * 3,
        )
    for i in range(2):
        ini = relogio * 6 + i * math.pi
        r.draw_ui_arc(x, y - 2, (12 - 4 * i) * escala, ini, ini + 3.6, alpha(TINTA, 150), 2)


def selo_mecanica(
    r: IRenderer, x: float, y: float, kanji: str, raio: float, cor: Cor, fundo: Cor = PRETO
) -> None:
    """Um selo redondo pequeno com um kanji (afixo, mecânica, ressonância)."""
    r.draw_ui_circle(x, y, raio + 2, alpha(fundo, 200))
    r.draw_ui_circle(x, y, raio, cor, 2)
    tam = max(10, round(raio * 1.25))
    r.draw_text(x, y - 1, kanji, tam, cor, anchor="center", font_id=FONTE_PINCEL)


def roda_adapta(r: IRenderer, x: float, y: float, k: float, giro: float) -> None:
    """Mahoraga se adapta: a roda grande aparece, gira uma casa com um estalo e
    mostra 適応."""
    if not 0 <= k < 1:
        return
    s = _sino(min(1.0, k * 1.1))
    vira = giro + math.pi / 4 * ease_out(max(0.0, min(1.0, (k - 0.25) / 0.18)))
    if 0.25 <= k < 0.45:  # o estalo
        r.draw_ui_circle(x, y, 90, alpha(OURO, 90 * (1 - (k - 0.25) / 0.2)))
    desenhar_roda(r, x, y, 62 * (0.7 + 0.3 * s), vira, alpha(OURO, 250 * s))
    r.draw_text(x, y + 84, "適応", 34, alpha(OURO, 255 * s), anchor="center", font_id=FONTE_PINCEL)


def selo_contrato(r: IRenderer, x: float, y: float, k: float) -> None:
    """Makima: o contrato cobra. O selo vermelho se abre e as correntes saem dele."""
    if not 0 <= k < 1:
        return
    s = _sino(k)
    raio = 40 + 30 * ease_out(min(1.0, k * 2))
    r.draw_ui_circle(x, y, raio, alpha(SANGUE_VIVO, 70 * s))
    r.draw_ui_circle(x, y, raio, alpha(SANGUE_VIVO, 240 * s), 3)
    r.draw_ui_circle(x, y, raio * 0.78, alpha(SANGUE_VIVO, 200 * s), 1)
    r.draw_text(x, y - 2, "契", 44, alpha(BRANCO, 255 * s), anchor="center", font_id=FONTE_PINCEL)
    for i in range(4):
        ang = i * math.pi / 2 + math.pi / 4 + k
        fim = (x + math.cos(ang) * (raio + 120 * k), y + math.sin(ang) * (raio + 120 * k))
        _corrente(
            r, (x + math.cos(ang) * raio, y + math.sin(ang) * raio), fim, alpha(OURO, 200 * s)
        )


def carga(r: IRenderer, x: float, y: float, n: int, relogio: float, escala: float = 1.0) -> None:
    """Leigan: as cargas do Disparo, esferas que giram em volta dele e um brilho que cresce."""
    if n <= 0:
        return
    pulso = 0.5 + 0.5 * math.sin(relogio * 7)
    r.draw_ui_circle(x, y, (70 + 12 * n) * escala, alpha(AZUL_CHAKRA, (18 + 12 * pulso) * n))
    for i in range(n * 2):
        ang = relogio * 2.4 + i * math.pi / n
        px = x + math.cos(ang) * 62 * escala
        py = y + math.sin(ang) * 22 * escala - 10 * escala
        r.draw_ui_circle(px, py, 7 * escala, alpha(AZUL_CHAKRA, 220))
        r.draw_ui_circle(px, py, 3.5 * escala, alpha(BRANCO, 240))


def armadura(r: IRenderer, x: float, y: float, k: float, escala: float = 1.0) -> None:
    """O Susanoo: costelas de energia se fecham em volta do corpo."""
    if not 0 <= k < 1:
        return
    s = _sino(k)
    cor = alpha((150, 110, 230, 255), 220 * s)
    for i in range(4):
        raio = (58 + i * 14) * escala * (0.6 + 0.4 * ease_out(min(1.0, k * 2)))
        r.draw_ui_arc(x, y + 10 * escala, raio, math.radians(200), math.radians(340), cor, 4)
        r.draw_ui_arc(x, y + 10 * escala, raio, math.radians(20), math.radians(160), cor, 2)


def vortice(r: IRenderer, x: float, y: float, k: float, escala: float = 1.0) -> None:
    """Kamui: o corpo vira um redemoinho e o golpe atravessa."""
    if not 0 <= k < 1:
        return
    s = _sino(k)
    for i in range(5):
        ini = k * 12 + i * 1.25
        raio = (14 + i * 12) * escala
        r.draw_ui_arc(x, y, raio, ini, ini + 2.4, alpha((40, 30, 50, 255), 220 * s), 3)
        r.draw_ui_arc(x, y, raio, ini + 3.1, ini + 4.4, alpha(TINTA, 150 * s), 1)


def petalas(r: IRenderer, x: float, y: float, relogio: float, escala: float = 1.0) -> None:
    """Senbonzakura: pétalas que giram em volta dele o tempo todo."""
    for i in range(14):
        fase = (relogio * 0.35 + i / 14) % 1.0
        ang = i * 2.4 + relogio * 1.3
        px = x + math.cos(ang) * (70 + 30 * math.sin(i)) * escala
        py = y - 60 * escala + fase * 150 * escala + math.sin(ang) * 14 * escala
        r.draw_ui_circle(px, py, 3.2 * escala, alpha(ROSA, 200 * _sino(fase)))


def _hesitar(r, a, b, k, t, forte):
    """Sem efeito: o turno passa."""


@dataclass(frozen=True)
class Efeito:
    desenho: Callable
    duracao: float = 0.6


EFEITOS: dict[str, Efeito] = {
    "impacto": Efeito(_impacto),
    "punho": Efeito(_punho),
    "guarda": Efeito(_guarda),
    "investida": Efeito(_investida),
    "corte_x": Efeito(_corte_x, 0.7),
    "rotacao": Efeito(_rotacao),
    "sangue": Efeito(_sangue, 0.7),
    "selo": Efeito(_selo, 0.8),
    "demonio": Efeito(_demonio, 1.1),
    "repulsao": Efeito(_repulsao, 0.9),
    "olho": Efeito(_olho, 0.9),
    "dominio": Efeito(_dominio, 1.4),
    "tempo": Efeito(_tempo, 1.2),
    "trovao": Efeito(_trovao, 0.5),
    "clones": Efeito(_clones, 0.9),
    "cura": Efeito(_cura, 0.8),
    "espiral": Efeito(_espiral, 0.9),
    "clarao_negro": Efeito(_clarao_negro, 0.8),
    "presa": Efeito(_presa, 0.7),
    "correntes": Efeito(_correntes, 0.8),
    "esfera": Efeito(_esfera, 1.3),
    "ilusao": Efeito(_ilusao, 1.2),
    "corte_mundo": Efeito(_corte_mundo, 1.3),
    "nada": Efeito(_hesitar, 0.4),
    "fogo": Efeito(_fogo, 0.8),
    "gelo": Efeito(_gelo, 0.8),
    "veneno": Efeito(_veneno, 0.8),
    "vento": Efeito(_vento, 0.7),
    "explosao": Efeito(_explosao, 1.0),
    # fusões e assinaturas novas
    "feixe": Efeito(_feixe, 1.1),
    "raio_na_mao": Efeito(_raio_na_mao, 0.9),
    "punho_gigante": Efeito(_punho_gigante, 1.0),
    "trovao_flamejante": Efeito(_trovao_flamejante, 0.8),
    "vermelho": Efeito(_vermelho, 1.0),
    "espirais": Efeito(_espirais, 1.1),
    "transmutacao": Efeito(_transmutacao, 1.1),
    "roda_dharma": Efeito(_roda_dharma, 1.1),
    "espelho": Efeito(_espelho, 1.0),
}

POR_HABILIDADE = {
    "golpe_basico": "impacto",
    "hesitar": "nada",
    "golpe_direto": "punho",
    "guarda_alta": "guarda",
    "investida": "investida",
    "corte_em_cruz": "corte_x",
    "contra_ataque": "rotacao",
    "lamina_de_sangue": "sangue",
    "marca_da_maldicao": "selo",
    "contrato": "demonio",
    "julgamento": "repulsao",
    "olho_roubado": "olho",
    "santuario": "dominio",
    "instante_suspenso": "tempo",
    "primeiro_trovao": "trovao",
    "clones_de_sombra": "clones",
    "mao_curadora": "cura",
    "espiral_concentrada": "espiral",
    "clarao_negro": "clarao_negro",
    "presa_da_lua": "presa",
    "corrente_do_julgamento": "correntes",
    "esfera_dos_mil": "esfera",
    "lua_ilusoria": "ilusao",
    "corte_do_mundo": "corte_mundo",
    # expansão
    "bola_de_fogo": "fogo",
    "rugido_do_dragao": "fogo",
    "chamas_negras": "fogo",
    "punho_de_magma": "fogo",
    "kaioken": "fogo",
    "grito_de_guerra": "repulsao",
    "onda_solar": "fogo",
    "quarta_marcha": "fogo",
    "deus_do_sol": "fogo",
    "lanca_de_gelo": "gelo",
    "era_do_gelo": "gelo",
    "prisao_de_cristal": "gelo",
    "agulhas_de_veneno": "veneno",
    "enxame": "veneno",
    "nevoa_venenosa": "veneno",
    "golpe_de_vento": "vento",
    "ferida_do_vento": "vento",
    "chute_do_furacao": "vento",
    "folha_cortante": "vento",
    "corte_rapido": "vento",
    "selo_explosivo": "explosao",
    "bomba_relogio": "explosao",
    "arte_explosiva": "explosao",
    "explosao_final": "explosao",
    "chifrada": "punho",
    "chuva_de_chutes": "punho",
    "rasteira": "punho",
    "punho_que_cresce": "punho",
    "punho_armado": "punho",
    "pistola_a_jato": "punho",
    "rajada_de_dempsey": "punho",
    "bazuca": "punho",
    "palma_suave": "punho",
    "ultimo_corte": "corte_x",
    "enma": "corte_x",
    "danca_da_lua_branca": "corte_x",
    "lua_cruzada": "corte_x",
    "lamina_que_ecoa": "corte_x",
    "nove_cabecas": "corte_x",
    "garra_do_tigre": "corte_x",
    "fio_de_aco": "corte_x",
    "corpo_de_ferro": "guarda",
    "parede_dagua": "guarda",
    "muralha_de_terra": "guarda",
    "pele_de_diamante": "guarda",
    "calmaria": "guarda",
    "espelho_sagrado": "guarda",
    "estrela_no_ombro": "guarda",
    "danca_dos_ossos": "rotacao",
    "presa_sobre_presa": "rotacao",
    "respiracao_total": "cura",
    "byakugo": "cura",
    "carne_maldita": "cura",
    "pilula_de_soldado": "cura",
    "olhar_de_nen": "olho",
    "intencao_assassina": "olho",
    "previsao": "olho",
    "olhos_do_futuro": "olho",
    "sexto_sentido": "olho",
    "raio_branco": "trovao",
    "mil_passaros": "trovao",
    "seis_trovoes": "trovao",
    "passo_relampago": "trovao",
    "tiro_de_dedo": "presa",
    "disparo_certeiro": "presa",
    "mira_do_falcao": "presa",
    "onda_de_ki": "espiral",
    "shuriken_espiral": "espiral",
    "dragao_dagua": "espiral",
    "vazio_purpura": "esfera",
    "lua_sem_luz": "corte_mundo",
    "sombra_que_prende": "correntes",
    "gaiola_de_fios": "correntes",
    "grilhao": "correntes",
    "fio_invisivel": "correntes",
    "calma_absoluta": "ilusao",
    "possessao": "ilusao",
    "bomba_de_fumaca": "ilusao",
    "luz_cegante": "clarao_negro",
    "golpe_de_misericordia": "clarao_negro",
    "vontade_do_rei": "repulsao",
    "pressao_gravitacional": "repulsao",
    "mao_que_apaga": "repulsao",
    "dente_de_tubarao": "sangue",
    "mordida": "sangue",
    "chuva_de_sangue": "sangue",
    "espinhos_da_rosa": "sangue",
    "banquete": "demonio",
    "mascarados": "demonio",
    "sangue_de_ymir": "demonio",
    "lotus_primaria": "investida",
    "martelo_de_cinco_toneladas": "investida",
    "portao_da_morte": "investida",
    "marionetes": "clones",
    "sessenta_e_quatro_palmas": "clones",
    "substituicao": "clones",
    "guerreiro_espectral": "dominio",
    "ceu_acelerado": "tempo",
    "fuga_dimensional": "tempo",
    # Leva 3
    "zoltraak": "presa",
    "disco_cortante": "presa",
    "lanca_do_coracao": "presa",
    "chacal": "presa",
    "canhao_do_braco": "explosao",
    "suor_explosivo": "explosao",
    "nuvem_de_trovao": "trovao",
    "espada_da_vitoria": "corte_mundo",
    "perna_em_brasa": "fogo",
    "estalo_de_chamas": "fogo",
    "metade_fria": "gelo",
    "olhar_de_pedra": "gelo",
    "lotus_de_gelo": "gelo",
    "danca_do_inseto": "veneno",
    "lamina_que_paralisa": "veneno",
    "facas_de_arremesso": "corte_x",
    "manobra_3d": "corte_x",
    "explosao_estelar": "corte_x",
    "espada_sem_magia": "corte_x",
    "motosserra": "sangue",
    "baionetas_bentas": "corte_x",
    "respingo_esmeralda": "clones",
    "mil_clones": "clones",
    "sementes_de_combate": "clones",
    "coruja_trovao": "trovao",
    "caes_divinos": "presa",
    "sapo_chefe": "demonio",
    "levantem_se": "demonio",
    "o_indomavel": "demonio",
    "ritual_de_sangue": "sangue",
    "caixao_negro": "dominio",
    "trevas": "ilusao",
    "olhar_que_apaga": "olho",
    "voz_amaldicoada": "repulsao",
    "chiclete_elastico": "correntes",
    "apagar_o_tempo": "tempo",
    "pedra_carregada": "punho",
    "soco_que_quebra": "punho",
    "respiracao_do_sol": "espiral",
    "defesa_magica": "guarda",
    "parede_transmutada": "guarda",
    "sete_petalas": "guarda",
    "sal_purificador": "cura",
    "arraia_curandeira": "cura",
    "diamante_que_conserta": "cura",
    "caixao_da_montanha": "dominio",
    "mundo_de_laminas": "dominio",
    "dedo_que_aponta": "presa",
    # transformações e técnicas de Dom/Linhagem da leva
    "energia_natural": "dominio",
    "segunda_marcha": "fogo",
    "corpo_inteiro": "trovao",
    "ponto_monstro": "repulsao",
    "cabelo_dourado": "repulsao",
    "juba_dourada": "repulsao",
    "lamina_negra_liberada": "corte_x",
    "velocidade_divina": "trovao",
    "mordida_na_mao": "demonio",
    "forma_do_demonio_negro": "demonio",
    "tempo_do_imperador": "correntes",
    "preco_do_futuro": "repulsao",
    "transbordar": "repulsao",
    "berserker": "demonio",
    "maos_invisiveis": "correntes",
    "exercito_de_um": "clones",
    "balanca_da_obediencia": "ilusao",
    "luas_crescentes": "corte_x",
    # técnicas-assinatura dos chefes
    "mil_laminas": "corte_x",
    "guerreiro_esqueleto": "rotacao",
    "estrela_que_prende": "esfera",
    "desvio_dimensional": "tempo",
    "lua_sem_fim": "presa",
    "disparo_espiritual": "espiral",
    "general_da_roda": "roda_dharma",
    "flor_no_espelho": "espelho",
    # as técnicas que só nascem de fusão (data/fusoes.json)
    "corta_raio": "raio_na_mao",
    "punho_colossal": "punho_gigante",
    "onda_carmesim": "feixe",
    "trovao_em_chamas": "trovao_flamejante",
    "repulsao_escarlate": "vermelho",
    "tempestade_de_espirais": "espirais",
    "relampago_ligeiro": "trovao",
    "palmas_da_verdade": "transmutacao",
}
TELA_CHEIA = {"dominio", "tempo", "ilusao", "corte_mundo", "demonio", "repulsao"}


def efeito_de(tecnica_id: str, tipo: str = "ataque") -> str:
    """O efeito de uma técnica (as sem homenagem própria caem no do tipo)."""
    if tecnica_id in POR_HABILIDADE:
        return POR_HABILIDADE[tecnica_id]
    return {"defesa": "guarda", "maldita": "selo", "modo": "selo"}.get(tipo, "impacto")


def duracao(nome: str) -> float:
    return EFEITOS[nome].duracao


def desenhar(
    r: IRenderer, nome: str, ator: Ponto, alvo: Ponto, k: float, relogio: float, forte=False
) -> None:
    if 0 <= k < 1:
        EFEITOS[nome].desenho(r, ator, alvo, k, relogio, forte)


# ----------------------------------------------------------------------- auras do Despertar

AURAS = {  # id do Despertar -> (cor, estilo)
    "retribuicao": (SANGUE_VIVO, "espinhos"),
    "tomar_o_destino": (OURO, "correntes"),
    "forma_desperta": (AMARELO, "chamas"),
    "renascer_das_cinzas": ((255, 150, 70, 255), "asas"),
    "liberacao_final": (SANGUE_VIVO, "pressao"),
    "instinto_puro": ((210, 220, 240, 255), "brilho"),
    "modo_eremita": ((240, 150, 60, 255), "aneis"),
    "marca_do_cacador": (SANGUE_VIVO, "marca"),
    "fera_interior": ((255, 140, 40, 255), "chamas"),
    "vazio_infinito": ((200, 225, 255, 255), "aneis"),
    "dragao_negro": ((120, 60, 200, 255), "pressao"),
    "retorno_pela_morte": ((160, 120, 200, 255), "correntes"),
    "sangue_explosivo": (SANGUE_VIVO, "chamas"),
    "santuario_malevolo": (SANGUE_VIVO, "pressao"),
    "vontade_herdada": (OURO, "brilho"),
    "izanami": (ROXO, "aneis"),
    "soco_serio": (AMARELO, "pressao"),
    "troca_de_corpos": (ROXO, "correntes"),
    "reflexo_vetorial": (BRANCO, "aneis"),
    "mordida_do_po": ((255, 140, 180, 255), "espinhos"),
    "mil_maos": (OURO, "asas"),
    "noite_sem_fim": (SANGUE_VIVO, "asas"),
    "rajada_ora": ((150, 120, 230, 255), "chamas"),
    "selo_de_cinco_partes": (ROXO, "correntes"),
    "zenkai": (AMARELO, "chamas"),
    "susanoo_completo": (ROXO, "aneis"),
    "olho_que_preve": (BRANCO, "brilho"),
    "relampago_do_tigre": (AZUL_CHAKRA, "brilho"),
    "selo_do_ceu": (PRETO, "marca"),
    "fenix_negra": (PRETO, "asas"),
    "dragao_de_trovao": (AZUL_CHAKRA, "pressao"),
    "uniao": (OURO, "aneis"),
    "selo_do_ceifador": (BRANCO, "correntes"),
    "deus_saiyajin": (SANGUE_VIVO, "chamas"),
    "rei_dos_demonios": (SANGUE_VIVO, "espinhos"),
    "asas_da_liberdade": (BRANCO, "asas"),
    "lacos": ((255, 150, 70, 255), "aneis"),
    "rei_dos_piratas": (OURO, "pressao"),
    "espada_do_fim": ((255, 120, 40, 255), "chamas"),
    "tempo_parado": (OURO, "correntes"),
    "gula_sem_fim": (PRETO, "espinhos"),
    "despertar_ackerman": (SANGUE_VIVO, "marca"),
    "inferno_negro": (PRETO, "chamas"),
    "o_que_o_heroi_faria": ((160, 200, 255, 255), "brilho"),
    "lei_das_fadas": (OURO, "brilho"),
}

AURAS_MODO = {  # transformações: a aura fica enquanto a forma dura
    "kaioken": (SANGUE_VIVO, "chamas"),
    "deus_do_sol": (BRANCO, "brilho"),
    "quarta_marcha": ((220, 80, 80, 255), "pressao"),
    "berserker": (PRETO, "espinhos"),
    "energia_natural": ((240, 150, 60, 255), "aneis"),
    "segunda_marcha": ((255, 160, 170, 255), "chamas"),
    "corpo_inteiro": ((120, 230, 120, 255), "brilho"),
    "ponto_monstro": ((255, 140, 40, 255), "pressao"),
    "cabelo_dourado": (AMARELO, "chamas"),
    "juba_dourada": (AMARELO, "chamas"),
    "lamina_negra_liberada": (PRETO, "pressao"),
    "velocidade_divina": (AZUL_CHAKRA, "brilho"),
    "mordida_na_mao": ((210, 120, 80, 255), "pressao"),
    "caixao_da_montanha": ((255, 120, 40, 255), "aneis"),
    "forma_do_demonio_negro": (PRETO, "chamas"),
    "tempo_do_imperador": (SANGUE_VIVO, "brilho"),
    "preco_do_futuro": (AMARELO, "pressao"),
    "transbordar": ((200, 120, 255, 255), "aneis"),
    "mundo_de_laminas": ((220, 200, 160, 255), "aneis"),
}


def aura(r: IRenderer, despertar_id: str, x: float, y: float, k: float, relogio: float) -> None:
    """A aura de quem desperta, em volta de (x, y) — o centro do corpo."""
    cor, estilo = AURAS.get(despertar_id) or AURAS_MODO.get(despertar_id) or (OURO, "chamas")
    forca = _sino(min(1.0, k * 1.2))
    t = relogio
    if estilo in ("chamas", "brilho"):
        for i in range(18):
            ang = -math.pi / 2 + (i - 9) * 0.17
            alto = 70 + 40 * (0.5 + 0.5 * math.sin(t * 9 + i * 1.7))
            base = (x + math.cos(ang) * 40, y + 40)
            topo = (x + math.cos(ang) * 60, y - alto)
            r.draw_ui_line(
                base[0],
                base[1],
                topo[0],
                topo[1],
                alpha(cor, 130 * forca),
                4 if estilo == "chamas" else 2,
            )
    elif estilo == "espinhos":
        for i in range(16):
            ang = i * 2 * math.pi / 16 + t
            comp = 60 + 40 * math.sin(t * 6 + i) ** 2
            r.draw_ui_line(
                x, y, x + math.cos(ang) * comp, y + math.sin(ang) * comp, alpha(cor, 170 * forca), 3
            )
    elif estilo == "correntes":
        for i in range(4):
            ang = i * math.pi / 2 + t * 0.6
            _corrente(
                r,
                (x, y),
                (x + math.cos(ang) * 140, y + math.sin(ang) * 140),
                alpha(cor, 200 * forca),
            )
    elif estilo == "asas":
        for lado in (-1, 1):
            for i in range(6):
                r.draw_ui_arc(
                    x + lado * (30 + i * 12),
                    y - 20,
                    50 + i * 10,
                    math.radians(90 - lado * 80),
                    math.radians(90 + lado * 10 - lado * 80 + 120 * lado),
                    alpha(cor, 160 * forca),
                    3,
                )
    elif estilo == "pressao":
        for i in range(5):
            raio = 40 + ((t * 120 + i * 40) % 200)
            r.draw_ui_circle(x, y, raio, alpha(PRETO, 160 * forca), 6)
            r.draw_ui_circle(x, y, raio + 3, alpha(cor, 120 * forca), 2)
    elif estilo == "aneis":
        for i in range(3):
            r.draw_ui_circle(
                x, y - 60, 20 + i * 14 + 4 * math.sin(t * 4 + i), alpha(cor, 160 * forca), 2
            )
    elif estilo == "marca":
        for i in range(5):
            ang = -math.pi / 2 + (i - 2) * 0.5
            r.draw_ui_arc(
                x + math.cos(ang) * 30,
                y - 80 + math.sin(ang) * 10,
                18,
                ang,
                ang + 2.4,
                alpha(cor, 220 * forca),
                4,
            )


# ----------------------------------------------------------------------- cinema: transição, fim

DURACAO_REVELAR = 0.5
_MANCHAS = [  # (x, y, raio): manchas que cobrem a tela inteira no começo
    (x, y, 150 + 40 * math.sin(x * 0.7 + y))
    for x in range(-40, LARGURA + 120, 170)
    for y in range(-40, ALTURA + 120, 170)
]


def revelar(r: IRenderer, t: float) -> None:
    """A tela nasce coberta de tinta e as manchas se recolhem (t: tempo desde a entrada)."""
    k = t / DURACAO_REVELAR
    if k >= 1:
        return
    encolhe = (1 - k) ** 2
    for i, (x, y, raio) in enumerate(_MANCHAS):
        atraso = 0.6 + 0.4 * math.sin(i * 1.7) ** 2  # cada mancha recolhe num ritmo
        tam = raio * min(1.0, encolhe / atraso)
        if tam < 2:
            continue
        r.draw_ui_circle(x, y, tam, (10, 9, 8, 255))
        for j in range(5):  # respingos em volta: a borda irregular da tinta
            a = i * 1.3 + j * 1.256
            d = tam * (0.85 + 0.25 * math.sin(i + j * 2.1))
            r.draw_ui_circle(x + math.cos(a) * d, y + math.sin(a) * d, tam * 0.32, (10, 9, 8, 255))


def correntes_fechando(r: IRenderer, x: float, y: float, k: float) -> None:
    """A derrota: correntes entram dos dois lados e se fecham sobre quem caiu."""
    fecha = 1 - (1 - min(1.0, k)) ** 3
    for dy in (-60, -20, 20):
        for lado in (-1, 1):
            inicio = (x + lado * 210, y + dy + lado * 24)  # perto de quem caiu, longe dos selos
            fim = _lerp(inicio, (x, y + dy), fecha)
            _corrente(r, inicio, fim, alpha((150, 140, 130, 255), 230))
        if fecha >= 0.98:
            r.draw_ui_circle(x, y + dy, 9, SANGUE_VIVO, 3)


def dissolver(r: IRenderer, x: float, y: float, k: float, cor: Cor, escala: float = 1.0) -> None:
    """A vitória: o rival se desfaz em gotas de tinta que sobem e se espalham.
    `escala` < 1 para quem é menor (uma invocação que vai embora)."""
    n = 46 if escala >= 0.8 else 24
    for i in range(n):
        s = i * 2.39
        ox = math.sin(s * 3.1) * 46 * escala
        oy = (-20 - (math.sin(s * 1.7) * 0.5 + 0.5) * 150) * escala
        sobe = k * (60 + 90 * (math.sin(s * 5.3) ** 2)) * escala
        px = x + ox * (1 + k * 1.5) + math.sin(s) * 40 * k * escala
        py = y + oy - sobe
        clara = mistura(cor, TINTA, 0.55)  # a tinta do rival, clara o bastante para o fundo escuro
        raio = (4.5 * (1 - k) + 1.5) * max(0.6, escala)
        r.draw_ui_circle(px, py, raio, alpha(clara, 240 * (1 - k)))


def mancha_de_tinta(r: IRenderer, x: float, y: float, k: float, escala: float = 1.0) -> None:
    """Uma invocação chega: a tinta se esparrama no chão e se recolhe (k: 0 → 1)."""
    if not 0 <= k < 1:
        return
    abre = 1 - (1 - min(1.0, k / 0.35)) ** 3
    some = 1 - max(0.0, k - 0.45) / 0.55
    raio = (16 + 46 * abre) * escala * (0.4 + 0.6 * some)
    cor = alpha(PRETO, 235 * some)
    r.draw_ui_polygon(
        [
            (
                x + math.cos(a) * raio * (0.85 + 0.2 * math.sin(a * 3 + 1.3)),
                y + math.sin(a) * raio * 0.32,
            )
            for a in (i * math.pi / 9 for i in range(18))
        ],
        cor,
    )
    for i in range(8):  # respingos que saltam e caem
        a = i * 0.785 + 0.4
        d = raio * (1.15 + 0.35 * math.sin(i * 2.1))
        alto = math.sin(min(1.0, k / 0.6) * math.pi) * 26 * escala * (0.5 + (i % 3) * 0.3)
        r.draw_ui_circle(
            x + math.cos(a) * d, y + math.sin(a) * d * 0.32 - alto, (2 + i % 3) * escala, cor
        )
    if k < 0.5:  # a coluna de tinta de onde ela sobe
        alto = 120 * escala * math.sin(k / 0.5 * math.pi)
        r.draw_ui_polygon(
            [
                (x - 10 * escala, y),
                (x + 10 * escala, y),
                (x + 4 * escala, y - alto),
                (x - 4 * escala, y - alto),
            ],
            alpha(PRETO, 200 * some),
        )


def nuvem(r: IRenderer, x: float, y: float, k: float, escala: float = 1.0) -> None:
    """O clone desfeito: uma nuvem de fumaça branca que estoura e se espalha (poof)."""
    if not 0 <= k < 1:
        return
    abre = 1 - (1 - k) ** 2
    for i in range(9):
        a = i * 0.698 + 0.3
        d = (8 + 34 * abre) * escala * (0.7 + 0.3 * math.sin(i * 1.7))
        raio = (10 + 18 * abre) * escala * (0.8 + 0.25 * math.cos(i * 2.3))
        cinza = mistura(BRANCO, TINTA, 0.35 + 0.1 * (i % 3))
        r.draw_ui_circle(
            x + math.cos(a) * d,
            y + math.sin(a) * d * 0.7 - 14 * abre * escala,
            raio,
            alpha(cinza, 170 * (1 - k) ** 1.5),
        )
    if k < 0.25:
        r.draw_ui_circle(x, y, 26 * escala * (k / 0.25), alpha(BRANCO, 200 * (1 - k / 0.25)))


def clarao_de_golpe(r: IRenderer, x: float, y: float, k: float, forca: float = 1.0) -> None:
    """O instante do golpe forte: um estouro branco e riscos que saem do alvo."""
    if not 0 <= k < 1:
        return
    a = 1 - k
    r.draw_ui_circle(x, y, (30 + 50 * k) * forca, alpha(BRANCO, 150 * a**2))
    r.draw_ui_circle(x, y, (44 + 70 * k) * forca, alpha(BRANCO, 220 * a), max(1, round(4 * a)))
    for i in range(12):
        ang = i * math.pi / 6 + 0.2
        d0 = (24 + 40 * k) * forca
        d1 = d0 + (40 + 30 * math.sin(i * 1.9)) * forca * a
        r.draw_ui_line(
            x + math.cos(ang) * d0,
            y + math.sin(ang) * d0,
            x + math.cos(ang) * d1,
            y + math.sin(ang) * d1,
            alpha(BRANCO, 230 * a),
            3,
        )


def mordida(r: IRenderer, x: float, y: float, k: float, cor: Cor, escala: float = 1.0) -> None:
    """O golpe de uma invocação no alvo: três riscos na cor dela e um estouro."""
    if not 0 <= k < 1:
        return
    a = 1 - k
    abre = 1 - (1 - k) ** 2
    for i in (-1, 0, 1):
        dx = i * 12 * escala
        r.draw_ui_line(
            x + dx - 22 * escala * abre,
            y - 26 * escala * abre,
            x + dx + 22 * escala * abre,
            y + 26 * escala * abre,
            alpha(cor, 240 * a),
            max(1, round(4 * escala)),
        )
    r.draw_ui_circle(x, y, (12 + 30 * abre) * escala, alpha(cor, 170 * a), 3)


# ----------------------------------------------------------------------- clima sombrio


def vinheta(r: IRenderer, forca: float = 1.0) -> None:
    """Bordas que afundam no escuro: o olho vai para o centro."""
    passo = 12
    for i in range(14):
        a = (14 - i) * 7 * forca
        cor = alpha(PRETO, a)
        d = i * passo
        r.draw_ui_rect(0, d, LARGURA, passo, cor)
        r.draw_ui_rect(0, ALTURA - d - passo, LARGURA, passo, cor)
        r.draw_ui_rect(d, 0, passo, ALTURA, cor)
        r.draw_ui_rect(LARGURA - d - passo, 0, passo, ALTURA, cor)


def grao(r: IRenderer, relogio: float, n: int = 220) -> None:
    """Grão de papel e tinta: pontos que mudam a cada quadro de filme (12 por segundo)."""
    quadro = math.floor(relogio * 12)
    for i in range(n):
        s = i * 12.9898 + quadro * 78.233
        x = (math.sin(s) * 43758.5453) % 1 * LARGURA
        y = (math.sin(s * 1.37) * 24634.6345) % 1 * ALTURA
        r.draw_ui_rect(x, y, 2, 2, alpha(PRETO if i % 3 else TINTA, 26))


def mancha_de_sangue(r: IRenderer, x: float, y: float, tam: float, semente: float) -> None:
    """Uma mancha de tinta-sangue no chão (fica até o fim da luta)."""
    cor = (70, 6, 8, 170)
    r.draw_ui_polygon(
        [
            (
                x + math.cos(a) * tam * (0.6 + 0.4 * math.sin(semente + a * 3)),
                y + math.sin(a) * tam * 0.35,
            )
            for a in (k * math.pi / 8 for k in range(16))
        ],
        cor,
    )
    for k in range(5):  # respingos
        a = semente + k * 1.3
        d = tam * (1.1 + 0.5 * math.sin(semente * 2 + k))
        r.draw_ui_circle(x + math.cos(a) * d, y + math.sin(a) * d * 0.35, 2 + (k % 3), cor)

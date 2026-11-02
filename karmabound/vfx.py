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
}
TELA_CHEIA = {"dominio", "tempo", "ilusao", "corte_mundo", "demonio", "repulsao"}


def efeito_de(tecnica_id: str, tipo: str = "ataque") -> str:
    """O efeito de uma técnica (as sem homenagem própria caem no do tipo)."""
    if tecnica_id in POR_HABILIDADE:
        return POR_HABILIDADE[tecnica_id]
    return {"defesa": "guarda", "maldita": "selo"}.get(tipo, "impacto")


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
}


def aura(r: IRenderer, despertar_id: str, x: float, y: float, k: float, relogio: float) -> None:
    """A aura de quem desperta, em volta de (x, y) — o centro do corpo."""
    cor, estilo = AURAS.get(despertar_id, (OURO, "chamas"))
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

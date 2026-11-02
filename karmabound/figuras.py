"""Lutadores de tinta: um esqueleto com articulações, vestido por estilo.

A figura é montada de juntas (quadril, peito, ombros, cotovelos, mãos, joelhos)
a partir de uma **pose**; as poses se misturam (parado → guarda → ataque → golpe
recebido), e o corpo respira. Cada parte é um polígono em pincel: o corpo sólido
e duas passadas deslocadas com pouca opacidade, que dão a borda irregular.

Estilos (os rivais variam; você é sempre o espadachim, visto de costas):
    espadachim  kimono, hakama e katana
    monge       manto longo, cajado com argolas e rosário
    ninja       cachecol ao vento, bandana e duas lâminas curtas, mais agachado
    oni         chifres, juba, ombros largos e o kanabō
    hollow      máscara de osso, buraco no peito, garras e o manto em farrapos
    tita        enorme, sem arma, músculos à mostra e vapor saindo do corpo
    colosso     o chefe: quatro braços, chifres em coroa, capa e uma lâmina enorme
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ouroboros.interfaces.renderer import IRenderer

from karmabound.visual import Cor, alpha, mistura

ESTILOS = ("espadachim", "monge", "ninja", "oni", "hollow", "tita")
BRANCO = (255, 255, 255, 255)
OSSO = (226, 220, 204, 255)
OLHO_RUBRO = (230, 40, 40, 255)

Ponto = tuple[float, float]


@dataclass(frozen=True)
class Pose:
    """Ângulos em graus na tela (0 = direita, 90 = para baixo)."""

    inclina: float = 0.0  # o tronco tomba para o lado
    agacha: float = 0.15  # 0 em pé, 1 bem baixo
    ombro_e: float = 100
    cotovelo_e: float = 110
    ombro_d: float = 70
    cotovelo_d: float = 40
    arma: float = -60
    cabeca: float = 0.0


POSES = {
    "parado": Pose(),
    "guarda": Pose(agacha=0.35, ombro_e=60, cotovelo_e=20, ombro_d=30, cotovelo_d=-40, arma=-100),
    "ataque": Pose(
        inclina=10, agacha=0.25, ombro_e=135, cotovelo_e=160, ombro_d=-40, cotovelo_d=-50, arma=-25
    ),
    "dano": Pose(
        inclina=-12,
        agacha=0.45,
        ombro_e=150,
        cotovelo_e=125,
        ombro_d=20,
        cotovelo_d=80,
        arma=-150,
        cabeca=-12,
    ),
}


def _mistura_pose(a: Pose, b: Pose, k: float) -> Pose:
    k = max(0.0, min(1.0, k))
    return Pose(*(x + (y - x) * k for x, y in zip(vars(a).values(), vars(b).values(), strict=True)))


def _polar(p: Ponto, ang: float, comp: float) -> Ponto:
    a = math.radians(ang)
    return p[0] + math.cos(a) * comp, p[1] + math.sin(a) * comp


def _rot(v: Ponto, ang: float) -> Ponto:
    a = math.radians(ang)
    return v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a)


def _soma(p: Ponto, v: Ponto) -> Ponto:
    return p[0] + v[0], p[1] + v[1]


@dataclass(frozen=True)
class _Corpo:
    """As juntas, em unidades (pés em (0, 0), y cresce para baixo)."""

    quadril: Ponto
    peito: Ponto
    cabeca: Ponto
    ombro_e: Ponto
    ombro_d: Ponto
    cotovelo_e: Ponto
    cotovelo_d: Ponto
    mao_e: Ponto
    mao_d: Ponto
    joelho_e: Ponto
    joelho_d: Ponto
    pe_e: Ponto
    pe_d: Ponto


def _esqueleto(p: Pose, largo: float, tempo: float, altura: float = 1.0) -> _Corpo:
    respira = math.sin(tempo * 2.1) * 1.4
    quadril = (0.0, -50 * altura + p.agacha * 10)
    peito = _soma(quadril, _rot((0, -44 * altura + respira), p.inclina))
    cabeca = _soma(peito, _rot((0, -20 * altura), p.inclina + p.cabeca))
    meio = 24 * largo
    ombro_e = _soma(peito, _rot((-meio, 2), p.inclina))
    ombro_d = _soma(peito, _rot((meio, 2), p.inclina))
    braco = 22 * altura
    cotovelo_e = _polar(ombro_e, p.ombro_e, braco)
    cotovelo_d = _polar(ombro_d, p.ombro_d, braco)
    mao_e = _polar(cotovelo_e, p.cotovelo_e, braco * 0.92)
    mao_d = _polar(cotovelo_d, p.cotovelo_d, braco * 0.92)
    abre = 16 + 10 * p.agacha
    pe_e, pe_d = (-abre * largo, 0.0), (abre * largo, 0.0)
    dobra = 6 + 10 * p.agacha  # joelhos abrem para fora quando agacha
    joelho_e = ((quadril[0] - 9 + pe_e[0]) / 2 - dobra, (quadril[1] + 0) / 2)
    joelho_d = ((quadril[0] + 9 + pe_d[0]) / 2 + dobra, (quadril[1] + 0) / 2)
    return _Corpo(
        quadril,
        peito,
        cabeca,
        ombro_e,
        ombro_d,
        cotovelo_e,
        cotovelo_d,
        mao_e,
        mao_d,
        joelho_e,
        joelho_d,
        pe_e,
        pe_d,
    )


class _Pincel:
    """Desenha em unidades, com a passada de pincel por trás do sólido."""

    def __init__(self, r: IRenderer, x: float, y: float, e: float, contorno: Cor) -> None:
        self.r, self.x, self.y, self.e, self.contorno = r, x, y, e, contorno

    def tela(self, p: Ponto) -> Ponto:
        return self.x + p[0] * self.e, self.y + p[1] * self.e

    def poligono(self, pontos, cor: Cor, borda: bool = True) -> None:
        if borda:
            for dx, dy, a in ((-1.6, 0.8, 70), (1.4, -1.0, 60)):
                self.r.draw_ui_polygon(
                    [(self.x + px * self.e + dx, self.y + py * self.e + dy) for px, py in pontos],
                    alpha(self.contorno, a * cor[3] / 255),
                )
        self.r.draw_ui_polygon([self.tela(p) for p in pontos], cor)

    def membro(self, a: Ponto, b: Ponto, w0: float, w1: float, cor: Cor, borda=True) -> None:
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n, dx / n
        self.poligono(
            [
                (a[0] + nx * w0, a[1] + ny * w0),
                (b[0] + nx * w1, b[1] + ny * w1),
                (b[0] - nx * w1, b[1] - ny * w1),
                (a[0] - nx * w0, a[1] - ny * w0),
            ],
            cor,
            borda,
        )

    def circulo(self, c: Ponto, raio: float, cor: Cor, borda=True, largura: int = 0) -> None:
        cx, cy = self.tela(c)
        if borda:
            self.r.draw_ui_circle(
                cx - 1.6, cy + 0.8, (raio + 1.5) * self.e, alpha(self.contorno, 70 * cor[3] / 255)
            )
        self.r.draw_ui_circle(cx, cy, raio * self.e, cor, largura)

    def linha(self, a: Ponto, b: Ponto, cor: Cor, largura: float) -> None:
        (x0, y0), (x1, y1) = self.tela(a), self.tela(b)
        self.r.draw_ui_line(x0, y0, x1, y1, cor, max(1, round(largura * self.e)))


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
    ataque: float = 0.0,
    dano: float = 0.0,
    costas: bool = False,
) -> None:
    """Desenha a figura com os pés em (x, y).

    `guarda`, `ataque` e `dano` (0–1) misturam as poses; `clarao` tinge a figura com
    `clarao_cor`; `tempo` anima respiração, tecido e cabelo; `costas`: visto de trás
    (sem rosto), como o jogador.
    """
    corpo = mistura(cor, clarao_cor, clarao) if clarao > 0 else cor
    escuro = mistura(corpo, (0, 0, 0, 255), 0.35)
    claro = mistura(corpo, BRANCO, 0.12)
    largo = {"oni": 1.35, "colosso": 1.45, "tita": 1.6, "hollow": 1.05}.get(estilo, 1.0)
    altura = {"tita": 1.08, "ninja": 0.96}.get(estilo, 1.0)

    pose = POSES["parado"]
    if estilo == "ninja":
        pose = _mistura_pose(pose, POSES["guarda"], 0.4)
    pose = _mistura_pose(pose, POSES["guarda"], guarda)
    pose = _mistura_pose(pose, POSES["ataque"], ataque)
    pose = _mistura_pose(pose, POSES["dano"], dano)
    j = _esqueleto(pose, largo, tempo, altura)
    p = _Pincel(r, x, y, escala, contorno)

    # sombra no chão
    s = 46 * largo
    r.draw_ui_polygon(
        [
            (x - s * escala, y + 2 * escala),
            (x + s * escala, y + 2 * escala),
            (x + s * 0.65 * escala, y + 9 * escala),
            (x - s * 0.75 * escala, y + 8 * escala),
        ],
        alpha(contorno, 42 * corpo[3] / 255),
    )

    # --- atrás do corpo: capa, cachecol, manto em farrapos, vapor
    if estilo == "colosso":
        onda = math.sin(tempo * 1.7) * 5
        a, b = j.ombro_e, j.ombro_d
        p.poligono(
            [_soma(a, (-6, -4)), _soma(b, (6, -4)), (52 + onda, 4), (-52 + onda * 0.6, 4)],
            escuro,
            False,
        )
    if estilo == "ninja":
        for k in range(2):
            pts = [
                _soma(
                    j.cabeca,
                    (-4 - i * 9, 10 + i * 2 + k * 5 + math.sin(tempo * 6 + i * 0.8 + k) * (2 + i)),
                )
                for i in range(7)
            ]
            for a, b in zip(pts, pts[1:], strict=False):
                p.linha(a, b, claro, 5)
    if estilo == "tita":
        for i in range(6):  # o vapor do corpo de titã
            fase = (tempo * 0.6 + i * 0.37) % 1.0
            base = j.ombro_e if i % 2 else j.ombro_d
            c = _soma(base, (math.sin(i * 2.1) * 10, -fase * 60))
            p.circulo(
                c, 5 + 9 * fase, alpha(BRANCO, 120 * (1 - fase) * corpo[3] / 255), borda=False
            )

    # --- pernas e roupa de baixo
    if estilo in ("espadachim", "ninja"):
        larg = 0.8 if estilo == "ninja" else 1.0
        h = j.quadril
        hem = math.sin(tempo * 1.4) * 2
        p.poligono(
            [
                (h[0] - 16 * larg, h[1] - 4),
                (h[0] + 16 * larg, h[1] - 4),
                (j.pe_d[0] + 12 * larg + hem, 0),
                (j.pe_d[0] - 6, 0),
                (h[0] + 1, h[1] + 24),
                (j.pe_e[0] + 6, 0),
                (j.pe_e[0] - 12 * larg + hem, 0),
            ],
            corpo,
        )
        for sx in (-1, 1):  # dobras do hakama
            p.linha((h[0] + sx * 6, h[1] + 4), (sx * 14 * larg + hem, -2), alpha(escuro, 160), 1.6)
    elif estilo in ("monge", "hollow"):
        h = j.quadril
        bainha = []
        for i in range(9):  # o manto (no hollow, em farrapos)
            t = i / 8
            xx = -30 * largo + 60 * largo * t
            yy = 0 if estilo == "monge" else -6 * (i % 2) + math.sin(tempo * 2 + i) * 2
            bainha.append((xx, yy))
        p.poligono(
            [(h[0] - 20 * largo, h[1] - 6), (h[0] + 20 * largo, h[1] - 6), *reversed(bainha)], corpo
        )
        if estilo == "monge":
            for sx in (-1, 0, 1):
                p.linha((sx * 8, h[1] + 6), (sx * 18, -3), alpha(escuro, 150), 1.4)
    else:  # oni, tita, colosso: pernas à mostra
        for quadril_x, joelho, pe in ((-9, j.joelho_e, j.pe_e), (9, j.joelho_d, j.pe_d)):
            q = (j.quadril[0] + quadril_x * largo, j.quadril[1])
            p.membro(q, joelho, 8 * largo, 7 * largo, corpo)
            p.membro(joelho, pe, 7 * largo, 5 * largo, corpo)
        tanga = [
            (j.quadril[0] - 18 * largo, j.quadril[1] - 6),
            (j.quadril[0] + 18 * largo, j.quadril[1] - 6),
            (j.quadril[0] + 10 * largo, j.quadril[1] + 16),
            (j.quadril[0] - 10 * largo, j.quadril[1] + 16),
        ]
        p.poligono(tanga, escuro)

    # --- tronco
    meio = 24 * largo
    q = j.quadril
    tronco = [
        _soma(j.ombro_e, (-3, -3)),
        _soma(j.ombro_d, (3, -3)),
        (q[0] + meio * 0.78, q[1] - 2),
        (q[0] - meio * 0.78, q[1] - 2),
    ]
    p.poligono(tronco, corpo)
    if estilo in ("espadachim", "monge", "ninja"):  # a gola do kimono
        gola = alpha(escuro, 200)
        p.linha(_soma(j.peito, (-10 * largo, -2)), _soma(j.peito, (4, 22)), gola, 2.2)
        p.linha(_soma(j.peito, (10 * largo, -2)), _soma(j.peito, (-2, 18)), gola, 2.2)
    if estilo in ("oni", "tita", "colosso"):  # músculos: o peito e o abdome em pinceladas
        for dy in (6, 18, 28):
            p.linha(
                _soma(j.peito, (-8 * largo, dy)),
                _soma(j.peito, (8 * largo, dy)),
                alpha(escuro, 120),
                1.6,
            )
        p.linha(_soma(j.peito, (0, 2)), _soma(j.peito, (0, 34)), alpha(escuro, 120), 1.6)
    if estilo == "hollow":  # o buraco no peito
        p.circulo(_soma(j.peito, (0, 12)), 7, (6, 5, 5, corpo[3]), borda=False)
    if estilo != "monge":  # a faixa na cintura, com o nó balançando
        faixa = alpha(mistura(corpo, contorno, 0.35), corpo[3])
        p.membro((q[0] - meio * 0.8, q[1] - 6), (q[0] + meio * 0.8, q[1] - 6), 4, 4, faixa, False)
        balanco = math.sin(tempo * 2.4) * 3
        p.linha((q[0] + 4, q[1] - 4), (q[0] + 8 + balanco, q[1] + 14), faixa, 3)
        p.linha((q[0] + 7, q[1] - 4), (q[0] + 14 + balanco, q[1] + 10), faixa, 2.5)
    if estilo == "monge":  # o rosário
        for i in range(9):
            a = math.pi * (0.15 + 0.7 * i / 8)
            p.circulo(
                _soma(j.peito, (math.cos(a) * 15, math.sin(a) * 18 - 2)), 2.6, contorno, borda=False
            )

    # --- braços (o segundo par do colosso sai da cintura)
    grosso = {"tita": 1.5, "oni": 1.25, "colosso": 1.3}.get(estilo, 1.0)
    mangas = estilo in ("espadachim", "monge")
    for ombro, cotovelo, mao in (
        (j.ombro_e, j.cotovelo_e, j.mao_e),
        (j.ombro_d, j.cotovelo_d, j.mao_d),
    ):
        if mangas:  # a manga larga do kimono pende do braço
            pende = 9 + math.sin(tempo * 1.8 + ombro[0]) * 1.5
            p.poligono(
                [
                    _soma(ombro, (0, -5)),
                    _soma(cotovelo, (6, 2)),
                    _soma(cotovelo, (2, pende + 6)),
                    _soma(ombro, (-2, 8)),
                ],
                corpo,
            )
        p.membro(ombro, cotovelo, 7 * grosso, 6 * grosso, corpo)
        p.membro(cotovelo, mao, 6 * grosso, 4.5 * grosso, claro if mangas else corpo)
        p.circulo(mao, 4.5 * grosso, claro if mangas else corpo, borda=False)
        if estilo == "hollow":  # garras
            for k in (-1, 0, 1):
                ang = math.degrees(math.atan2(mao[1] - cotovelo[1], mao[0] - cotovelo[0])) + k * 22
                p.linha(mao, _polar(mao, ang, 9), OSSO, 1.6)
    if estilo == "colosso":
        for lado in (-1, 1):
            base = _soma(j.peito, (lado * 20 * largo, 24))
            cot = _soma(base, (lado * 22, 18 + math.sin(tempo * 1.3 + lado) * 3))
            mao = _soma(cot, (lado * 10, 18))
            p.membro(base, cot, 7, 6, corpo)
            p.membro(cot, mao, 6, 4.5, corpo)
            p.circulo(mao, 5, corpo, borda=False)

    # --- cabeça, cabelo e rosto
    c = j.cabeca
    if estilo == "hollow":
        p.circulo(c, 13, OSSO)  # a máscara de osso
    else:
        p.circulo(c, 13 * (1.1 if estilo == "tita" else 1.0), corpo)
    vento = math.sin(tempo * 2.3) * 2
    if estilo == "espadachim":  # o coque e mechas soltas
        p.circulo(_soma(c, (0, -14)), 5, escuro, borda=False)
        p.linha(_soma(c, (4, -10)), _soma(c, (16 + vento, -16)), escuro, 3)
        p.linha(_soma(c, (-6, -8)), _soma(c, (-14 + vento, 2)), escuro, 2)
    elif estilo == "ninja":
        p.linha(_soma(c, (-13, -4)), _soma(c, (13, -4)), contorno, 3)
        for k in range(2):  # as pontas da bandana
            p.linha(_soma(c, (12, -4)), _soma(c, (24 + vento * 2, -2 + k * 6)), contorno, 2)
    elif estilo == "oni":
        for i in range(7):  # a juba
            a = -150 + i * 20
            p.linha(_soma(c, (0, -2)), _polar(_soma(c, (0, -2)), a + vento, 20), escuro, 3)
    elif estilo == "tita":
        p.linha(_soma(c, (-12, -6)), _soma(c, (12, -6)), alpha(escuro, 180), 3)
    if estilo in ("oni", "colosso", "hollow"):
        chifres = ((-8, -1), (8, 1)) if estilo != "colosso" else ((-10, -1), (0, 0), (10, 1))
        for cx, lado in chifres:
            base = _soma(c, (cx, -10))
            ponta = _soma(c, (cx + lado * 7, -28 if cx else -34))
            p.poligono(
                [_soma(base, (-4, 0)), _soma(base, (4, 0)), ponta],
                OSSO if estilo == "hollow" else contorno,
                False,
            )
    if not costas:  # o rosto: olhos que brilham nos monstros, um traço nos humanos
        if estilo in ("oni", "hollow", "colosso", "tita"):
            for lado in (-1, 1):
                olho = _soma(c, (lado * 5, -1))
                if estilo == "hollow":
                    p.circulo(olho, 3.2, (6, 5, 5, 255), borda=False)
                p.circulo(olho, 1.8, OLHO_RUBRO, borda=False)
            if estilo == "hollow":
                for k in range(-2, 3):  # os dentes da máscara
                    p.linha(_soma(c, (k * 2.5, 6)), _soma(c, (k * 2.5, 9)), (6, 5, 5, 255), 1.2)
        else:
            for lado in (-1, 1):
                p.linha(_soma(c, (lado * 3, -1)), _soma(c, (lado * 8, -2)), alpha(BRANCO, 150), 1.4)

    if not espada or estilo == "tita":
        return
    # --- a arma, na mão direita, no ângulo da pose
    aco = mistura(contorno, BRANCO, 0.3)
    m = j.mao_d
    if estilo == "espadachim":
        ponta = _polar(m, pose.arma, 92)
        p.linha(m, ponta, aco, 3)
        p.linha(_polar(m, pose.arma + 90, 6), _polar(m, pose.arma - 90, 6), contorno, 4)  # a tsuba
        p.linha(m, _polar(m, pose.arma + 180, 14), escuro, 4)  # o cabo
    elif estilo == "monge":
        topo = (m[0], -150)
        p.linha((m[0], 0), topo, contorno, 3)
        p.circulo(topo, 9, contorno, borda=False, largura=max(1, round(2 * escala)))
        for k in (-1, 1):
            p.circulo(_soma(topo, (k * 6, 8)), 3, contorno, borda=False, largura=1)
    elif estilo == "ninja":
        for mao, ang in ((j.mao_e, pose.arma + 160), (m, pose.arma + 40)):
            p.linha(mao, _polar(mao, ang, 30), aco, 3)
    elif estilo == "oni":
        ponta = _polar(m, pose.arma - 10, 84)
        p.linha(m, ponta, contorno, 9)
        for k in range(4):
            t = 0.45 + 0.15 * k
            p.circulo(
                (m[0] + (ponta[0] - m[0]) * t, m[1] + (ponta[1] - m[1]) * t), 3.4, aco, borda=False
            )
    elif estilo == "hollow":
        ponta = _polar(m, pose.arma + 10, 70)
        p.linha(m, ponta, alpha(OSSO, 220), 3)
    elif estilo == "colosso":
        ponta = _polar(m, pose.arma - 20, 140)
        a = math.radians(pose.arma - 20)
        nx, ny = -math.sin(a) * 7, math.cos(a) * 7
        p.poligono([(m[0] + nx, m[1] + ny), ponta, (m[0] - nx, m[1] - ny)], aco, False)
        p.linha(_polar(m, pose.arma + 70, 10), _polar(m, pose.arma - 110, 10), contorno, 5)

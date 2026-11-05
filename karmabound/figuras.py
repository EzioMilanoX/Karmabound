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


def _esqueleto(
    p: Pose, largo: float, tempo: float, altura: float = 1.0, respiro: float = 1.0
) -> _Corpo:
    respira = math.sin(tempo * 2.1) * 1.4 * respiro
    # o peito sobe e os joelhos cedem um pouco a cada respiração
    quadril = (0.0, -50 * altura + (p.agacha + 0.04 * (respiro - 1) * respira) * 10)
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

    def __init__(
        self,
        r: IRenderer,
        x: float,
        y: float,
        e: float,
        contorno: Cor,
        lado: float = 1.0,
        achata: float = 1.0,
    ) -> None:
        """`lado` -1 espelha (olha para a esquerda); `achata` encolhe na vertical (surgir)."""
        self.r, self.x, self.y, self.e, self.contorno = r, x, y, e, contorno
        self.lado, self.achata = lado, achata

    def tela(self, p: Ponto) -> Ponto:
        return self.x + p[0] * self.e * self.lado, self.y + p[1] * self.e * self.achata

    def poligono(self, pontos, cor: Cor, borda: bool = True) -> None:
        tela = [self.tela(p) for p in pontos]
        if borda:
            for dx, dy, a in ((-1.6, 0.8, 70), (1.4, -1.0, 60)):
                self.r.draw_ui_polygon(
                    [(px + dx, py + dy) for px, py in tela],
                    alpha(self.contorno, a * cor[3] / 255),
                )
        self.r.draw_ui_polygon(tela, cor)

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
    respiro: float = 1.0,
) -> None:
    """Desenha a figura com os pés em (x, y).

    `guarda`, `ataque` e `dano` (0–1) misturam as poses; `clarao` tinge a figura com
    `clarao_cor`; `tempo` anima respiração, tecido e cabelo; `costas`: visto de trás
    (sem rosto), como o jogador; `respiro` aumenta a respiração ociosa (1 = a de sempre).
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
    j = _esqueleto(pose, largo, tempo, altura, respiro)
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


# ----------------------------------------------------------------------- criaturas
#
# As invocações em campo. Cada uma é desenhada em unidades com os pés em (0, 0),
# olhando para a direita (`lado` -1 espelha: as do rival olham para o jogador).
# `ataque` (0–1) é o bote; `tempo` anima a respiração, as asas e o caule.

PRETO = (8, 7, 6, 255)
AMARELO = (255, 220, 110, 255)
AZUL_SOMBRA = (120, 190, 255, 255)

# origem (id da técnica que invocou) -> criatura; o resto vira o shikigami de tinta
CRIATURA_DA_ORIGEM = {
    "sapo_chefe": "sapo",
    "caes_divinos": "cao",
    "coruja_trovao": "ave",
    "o_indomavel": "roda",
    "general_da_roda": "roda",  # o chefe que invoca o general
    "levantem_se": "soldado",
    "sementes_de_combate": "broto",
}
# (altura em unidades, até o alto da cabeça ou da roda; tamanho relativo)
MEDIDAS_CRIATURA = {
    "sapo": (84, 1.3),
    "cao": (80, 0.95),
    "ave": (130, 0.85),
    "roda": (212, 0.92),
    "soldado": (142, 0.86),
    "broto": (110, 0.85),
    "shikigami": (106, 0.8),
}


def criatura_de(origem: str) -> str:
    return CRIATURA_DA_ORIGEM.get(origem, "shikigami")


def medidas_criatura(origem: str) -> tuple[float, float]:
    """(altura em unidades, tamanho relativo) da criatura desta origem."""
    return MEDIDAS_CRIATURA[criatura_de(origem)]


def _elipse(c: Ponto, rx: float, ry: float, giro: float = 0.0, n: int = 18) -> list[Ponto]:
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(_soma(c, _rot((math.cos(a) * rx, math.sin(a) * ry), giro)))
    return pts


def _ziguezague(p: _Pincel, a: Ponto, b: Ponto, cor: Cor, semente: float) -> None:
    """Uma faísca de raio, de a até b."""
    passos = 5
    nx, ny = -(b[1] - a[1]), b[0] - a[0]
    norma = math.hypot(nx, ny) or 1
    nx, ny = nx / norma, ny / norma
    anterior = a
    for i in range(1, passos + 1):
        t = i / passos
        desvio = 0 if i == passos else math.sin((semente + i) * 12.9898) * 7
        q = (a[0] + (b[0] - a[0]) * t + nx * desvio, a[1] + (b[1] - a[1]) * t + ny * desvio)
        p.linha(anterior, q, cor, 1.6)
        anterior = q


def _sapo(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O sapo chefe: largo, atarracado, olhos no alto e a boca de orelha a orelha."""
    pele = alpha((122, 76, 44, 255), 255 * v)
    escuro = alpha(mistura(pele, PRETO, 0.42), 255 * v)
    barriga = alpha((206, 172, 120, 255), 255 * v)
    respira = math.sin(t * 1.9) * 1.6
    inclina = -6 - 10 * ataque  # no bote, a cara vem à frente
    p.poligono([(-50, 0), (-58, -20), (-44, -46), (-16, -42), (-8, -14), (-22, 0)], escuro)
    p.poligono(_elipse((0, -36), 50 + respira, 32 + respira * 0.6, inclina), pele)
    p.poligono(_elipse((16, -22), 30, 14, inclina), barriga, False)
    faixa = alpha((150, 28, 30, 255), 230 * v)  # a faixa de chefe atravessa o dorso
    p.membro((-30, -50), (6, -18), 4, 4, faixa, False)
    for wx, wy in ((-22, -50), (-34, -34), (-6, -60), (6, -46), (-14, -28)):
        p.circulo((wx, wy), 2.6, escuro, borda=False)
    abre = max(0.0, ataque - 0.25) * 1.3
    boca = _rot((50, -30), inclina * 0.5)
    canto = _rot((14, -28), inclina * 0.5)
    if abre:
        p.poligono([boca, canto, _soma(boca, (-4, 18 * abre))], alpha((60, 10, 12, 255), 255 * v))
        lingua = alpha((200, 70, 80, 255), 230 * v)
        p.linha(_soma(boca, (-4, 4)), _soma(boca, (24 * abre, 10 * abre)), lingua, 4)
    p.linha(boca, canto, escuro, 2.6)
    for ex, ey in ((20, -66), (38, -62)):
        olho = _rot((ex, ey + respira * 0.4), inclina * 0.5)
        p.circulo(olho, 9, pele)
        p.circulo(_soma(olho, (1, -1)), 5.6, alpha(AMARELO, 255 * v), borda=False)
        p.linha(_soma(olho, (1, -5)), _soma(olho, (1, 3)), alpha(PRETO, 255 * v), 2)
    pe = (42 + 6 * ataque, 0)
    p.membro((30, -22), pe, 6.5, 5, pele)
    for k in (-1, 0, 1):
        p.linha(pe, _soma(pe, (6 + k * 2, k * 3)), escuro, 2)


def _cao(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O cão de sombra: preto como tinta, a marca branca na testa."""
    preto = alpha((16, 14, 20, 255), 255 * v)
    marca = alpha((236, 230, 218, 255), 255 * v)
    for i in range(4):  # a fumaça que escorre das patas
        fase = (t * 0.7 + i * 0.29) % 1.0
        c = (-30 + i * 20 + math.sin(i * 2.3) * 4, -4 - fase * 22)
        p.circulo(c, 4 + 6 * fase, alpha((40, 36, 52, 255), 110 * (1 - fase) * v), borda=False)
    estica = 10 * ataque  # no bote ele se alonga
    for x0, fase in ((-26, 0.0), (-16, 1.6), (18, 0.8), (28, 2.4)):
        passo = math.sin(t * 2.2 + fase) * 1.5
        frente = estica if x0 > 0 else -estica * 0.5
        p.membro((x0 + frente * 0.5, -30), (x0 + 3 + passo + frente, 0), 4.2, 3, preto)
    corpo = [(26, -50), (-28, -48), (-40, -38), (-34, -26), (-10, -24), (22, -26), (34, -34)]
    respira = math.sin(t * 2.4) * 1.2
    p.poligono([(x + (estica if x > 0 else 0), y - respira * (y < -40)) for x, y in corpo], preto)
    cab = (estica, 4 * ataque)
    cabeca = ((20, -48), (32, -66), (48, -68), (66, -56), (64, -50), (44, -46), (30, -36))
    p.poligono([_soma(cab, q) for q in cabeca], preto)
    for base, ponta in (((36, -64), (38, -82)), ((44, -66), (50, -80))):  # as orelhas
        orelha = [_soma(cab, base), _soma(cab, ponta), _soma(cab, (base[0] + 7, base[1]))]
        p.poligono(orelha, preto)
    if ataque > 0.3:  # a bocarra
        boca = [_soma(cab, (64, -50)), _soma(cab, (44, -46)), _soma(cab, (60, -40))]
        p.poligono(boca, alpha((150, 20, 30, 255), 255 * v), False)
    p.linha(_soma(cab, (40, -62)), _soma(cab, (56, -58)), marca, 2.2)
    p.circulo(_soma(cab, (52, -61)), 2.2, marca, borda=False)
    cauda = [(-38 - i * 4, -42 - i * 4 + math.sin(t * 3 + i * 0.7) * i) for i in range(5)]
    for a, b in zip(cauda, cauda[1:], strict=False):
        p.linha(a, b, preto, 4)


def _ave(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """A ave-trovão: plana, as asas abertas estalando raios."""
    corpo = alpha((44, 40, 78, 255), 255 * v)
    escuro = alpha(mistura(corpo, PRETO, 0.4), 255 * v)
    face = alpha((214, 204, 172, 255), 255 * v)
    sombra = [p.tela(q) for q in _elipse((0, 2), 26, 4)]
    p.r.draw_ui_polygon(sombra, alpha(PRETO, 70 * v))  # a sombra no chão, longe dela
    alto = -26 + math.sin(t * 3.0) * 3 - 10 * ataque
    bate = math.sin(t * 6.0) * (1 - ataque) - ataque * 0.8  # no bote as asas recolhem
    off = (8 * ataque, alto)

    def m(q: Ponto) -> Ponto:
        return _soma(q, off)

    def asa(lado: float, cor: Cor) -> None:
        pts = (
            (-2, -48),
            (-40, -86 - bate * 22),
            (-74, -72 - bate * 12),
            (-54, -64),
            (-64, -52),
            (-38, -50),
            (-12, -38),
        )
        p.poligono([m((x * lado, y)) for x, y in pts], cor)

    asa(-0.8, escuro)  # a de trás
    p.poligono([m(q) for q in ((0, -14), (14, -32), (12, -58), (-4, -62), (-14, -40))], corpo)
    for k in (-1, 1):  # as garras penduradas
        p.linha(m((k * 4, -16)), m((k * 6, -4)), face, 2)
    p.circulo(m((6, -64)), 11, corpo)
    p.circulo(m((8, -64)), 7.5, face, borda=False)
    for ex in (5, 12):
        p.circulo(m((ex, -66)), 1.9, alpha(AMARELO, 255 * v), borda=False)
    p.poligono([m((14, -62)), m((22, -60)), m((14, -57))], alpha(AMARELO, 220 * v), False)
    asa(1.0, corpo)  # a da frente
    if int(t * 9) % 3:  # os raios estalam e somem
        for k, (a, b) in enumerate((((-60, -70), (-84, -92)), ((-30, -84), (-36, -108)))):
            _ziguezague(p, m(a), m(b), alpha(AMARELO, 230 * v), math.floor(t * 9) + k)


def _humanoide(p: _Pincel, j: _Corpo, pele: Cor, largo: float, grosso: float) -> None:
    """Pernas, tronco, braços e cabeça de um esqueleto (as invocações de pé)."""
    for quadril_x, joelho, pe in ((-9, j.joelho_e, j.pe_e), (9, j.joelho_d, j.pe_d)):
        q = (j.quadril[0] + quadril_x * largo, j.quadril[1])
        p.membro(q, joelho, 7 * grosso, 6 * grosso, pele)
        p.membro(joelho, pe, 6 * grosso, 4.5 * grosso, pele)
    meio = 24 * largo
    q = j.quadril
    tronco = [
        _soma(j.ombro_e, (-3, -3)),
        _soma(j.ombro_d, (3, -3)),
        (q[0] + meio * 0.72, q[1] - 2),
        (q[0] - meio * 0.72, q[1] - 2),
    ]
    p.poligono(tronco, pele)
    bracos = ((j.ombro_e, j.cotovelo_e, j.mao_e), (j.ombro_d, j.cotovelo_d, j.mao_d))
    for ombro, cotovelo, mao in bracos:
        p.membro(ombro, cotovelo, 6.5 * grosso, 5.5 * grosso, pele)
        p.membro(cotovelo, mao, 5.5 * grosso, 4 * grosso, pele)
        p.circulo(mao, 4.2 * grosso, pele, borda=False)
    p.circulo(j.cabeca, 12, pele)


def _roda(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O general das oito empunhaduras: alto, pálido, a roda girando nas costas."""
    pele = alpha((198, 192, 180, 255), 255 * v)
    escuro = alpha((40, 36, 34, 255), 255 * v)
    ouro = alpha((206, 172, 98, 255), 255 * v)
    pose = _mistura_pose(POSES["parado"], POSES["ataque"], ataque)
    j = _esqueleto(pose, 1.15, t * 0.8, 1.28)
    centro = _soma(j.cabeca, (0, -34))
    giro = t * 0.5 + ataque * 0.785  # a roda vira uma casa a cada golpe
    for i in range(8):
        a = giro + i * math.pi / 4
        dentro = _soma(centro, (math.cos(a) * 6, math.sin(a) * 6))
        fora = _soma(centro, (math.cos(a) * 26, math.sin(a) * 26))
        p.linha(dentro, fora, ouro, 2.2)
        p.circulo(_soma(centro, (math.cos(a) * 30, math.sin(a) * 30)), 3.4, ouro, borda=False)
    p.circulo(centro, 20, ouro, borda=False, largura=max(1, round(3 * p.e)))
    p.circulo(centro, 5, ouro, borda=False)
    _humanoide(p, j, pele, 1.15, 1.2)
    q = j.quadril
    tanga = [
        (q[0] - 20, q[1] - 6),
        (q[0] + 20, q[1] - 6),
        (q[0] + 12, q[1] + 22),
        (q[0] - 12, q[1] + 22),
    ]
    p.poligono(tanga, escuro)
    for dy in (8, 20):  # o peito marcado
        p.linha(_soma(j.peito, (-9, dy)), _soma(j.peito, (9, dy)), alpha(escuro, 110 * v), 1.6)
    c = j.cabeca
    for lado in (-1, 1):  # as asas que cobrem os olhos
        asa = [_soma(c, (lado * 2, -4)), _soma(c, (lado * 22, -12)), _soma(c, (lado * 16, 2))]
        p.poligono(asa, pele)
        p.linha(_soma(c, (lado * 4, -3)), _soma(c, (lado * 18, -8)), escuro, 1.2)
    aco = alpha(mistura((220, 220, 230, 255), pele, 0.2), 255 * v)  # o braço que vira lâmina
    p.linha(j.mao_d, _polar(j.mao_d, pose.arma + 20, 70), aco, 3.4)


def _soldado(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O soldado que levantou da sombra: escuro, olhos azuis, fumaça subindo."""
    corpo = alpha((20, 22, 34, 255), 255 * v)
    fumaca = (46, 36, 74, 255)
    guarda = _mistura_pose(POSES["parado"], POSES["guarda"], 0.5)
    pose = _mistura_pose(guarda, POSES["ataque"], ataque)
    j = _esqueleto(pose, 1.05, t * 0.9, 1.05)
    for i in range(5):
        fase = (t * 0.55 + i * 0.31) % 1.0
        base = j.ombro_e if i % 2 else j.ombro_d
        c = _soma(base, (math.sin(i * 1.9) * 8, -fase * 50))
        p.circulo(c, 4 + 8 * fase, alpha(fumaca, 130 * (1 - fase) * v), borda=False)
    _humanoide(p, j, corpo, 1.05, 1.0)
    h = j.quadril  # a capa em farrapos
    bainha = [(-26 + 52 * i / 7, -4 * (i % 2) + math.sin(t * 2 + i) * 2) for i in range(8)]
    p.poligono([(h[0] - 18, h[1] - 6), (h[0] + 18, h[1] - 6), *reversed(bainha)], corpo)
    c = j.cabeca  # o elmo com a crista
    p.poligono([_soma(c, (-12, -4)), _soma(c, (0, -20)), _soma(c, (12, -4))], corpo)
    for lado in (-1, 1):
        olho = _soma(c, (4 + lado * 4, -1))
        p.circulo(olho, 4.5, alpha(AZUL_SOMBRA, 70 * v), borda=False)
        p.circulo(olho, 1.9, alpha(AZUL_SOMBRA, 255 * v), borda=False)
    aco = alpha((150, 170, 220, 255), 230 * v)
    p.linha(j.mao_d, _polar(j.mao_d, pose.arma, 64), aco, 2.6)


def _broto(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """A semente que brotou: um caule que balança e uma boca de dentes."""
    verde = alpha((70, 128, 74, 255), 255 * v)
    escuro = alpha(mistura(verde, PRETO, 0.45), 255 * v)
    terra = alpha((44, 32, 24, 255), 255 * v)
    dente = alpha((236, 230, 214, 255), 255 * v)
    p.poligono([(-22, 2), (-14, -6), (12, -7), (22, 2)], terra, False)
    balanca = math.sin(t * 1.6) * 5 + ataque * 22
    pts = [(balanca * (i / 6) ** 1.6, -i * 12.5) for i in range(7)]
    for i, (a, b) in enumerate(zip(pts, pts[1:], strict=False)):
        p.membro(a, b, 4.6 - i * 0.4, 4.2 - i * 0.4, verde)
    for (bx, by), lado in ((pts[2], -1), (pts[4], 1)):  # as folhas
        mexe = math.sin(t * 2.2 + lado) * 3
        folha = [
            (bx, by),
            (bx + lado * 14, by - 12 + mexe),
            (bx + lado * 28, by - 4 + mexe),
            (bx + lado * 14, by + 2),
        ]
        p.poligono(folha, verde)
        p.linha((bx, by), (bx + lado * 24, by - 4 + mexe), escuro, 1.2)
    abre = 0.25 + 0.75 * ataque + 0.05 * math.sin(t * 3)
    c = _soma(pts[-1], (6, -8))
    sup = [c, _soma(c, (26, -10 - 18 * abre)), _soma(c, (8, -22 - 6 * abre)), _soma(c, (-10, -12))]
    inf = [c, _soma(c, (26, 6 + 14 * abre)), _soma(c, (8, 14)), _soma(c, (-10, 6))]
    p.poligono([c, sup[1], inf[1]], alpha((150, 30, 40, 255), 255 * v), False)
    for queixo, sentido in ((sup, 1), (inf, -1)):
        p.poligono(queixo, verde)
        a, b = queixo[0], queixo[1]
        for k in range(1, 4):  # os dentes
            d = _soma(a, ((b[0] - a[0]) * k / 4, (b[1] - a[1]) * k / 4))
            p.poligono(
                [_soma(d, (-2, 0)), _soma(d, (2, 0)), _soma(d, (0, 5 * sentido))], dente, False
            )


def _shikigami(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O shikigami de tinta: um boneco de papel que flutua, com o selo no peito."""
    papel = alpha((228, 222, 206, 255), 255 * v)
    tinta = alpha((20, 18, 16, 255), 255 * v)
    alto = -10 + math.sin(t * 2.4) * 4
    giro = math.sin(t * 1.7) * 6 + 14 * ataque

    def m(q: Ponto) -> Ponto:
        return _soma(_rot(_soma(q, (0, 50)), giro), (0, -50 + alto))

    for i in range(3):  # a tinta que pinga dele
        fase = (t * 0.8 + i * 0.33) % 1.0
        gota = (math.sin(i * 2.7) * 8, -14 + alto + fase * 14)
        p.circulo(gota, 2.4 * (1 - fase) + 0.6, tinta, borda=False)
    corpo = (
        (-8, -74),
        (8, -74),
        (34, -70),
        (34, -62),
        (10, -60),
        (14, -22),
        (4, -22),
        (0, -40),
        (-4, -22),
        (-14, -22),
        (-10, -60),
        (-34, -62),
        (-34, -70),
    )
    p.poligono([m(q) for q in corpo], papel)
    p.circulo(m((0, -86)), 12, papel)
    p.linha(m((0, -70)), m((0, -32)), tinta, 2.4)  # a pincelada do nome
    p.linha(m((-6, -64)), m((6, -60)), tinta, 1.6)
    p.circulo(m((0, -50)), 5, alpha((196, 34, 40, 255), 255 * v), borda=False)
    for ex in (-4, 4):
        p.circulo(m((ex + 2, -88)), 1.6, tinta, borda=False)


_CRIATURAS = {
    "sapo": _sapo,
    "cao": _cao,
    "ave": _ave,
    "roda": _roda,
    "soldado": _soldado,
    "broto": _broto,
    "shikigami": _shikigami,
}


def desenhar_criatura(
    r: IRenderer,
    origem: str,
    x: float,
    y: float,
    escala: float,
    tempo: float = 0.0,
    ataque: float = 0.0,
    lado: float = 1.0,
    visivel: float = 1.0,
    surgir: float = 1.0,
    clarao: float = 0.0,
) -> None:
    """Desenha a invocação de `origem` com os pés em (x, y).

    `escala` já é a do lugar; o tamanho próprio da criatura (o sapo é grande) entra
    aqui. `lado` 1 olha para a direita, -1 para a esquerda; `visivel` (0–1) é a
    opacidade; `surgir` (0–1) a faz crescer do chão; `clarao` a cobre de branco.
    """
    if visivel <= 0.01 or surgir <= 0.01:
        return
    tipo = criatura_de(origem)
    altura, tamanho = MEDIDAS_CRIATURA[tipo]
    e = escala * tamanho
    contorno = alpha(mistura((216, 207, 192, 255), BRANCO, clarao), 255 * visivel)
    p = _Pincel(r, x, y, e, contorno, lado, surgir)
    if tipo != "ave":  # a sombra no chão
        s = 34 * e
        sombra = [
            (x - s, y + 2 * e),
            (x + s, y + 2 * e),
            (x + s * 0.7, y + 8 * e),
            (x - s * 0.7, y + 7 * e),
        ]
        r.draw_ui_polygon(sombra, alpha(PRETO, 70 * visivel))
    _CRIATURAS[tipo](p, tempo, ataque, visivel)
    if clarao > 0:  # o branco do golpe por cima
        r.draw_ui_circle(
            x, y - altura * 0.4 * e * surgir, altura * 0.42 * e, alpha(BRANCO, 90 * clarao)
        )


# ----------------------------------------------------------------------- aliados
#
# O companheiro da run (aliados.py): uma figura pequena ao seu lado, em unidades com
# os pés em (0, 0), olhando para a direita. `ataque` (0–1) é o gesto da ação dele.

# (altura em unidades, até o alto da cabeça; tamanho relativo)
MEDIDAS_ALIADO = {
    "faro": (62, 1.0),
    "pequeno_doutor": (92, 0.9),
    "cavaleiro_de_sombra": (150, 0.8),
    "raposa_rubra": (78, 1.0),
    "borboleta_de_glicinia": (118, 0.9),
}


def medidas_aliado(aid: str) -> tuple[float, float]:
    """(altura em unidades, tamanho relativo) do aliado `aid`."""
    return MEDIDAS_ALIADO.get(aid, (80, 1.0))


def _faro(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O cão ninja: pequeno, cara amassada, a bandana de metal na testa e o colete."""
    pelo = alpha((196, 158, 104, 255), 255 * v)
    focinho = alpha((92, 62, 40, 255), 255 * v)
    colete = alpha((44, 62, 92, 255), 255 * v)
    metal = alpha((178, 184, 194, 255), 255 * v)
    respira = math.sin(t * 2.4) * 1.2
    fareja = math.sin(t * 9) * 1.5 * (1 - ataque)  # o nariz não para
    avanca = 10 * ataque
    for x0, fase in ((-14, 0.0), (-6, 1.6), (8, 0.8), (16, 2.4)):  # as patas
        passo = math.sin(t * 2 + fase) * 1.2
        p.membro((x0 + avanca * 0.5, -14), (x0 + passo + avanca * 0.3, 0), 3.4, 3, pelo)
    rabo = math.sin(t * 6) * 6
    p.membro((-20, -20), (-30, -32 + rabo * 0.3), 3, 2, pelo)
    p.poligono(_elipse((0 + avanca * 0.4, -20), 21, 11 + respira * 0.4), pelo)
    p.poligono([(-14 + avanca * 0.4, -28), (12 + avanca * 0.4, -29), (14, -12), (-12, -11)], colete)
    c = (20 + avanca, -36 + respira * 0.5)  # a cabeça grande
    for lado in (-1, 1):
        orelha = [
            _soma(c, (lado * 6 - 2, -8)),
            _soma(c, (lado * 13 - 2, -16)),
            _soma(c, (lado * 12, -4)),
        ]
        p.poligono(orelha, focinho)
    p.circulo(c, 14, pelo)
    p.poligono(_elipse(_soma(c, (11, 4 + fareja * 0.3)), 8, 6), focinho)
    p.circulo(_soma(c, (17, 2 + fareja * 0.3)), 2.4, alpha(PRETO, 255 * v), borda=False)
    p.circulo(_soma(c, (5, -3)), 1.8, alpha(PRETO, 255 * v), borda=False)
    p.poligono(
        [_soma(c, (-13, -10)), _soma(c, (12, -12)), _soma(c, (12, -6)), _soma(c, (-13, -4))], metal
    )
    p.linha(_soma(c, (-2, -10)), _soma(c, (4, -8)), alpha(PRETO, 200 * v), 1.2)
    p.linha(
        _soma(c, (-12, -7)), _soma(c, (-22, -2 + math.sin(t * 3) * 2)), metal, 2
    )  # a ponta da faixa


def _pequeno_doutor(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """A rena médica: pequena, de pé, chapéu rosa com a cruz, galhada e nariz azul."""
    pelo = alpha((150, 96, 60, 255), 255 * v)
    calca = alpha((120, 70, 140, 255), 255 * v)
    chapeu = alpha((232, 120, 156, 255), 255 * v)
    branco = alpha((240, 236, 226, 255), 255 * v)
    galho = alpha((120, 80, 50, 255), 255 * v)
    respira = math.sin(t * 2.2) * 1.4
    pula = -abs(math.sin(ataque * math.pi)) * 14  # o pulinho de quando cura
    for x0 in (-6, 6):
        p.membro((x0, -18 + pula), (x0 + 1, 0 + pula * 0.3), 4, 3.6, pelo)
    p.poligono(_elipse((0, -32 + pula), 14, 16 + respira * 0.5), pelo)
    p.poligono([(-14, -24 + pula), (14, -24 + pula), (12, -12 + pula), (-12, -12 + pula)], calca)
    ergue = 30 * ataque
    for lado in (-1, 1):  # os bracinhos (no gesto, para o alto)
        ombro = (lado * 11, -40 + pula)
        mao = _soma(ombro, (lado * 9, 12 - ergue - 6 * ataque))
        p.membro(ombro, mao, 3.4, 3, pelo)
        p.circulo(mao, 3.2, pelo, borda=False)
    c = (2, -58 + pula + respira * 0.3)
    for lado in (-1, 1):  # a galhada saindo do chapéu
        base = _soma(c, (lado * 10, -14))
        ponta = _soma(base, (lado * 14, -14))
        p.linha(base, ponta, galho, 2.6)
        p.linha(_soma(base, (lado * 7, -7)), _soma(base, (lado * 4, -18)), galho, 2)
        p.linha(_soma(base, (lado * 11, -11)), _soma(base, (lado * 22, -12)), galho, 2)
    p.circulo(c, 12, pelo)
    p.circulo(_soma(c, (10, 3)), 3.6, alpha((70, 120, 230, 255), 255 * v), borda=False)
    p.circulo(_soma(c, (4, -1)), 1.8, alpha(PRETO, 255 * v), borda=False)
    p.poligono(_elipse(_soma(c, (0, -10)), 17, 5), chapeu)  # a aba
    p.poligono(
        [
            _soma(c, (-12, -11)),
            _soma(c, (-10, -26)),
            _soma(c, (0, -31)),
            _soma(c, (10, -26)),
            _soma(c, (12, -11)),
        ],
        chapeu,
    )
    p.linha(_soma(c, (-4, -24)), _soma(c, (4, -16)), branco, 2)  # a cruz
    p.linha(_soma(c, (4, -24)), _soma(c, (-4, -16)), branco, 2)


def _cavaleiro_de_sombra(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """O cavaleiro que jurou lealdade: armadura negra, o penacho e os olhos vermelhos."""
    corpo = alpha((24, 20, 34, 255), 255 * v)
    placa = alpha((58, 52, 76, 255), 255 * v)
    penacho = alpha((150, 30, 60, 255), 255 * v)
    fumaca = (60, 40, 90, 255)
    pose = _mistura_pose(POSES["parado"], POSES["guarda"], 0.3 + 0.7 * ataque)
    j = _esqueleto(pose, 1.1, t * 0.8, 1.05)
    for i in range(4):  # a sombra que sobe dele
        fase = (t * 0.5 + i * 0.27) % 1.0
        c = _soma(j.quadril, (math.sin(i * 2.3) * 14, -fase * 70))
        p.circulo(c, 3 + 7 * fase, alpha(fumaca, 110 * (1 - fase) * v), borda=False)
    h = j.quadril  # a capa
    onda = math.sin(t * 2) * 3
    capa = [
        _soma(j.ombro_e, (-6, 0)),
        _soma(j.ombro_d, (6, 0)),
        (h[0] + 22 + onda, h[1] + 16),
        (h[0] - 22 + onda, h[1] + 12),
    ]
    p.poligono(capa, corpo)
    _humanoide(p, j, corpo, 1.1, 1.15)
    for ombro in (j.ombro_e, j.ombro_d):  # as ombreiras
        p.poligono(_elipse(_soma(ombro, (0, -2)), 10, 6), placa)
    c = j.cabeca  # o elmo e o penacho
    p.poligono(
        [
            _soma(c, (-12, -6)),
            _soma(c, (0, -16)),
            _soma(c, (12, -6)),
            _soma(c, (10, 8)),
            _soma(c, (-10, 8)),
        ],
        placa,
    )
    balanca = math.sin(t * 2.4) * 4
    p.poligono(
        [
            _soma(c, (-2, -14)),
            _soma(c, (-24, -22 + balanca)),
            _soma(c, (-30, -8 + balanca)),
            _soma(c, (-6, -10)),
        ],
        penacho,
    )
    p.linha(_soma(c, (-8, 0)), _soma(c, (10, 0)), alpha(PRETO, 255 * v), 2)
    for ex in (1, 7):
        olho = _soma(c, (ex, 0))
        p.circulo(olho, 3.6, alpha(OLHO_RUBRO, 80 * v), borda=False)
        p.circulo(olho, 1.6, alpha(OLHO_RUBRO, 255 * v), borda=False)
    aco = alpha((150, 150, 175, 255), 240 * v)
    p.linha(j.mao_d, _polar(j.mao_d, pose.arma - 10, 70), aco, 3.2)
    p.linha(_polar(j.mao_d, pose.arma + 80, 9), _polar(j.mao_d, pose.arma - 100, 9), aco, 3)


def _raposa_rubra(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """A raposa de chakra vermelho: sentada, várias caudas e a brasa em volta."""
    pelo = alpha((214, 72, 34, 255), 255 * v)
    escuro = alpha((120, 30, 20, 255), 255 * v)
    brasa = (255, 140, 60, 255)
    olho = alpha((255, 220, 90, 255), 255 * v)
    avanca = 18 * ataque
    for i in range(6):  # a brasa que sobe
        fase = (t * 0.9 + i * 0.17) % 1.0
        c = (math.sin(i * 1.9) * 26 - 6, -10 - fase * 70)
        p.circulo(c, 3 + 3 * (1 - fase), alpha(brasa, 150 * (1 - fase) * v), borda=False)
    for i in range(4):  # as caudas, em leque atrás
        a = (-12, -18)
        pts = [a]
        ang = math.radians(178 + i * 24)  # da esquerda para o alto
        for s in range(1, 5):
            curva = ang + s * 0.18 + math.sin(t * 2.6 + i * 1.3) * 0.08 * s
            x, y = pts[-1]
            pts.append((x + math.cos(curva) * 9, y + math.sin(curva) * 9))
        for s, (q0, q1) in enumerate(zip(pts, pts[1:], strict=False)):
            p.membro(q0, q1, 6.5 - s * 0.6, 6 - s * 0.6, pelo)
        p.circulo(pts[-1], 4, alpha((255, 230, 200, 255), 255 * v), borda=False)
    for x0 in (2, 12):  # as patas da frente
        p.membro((x0 + avanca * 0.6, -22), (x0 + 2 + avanca, 0), 3.6, 3, pelo)
    p.poligono(_elipse((-2 + avanca * 0.4, -22), 18, 14, -0.3), pelo)
    c = (16 + avanca, -44)
    for lado in (-1, 1):
        orelha = [
            _soma(c, (lado * 5 - 3, -6)),
            _soma(c, (lado * 9 - 2, -22)),
            _soma(c, (lado * 11 + 3, -4)),
        ]
        p.poligono(orelha, pelo)
        p.poligono(
            [
                _soma(c, (lado * 6 - 2, -7)),
                _soma(c, (lado * 9 - 2, -17)),
                _soma(c, (lado * 9 + 2, -6)),
            ],
            escuro,
            False,
        )
    p.circulo(c, 11, pelo)
    p.poligono([_soma(c, (6, -4)), _soma(c, (22, 2)), _soma(c, (6, 6))], pelo)  # o focinho
    p.circulo(_soma(c, (21, 2)), 2, alpha(PRETO, 255 * v), borda=False)
    p.linha(_soma(c, (2, -3)), _soma(c, (8, -2)), olho, 2)  # o olho em fenda
    abre = max(0.0, ataque - 0.3) * 1.4
    if abre:
        p.poligono(
            [_soma(c, (6, 4)), _soma(c, (22, 4 + 6 * abre)), _soma(c, (6, 8))],
            alpha((90, 10, 10, 255), 255 * v),
            False,
        )


def _borboleta_de_glicinia(p: _Pincel, t: float, ataque: float, v: float) -> None:
    """A borboleta de glicínia: asas lilás que batem, voando um pouco acima do chão."""
    lilas = alpha((176, 132, 226, 255), 235 * v)
    claro = alpha((226, 206, 250, 255), 235 * v)
    veia = alpha((70, 40, 110, 255), 220 * v)
    corpo = alpha((40, 28, 50, 255), 255 * v)
    voa = math.sin(t * 2.1) * 6 - 18 * ataque
    c = (0 + 24 * ataque, -78 + voa)
    bate = 0.3 + 0.7 * abs(math.cos(t * (7 + 6 * ataque)))  # as asas abrem e fecham
    for i in range(5):  # o pó de veneno que cai
        fase = (t * 0.7 + i * 0.2) % 1.0
        g = (c[0] + math.sin(i * 2.7) * 12, c[1] + 10 + fase * 60)
        p.circulo(
            g,
            1.8 * (1 - fase) + 0.6,
            alpha((200, 160, 255, 255), 200 * (1 - fase) * v),
            borda=False,
        )
    for lado in (-1, 1):
        cima = [
            c,
            _soma(c, (lado * 30 * bate, -26)),
            _soma(c, (lado * 40 * bate, -6)),
            _soma(c, (lado * 8 * bate, 2)),
        ]
        baixo = [
            c,
            _soma(c, (lado * 26 * bate, 8)),
            _soma(c, (lado * 18 * bate, 24)),
            _soma(c, (lado * 4 * bate, 10)),
        ]
        p.poligono(cima, lilas)
        p.poligono(baixo, claro)
        p.linha(c, _soma(c, (lado * 30 * bate, -18)), veia, 1.2)
        p.linha(c, _soma(c, (lado * 20 * bate, 16)), veia, 1.2)
        p.circulo(
            _soma(c, (lado * 24 * bate, -12)),
            3.2 * bate,
            alpha((255, 240, 255, 255), 220 * v),
            borda=False,
        )
    p.membro(_soma(c, (0, -8)), _soma(c, (0, 12)), 2.4, 1.6, corpo)
    for lado in (-1, 1):  # as antenas
        p.linha(_soma(c, (0, -8)), _soma(c, (lado * 7, -20)), corpo, 1.2)


_ALIADOS = {
    "faro": _faro,
    "pequeno_doutor": _pequeno_doutor,
    "cavaleiro_de_sombra": _cavaleiro_de_sombra,
    "raposa_rubra": _raposa_rubra,
    "borboleta_de_glicinia": _borboleta_de_glicinia,
}


def desenhar_aliado(
    r: IRenderer,
    aid: str,
    x: float,
    y: float,
    escala: float,
    tempo: float = 0.0,
    ataque: float = 0.0,
    lado: float = 1.0,
    visivel: float = 1.0,
    clarao: float = 0.0,
) -> None:
    """Desenha o aliado `aid` com os pés em (x, y) (a borboleta voa acima deles).

    `ataque` (0–1) é o gesto da ação (o bote, o pulinho da cura, a guarda); `clarao`
    cobre de branco; um id desconhecido desenha o shikigami de tinta."""
    if visivel <= 0.01:
        return
    altura, tamanho = medidas_aliado(aid)
    e = escala * tamanho
    contorno = alpha(mistura((216, 207, 192, 255), BRANCO, clarao), 255 * visivel)
    p = _Pincel(r, x, y, e, contorno, lado)
    s = 26 * e
    r.draw_ui_polygon(
        [
            (x - s, y + 2 * e),
            (x + s, y + 2 * e),
            (x + s * 0.7, y + 7 * e),
            (x - s * 0.7, y + 6 * e),
        ],
        alpha(PRETO, (40 if aid == "borboleta_de_glicinia" else 70) * visivel),
    )
    _ALIADOS.get(aid, _shikigami)(p, tempo, ataque, visivel)
    if clarao > 0:
        r.draw_ui_circle(x, y - altura * 0.45 * e, altura * 0.4 * e, alpha(BRANCO, 90 * clarao))

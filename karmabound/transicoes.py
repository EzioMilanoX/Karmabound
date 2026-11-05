"""Movimento fora da luta: a transição de tinta entre as telas e a vida das cartas.

- `Transicao`: o Fluxo a chama a cada troca de tela. Ela desenha POR CIMA da tela nova
  (pelo `set_on_draw_ui` do GameLoop), então nenhuma cena precisa saber dela: a tela velha
  fica congelada enquanto a pincelada a cobre, e a nova aparece quando a tinta passa.
  A tela nova já está no topo da pilha desde o primeiro quadro e recebe entrada sempre;
  Enter durante a transição só a encurta.
- `Camada`: um renderer por cima de outro, com escala, deslocamento e opacidade (cartas
  que surgem e carimbam, painéis que entram em fade).
- `Cartas`: o relógio das cartas de uma tela (entrada escalonada, foco da seleção com
  easing, carimbo da escolhida).

Tudo anda no tempo das animações das opções (`OPCOES.velocidade`); nada aqui decide regra.
"""

from __future__ import annotations

import math
import time

from ouroboros.interfaces.renderer import IRenderer

from karmabound import vfx
from karmabound.opcoes import OPCOES
from karmabound.visual import (
    ALTURA,
    FONTE_PINCEL,
    LARGURA,
    SANGUE_VIVO,
    TINTA,
    alpha,
    ease_out,
)

TINTA_NEGRA = (9, 8, 7, 255)
BORDA_SANGUE = (92, 12, 15, 255)  # a borda molhada da pincelada


def suave(x: float) -> float:
    """Ease in-out (smoothstep), preso em 0..1."""
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _preso(x: float) -> float:
    return max(0.0, min(1.0, x))


# ----------------------------------------------------------------------- Camada


class Camada:
    """Desenha por cima de `r` com escala em volta de `pivo`, deslocamento e opacidade.

    Repassa só as primitivas de UI e o texto (o que as telas de menu usam); o resto vai
    direto ao renderer de baixo. A opacidade é quantizada para não encher o cache de texto.
    """

    def __init__(self, r, pivo=(0.0, 0.0), escala=1.0, dx=0.0, dy=0.0, opac=1.0) -> None:
        self.r = r
        self.px, self.py = pivo
        self.s = escala
        self.dx, self.dy = dx, dy
        self.opac = _preso(opac)

    def _xy(self, x: float, y: float) -> tuple[float, float]:
        return self.px + (x - self.px) * self.s + self.dx, self.py + (
            y - self.py
        ) * self.s + self.dy

    def _cor(self, cor):
        if self.opac >= 1.0:
            return cor
        a = round(cor[3] * self.opac / 8) * 8
        return (cor[0], cor[1], cor[2], max(0, min(255, a)))

    def _larg(self, w: int) -> int:
        return 0 if w == 0 else max(1, round(w * self.s))

    def draw_text(self, x, y, text, size, rgba, anchor="topleft", font_id=None) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        x, y = self._xy(x, y)
        self.r.draw_text(
            x, y, text, max(6, round(size * self.s)), cor, anchor=anchor, font_id=font_id
        )

    def draw_ui_rect(self, x, y, w, h, rgba) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        x, y = self._xy(x, y)
        self.r.draw_ui_rect(x, y, w * self.s, h * self.s, cor)

    def draw_ui_line(self, x1, y1, x2, y2, rgba, width=1) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        x1, y1 = self._xy(x1, y1)
        x2, y2 = self._xy(x2, y2)
        self.r.draw_ui_line(x1, y1, x2, y2, cor, self._larg(width))

    def draw_ui_circle(self, x, y, radius, rgba, width=0) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        x, y = self._xy(x, y)
        self.r.draw_ui_circle(x, y, radius * self.s, cor, self._larg(width))

    def draw_ui_arc(self, x, y, radius, start_rad, end_rad, rgba, width=1) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        x, y = self._xy(x, y)
        self.r.draw_ui_arc(x, y, radius * self.s, start_rad, end_rad, cor, self._larg(width))

    def draw_ui_polygon(self, points, rgba, width=0) -> None:
        cor = self._cor(rgba)
        if cor[3] <= 0:
            return
        self.r.draw_ui_polygon([self._xy(x, y) for x, y in points], cor, self._larg(width))

    def __getattr__(self, nome):
        return getattr(self.r, nome)


def real(r):
    """O renderer de verdade por baixo de qualquer `Camada`."""
    while isinstance(r, Camada):
        r = r.r
    return r


# ----------------------------------------------------------------------- Cartas


def carimbo(u: float) -> float:
    """A escala do carimbo: cresce rápido até 1,10 e assenta em 1,03."""
    if u <= 0:
        return 1.0
    if u < 0.3:
        return 1.0 + 0.1 * ease_out(u / 0.3)
    return 1.1 - 0.07 * suave((u - 0.3) / 0.7)


class Cartas:
    """O relógio das cartas (ou linhas) de uma tela de escolha.

    `avancar(dt, cursor, n)` a cada quadro; `camada(r, i, pivo)` devolve onde e como
    desenhar a carta `i`: surge de baixo com atraso por carta, a do cursor levanta, e
    depois de `escolher(i)` a escolhida carimba enquanto as outras afundam e somem.
    """

    ATRASO = 0.07  # entre uma carta e a próxima
    ENTRADA = 0.34  # o tempo de cada carta surgir
    CARIMBO = 0.26
    LEVANTA = 10.0  # px que a carta do cursor sobe
    SOBE = 34.0  # de onde a carta vem (px abaixo)

    def __init__(self, sobe: float | None = None, lado: bool = False) -> None:
        self.t = 0.0
        self.foco: list[float] = []
        self.escolhida: int | None = None
        self.t_escolha = 0.0
        self.sobe = self.SOBE if sobe is None else sobe
        self.lado = lado  # True: entra da esquerda (listas), não de baixo (cartas)

    def avancar(self, dt: float, cursor: int | None, n: int) -> None:
        dt *= OPCOES.velocidade
        self.t += dt
        if len(self.foco) != n:
            self.foco = (self.foco + [0.0] * n)[:n]
        puxa = 1 - math.exp(-dt * 14)
        for i in range(n):
            alvo = 1.0 if i == cursor else 0.0
            if self.escolhida is not None:
                alvo = 1.0 if i == self.escolhida else 0.0
            self.foco[i] += (alvo - self.foco[i]) * puxa

    def foco_de(self, i: int) -> float:
        return self.foco[i] if 0 <= i < len(self.foco) else 0.0

    def surgiu(self, i: int) -> float:
        """0 (ainda não apareceu) a 1 (no lugar)."""
        return ease_out(_preso((self.t - i * self.ATRASO) / self.ENTRADA))

    def escolher(self, i: int) -> None:
        if self.escolhida is None:
            self.escolhida, self.t_escolha = i, self.t

    def u_carimbo(self) -> float:
        if self.escolhida is None:
            return 0.0
        return _preso((self.t - self.t_escolha) / self.CARIMBO)

    @property
    def assentou(self) -> bool:
        n = max(1, len(self.foco))
        return self.t >= (n - 1) * self.ATRASO + self.ENTRADA

    def pulso(self) -> float:
        """0..1, para a borda da carta do cursor pulsar."""
        return 0.5 + 0.5 * math.sin(self.t * 4.2)

    def camada(self, r, i: int, pivo, ordem: int | None = None) -> Camada:
        """`ordem`: a posição na fila de entrada, se não for `i` (listas que rolam)."""
        k = self.surgiu(i if ordem is None else ordem)
        f = self.foco_de(i)
        escala, opac = 0.94 + 0.06 * k, k
        dx = -self.sobe * (1 - k) if self.lado else 0.0
        dy = 0.0 if self.lado else self.sobe * (1 - k)
        if self.escolhida is not None:
            u = self.u_carimbo()
            if i == self.escolhida:  # carimba: cresce e assenta de volta no lugar
                escala *= carimbo(u)
                f *= 1 - suave(u)
            else:
                opac *= 1 - suave(u * 1.4)
                dy += 26 * suave(u)
                escala *= 1 - 0.05 * u
        if not self.lado:
            dy -= self.LEVANTA * f
        return Camada(r, pivo, escala, dx, dy, opac)

    def selo(self, r, x: float, y: float, kanji: str, tam: float = 30) -> None:
        """O selo vermelho do carimbo, batido no canto da escolhida."""
        u = self.u_carimbo()
        if self.escolhida is None or u <= 0.12:
            return
        v = _preso((u - 0.12) / 0.4)
        s = 1.8 - 0.8 * ease_out(v)  # cai de grande para o tamanho certo
        lado = tam * 1.5 * s
        cor = alpha(SANGUE_VIVO, 230 * min(1.0, v * 2.5))
        r.draw_ui_rect(x - lado / 2, y - lado / 2, lado, lado, alpha(cor, cor[3] * 0.25))
        r.draw_ui_polygon(
            [
                (x - lado / 2, y - lado / 2),
                (x + lado / 2, y - lado / 2),
                (x + lado / 2, y + lado / 2),
                (x - lado / 2, y + lado / 2),
            ],
            cor,
            max(2, round(3 * s)),
        )
        r.draw_text(x, y, kanji, max(8, round(tam * s)), cor, anchor="center", font_id=FONTE_PINCEL)


# ----------------------------------------------------------------------- a pincelada


def _borda(base: float, semente: float, inclina: float = 0.26) -> list[tuple[float, float]]:
    """A borda irregular da pincelada, de cima para baixo (x cresce para a direita)."""
    pontos = []
    n = 40
    for j in range(n + 1):
        y = -24 + (ALTURA + 48) * j / n
        irregular = (
            10 * math.sin(j * 0.55 + semente)
            + 5 * math.sin(j * 1.7 + semente * 1.3)
            + 2.5 * math.sin(j * 4.1 + semente * 2.1)
        )
        pontos.append((base + inclina * (ALTURA / 2 - y) + irregular, y))
    return pontos


_FIOS = [  # (y, comprimento, espessura): os fios de cerda que a pincelada arrasta
    (
        (i * 0.137 + 0.03) % 1.0 * ALTURA,
        40 + 110 * abs(math.sin(i * 2.7)),
        2 + i % 3,
    )
    for i in range(22)
]
_MARGEM = 0.26 * ALTURA / 2 + 30  # o quanto a borda inclinada passa do centro


def _x_da_borda(base: float, y: float, inclina: float = 0.26) -> float:
    return base + inclina * (ALTURA / 2 - y)


def _base(k: float) -> float:
    """Onde a borda está: fora da tela à esquerda (k=0) até fora à direita (k=1)."""
    return -_MARGEM - 40 + (LARGURA + 2 * _MARGEM + 80) * suave(k)


def _borda_molhada(r: IRenderer, borda, lado: int, forca: float) -> None:
    """O vermelho da tinta fresca, logo atrás da borda."""
    for (x1, y1), (x2, y2) in zip(borda, borda[1:], strict=False):
        r.draw_ui_line(x1 - lado * 5, y1, x2 - lado * 5, y2, alpha(BORDA_SANGUE, 210 * forca), 5)


def pincelada_cobre(r: IRenderer, k: float, semente: float = 0.0) -> None:
    """A tinta entra pela esquerda e cobre a tela até a borda chegar em `k` (0..1)."""
    if k <= 0:
        return
    base = _base(k)
    borda = _borda(base, semente)
    r.draw_ui_polygon([(-80, -30), *borda, (-80, ALTURA + 30)], TINTA_NEGRA)
    _fios(r, base, +1, k, semente)
    _borda_molhada(r, borda, +1, 1.0)


def pincelada_descobre(r: IRenderer, k: float, semente: float = 0.0) -> None:
    """A tinta sai pela direita: da esquerda até a borda em `k`, a tela nova aparece."""
    if k >= 1:
        return
    base = _base(k)
    borda = _borda(base, semente + 3.1)
    r.draw_ui_polygon([*borda, (LARGURA + 80, ALTURA + 30), (LARGURA + 80, -30)], TINTA_NEGRA)
    _fios(r, base, -1, 1 - k, semente + 3.1)
    _borda_molhada(r, borda, -1, 0.9 * (1 - k))


def _fios(r: IRenderer, base: float, lado: int, forca: float, semente: float) -> None:
    """As cerdas: fios de tinta à frente (lado=+1) ou atrás (lado=-1) da borda."""
    for i, (y, comp, larg) in enumerate(_FIOS):
        x0 = _x_da_borda(base, y) - lado * 22
        c = comp * (0.6 + 0.4 * math.sin(i * 1.3 + semente)) * min(1.0, 0.4 + forca)
        x1 = x0 + lado * c
        r.draw_ui_line(x0, y, x1, y, alpha(TINTA_NEGRA, 235), larg + 1)
        r.draw_ui_line(x1, y, x1 + lado * c * 0.35, y, alpha(TINTA_NEGRA, 140), max(1, larg - 1))
        if i % 4 == 0:  # um respingo na ponta
            r.draw_ui_circle(x1 + lado * (c * 0.5 + 8), y + 3, 2 + i % 3, alpha(TINTA_NEGRA, 220))


# ----------------------------------------------------------------------- o corte (luta)

_COMP = math.hypot(LARGURA, ALTURA)
_D = (-LARGURA / _COMP, ALTURA / _COMP)  # a direção do corte: do alto à direita para baixo
_N = (ALTURA / _COMP, LARGURA / _COMP)  # a normal: aponta para baixo e para a direita
_C = (LARGURA / 2, ALTURA / 2)


def _metade(lado: int, off: tuple[float, float]) -> list[tuple[float, float]]:
    """Um semiplano da tela, do corte para o lado `lado` (-1: alto/esquerda, +1: baixo)."""
    big = _COMP
    cx, cy = _C[0] + off[0], _C[1] + off[1]
    dx, dy = _D[0] * big, _D[1] * big
    nx, ny = _N[0] * big * lado, _N[1] * big * lado
    return [
        (cx + dx, cy + dy),
        (cx - dx, cy - dy),
        (cx - dx + nx, cy - dy + ny),
        (cx + dx + nx, cy + dy + ny),
    ]


def _reta(r: IRenderer, off, cor, largura: int, comprimento: float = _COMP) -> None:
    """Um traço ao longo do corte (deslocado por `off`), do alto à direita para baixo."""
    ini = (_C[0] - _D[0] * _COMP / 2 + off[0], _C[1] - _D[1] * _COMP / 2 + off[1])
    fim = (ini[0] + _D[0] * comprimento, ini[1] + _D[1] * comprimento)
    r.draw_ui_line(*ini, *fim, cor, largura)


def _lamina(r: IRenderer, comprimento: float, brilho: float) -> None:
    """O traço da lâmina: um rastro largo de sangue, o fio vermelho e o núcleo claro."""
    if brilho <= 0:
        return
    zero = (0.0, 0.0)
    _reta(r, zero, alpha(SANGUE_VIVO, 60 * brilho), 26, comprimento)
    _reta(r, zero, alpha(SANGUE_VIVO, 150 * brilho), 9, comprimento)
    _reta(r, zero, alpha(TINTA, 255 * brilho), 3, comprimento)


def _metade_de_tinta(r: IRenderer, lado: int, off, borda: float) -> None:
    """Uma metade da tela em tinta, com a borda do corte molhada de vermelho."""
    r.draw_ui_polygon(_metade(lado, off), TINTA_NEGRA)
    if borda > 0:
        dentro = (off[0] + _N[0] * 4 * lado, off[1] + _N[1] * 4 * lado)
        _reta(r, dentro, alpha(BORDA_SANGUE, 230 * borda), 6)


def corte_fecha(r: IRenderer, k: float) -> None:
    """A lâmina risca a tela na diagonal e as duas metades de tinta se fecham sobre ela."""
    if k <= 0:
        return
    if k < 0.3:
        _lamina(r, _COMP * ease_out(k / 0.3), 1.0)
        return
    u = suave((k - 0.3) / 0.7)
    longe = 620 * (1 - u)
    for lado in (-1, 1):
        _metade_de_tinta(r, lado, (_N[0] * longe * lado, _N[1] * longe * lado), 1.0)
    _lamina(r, _COMP, 1.0 - 0.5 * u)


def corte_cheio(r: IRenderer, k: float) -> None:
    """A tela inteira fechada: só a cicatriz do corte, apagando."""
    r.draw_ui_rect(0, 0, LARGURA, ALTURA, TINTA_NEGRA)
    _reta(r, (0.0, 0.0), alpha(SANGUE_VIVO, 140 * (1 - k)), 3)


def corte_abre(r: IRenderer, k: float) -> None:
    """As metades se separam pelo corte (e escorregam uma contra a outra): a luta aparece."""
    if k >= 1:
        return
    u = suave(k)
    abre, desliza = 660 * u, 90 * u
    for lado in (-1, 1):
        off = (
            _N[0] * abre * lado + _D[0] * desliza * lado,
            _N[1] * abre * lado + _D[1] * desliza * lado,
        )
        _metade_de_tinta(r, lado, off, 1 - u)


# ----------------------------------------------------------------------- a transição

# segundos na velocidade 1: (fecha, cheio, abre). "segura" vem da tela velha (o carimbo).
DURACOES = {"tinta": (0.18, 0.0, 0.24), "corte": (0.22, 0.12, 0.22)}


class Transicao:
    """A troca de tela do Fluxo, em fases: segura (o carimbo da velha), fecha (a tinta
    cobre a velha), cheio (tudo coberto; só no corte) e abre (a tinta descobre a nova).
    Desenha pelo callback de UI do GameLoop.

    `tolerante`: se a tela velha quebrar ao ser desenhada de novo (estado que já andou),
    a fase de fechar vira tinta inteira em vez de derrubar o jogo. Os testes desligam.
    """

    tolerante = True

    def __init__(self, entrada=None, mundo=None, relogio=time.perf_counter) -> None:
        self._entrada = entrada or (lambda: None)  # funções: o loop pode trocar a entrada
        self._mundo = mundo or (lambda: None)
        self._relogio = relogio
        self._antes: float | None = None
        self.velha = None
        self.estilo = "tinta"
        self.t = 0.0
        self.segura = self.fecha = self.cheio = self.abre = 0.0
        self.quadros = 0
        self.semente = 0.0
        self.ativa = False

    @property
    def total(self) -> float:
        return self.segura + self.fecha + self.cheio + self.abre

    def comecar(self, velha, estilo: str = "tinta") -> None:
        """`velha`: a tela que sai (None: começa já coberta, como na abertura do jogo)."""
        self.estilo = estilo if estilo in DURACOES else "tinta"
        self.fecha, self.cheio, self.abre = DURACOES[self.estilo]
        self.velha = velha
        self.segura = float(getattr(velha, "segurar_saida", 0.0) or 0.0) if velha else 0.0
        self.t = 0.0 if velha is not None else self.fecha
        self.quadros = 0
        self.semente = (self.semente + 1.7) % 6.28
        self.ativa = True

    def _fases(self):
        return (
            ("segura", self.segura),
            ("fecha", self.fecha),
            ("cheio", self.cheio),
            ("abre", self.abre),
        )

    def fase(self) -> str | None:
        return self.onde()[0]

    def onde(self) -> tuple[str | None, float]:
        """(a fase, quanto dela já passou de 0 a 1)."""
        if not self.ativa:
            return None, 0.0
        t = self.t
        for nome, dur in self._fases():
            if t < dur:
                return nome, t / dur
            t -= dur
        return "abre", 1.0

    def avancar(self, dt: float) -> None:
        if not self.ativa:
            return
        dt *= OPCOES.velocidade
        if self.velha is not None and self.fase() in ("segura", "fecha"):
            animar = getattr(self.velha, "animar", None)
            if animar is not None:
                animar(dt)  # o carimbo da velha continua enquanto a tinta não a cobre
        self.t += dt
        self.quadros += 1
        if self.t >= self.total:
            self.terminar()

    def terminar(self) -> None:
        self.ativa = False
        self.velha = None

    def _velha(self, r: IRenderer) -> bool:
        try:
            self.velha.render(self._mundo(), r)
            return True
        except Exception:
            if not self.tolerante:
                raise
            r.set_camera_offset(0, 0)
            self.velha = None
            return False

    def desenhar(self, r: IRenderer) -> None:
        fase, k = self.onde()
        if fase is None:
            return
        corte = self.estilo == "corte"
        if fase in ("segura", "fecha"):
            if self.velha is None or not self._velha(r):
                fase = "cheio"  # sem a velha para mostrar: a tinta já está fechada
            elif fase == "fecha":
                (corte_fecha if corte else pincelada_cobre)(r, k)
        if fase == "cheio":
            if corte:
                corte_cheio(r, k)
            else:
                r.draw_ui_rect(0, 0, LARGURA, ALTURA, TINTA_NEGRA)
        elif fase == "abre":
            if corte:
                corte_abre(r, k)
            else:
                pincelada_descobre(r, k, self.semente)

    def quadro(self, r: IRenderer) -> None:
        """O callback de UI do GameLoop: mede o tempo, deixa Enter encurtar, desenha."""
        agora = self._relogio()
        dt = 0.0 if self._antes is None else min(0.1, max(0.0, agora - self._antes))
        self._antes = agora
        if not self.ativa:
            return
        entrada = self._entrada()
        if (
            self.quadros > 0  # o Enter que trocou a tela não conta
            and entrada is not None
            and entrada.is_action_pressed("confirmar")
        ):
            self.terminar()
            return
        self.avancar(dt)
        self.desenhar(r)


def revelar(cena, r: IRenderer, t: float) -> None:
    """O `vfx.revelar` de uma tela, a não ser que o Fluxo cuide da entrada dela."""
    if not getattr(cena, "sem_revelar", False):
        vfx.revelar(r, t)

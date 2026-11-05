"""Tela da roleta: a mandala de selos, as correntes do Carma e o Despertar.

Só apresentação: todo sorteio passa pela `Mesa`. A cena escolhe o alvo
antes de animar (o resultado já está decidido quando o selo começa a correr).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes, vfx
from karmabound.mesa import Giro, Mesa
from karmabound.opcoes import OPCOES
from karmabound.rodas import Fatia
from karmabound.transicoes import Camada, Cartas, suave
from karmabound.visual import (  # noqa: F401  (reexporta para quem importava daqui)
    ALTURA,
    FERRO,
    FONTE_PINCEL,
    FUNDO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    Cor,
    moldura,
)
from karmabound.visual import alpha as _alpha
from karmabound.visual import ease_out as _ease_out
from karmabound.visual import hex_cor as _hex
from karmabound.visual import mistura as _mistura
from karmabound.visual import pct as _pct
from karmabound.visual import quebrar as _quebrar

CENTRO = (370, 352)
RAIO_SELOS = 170
RAIO_SELO = 27
RAIO_CORRENTE = 232
RAIO_ENSO = 268
ELOS = 44

DURACAO_GIRO = 2.4
DURACAO_SUBGIRO = 1.1  # cada opção do modo "escolha"
DURACAO_QUEBRA = 1.3  # correntes se partindo, antes do giro do Despertar
VOLTAS = 2

ORDEM_RODAS = ("linhagem", "destino", "tecnicas", "arco", "reliquias")
MAX_SELOS = 20  # rodas maiores mostram uma amostra na mandala (sempre com as sorteadas)

# O cartão do resultado: o lugar de sempre, o mais alto que ele sobe (sobre as Taxas), o pé dele
# e as letras que ele tenta, da maior para a menor: (tamanho, caracteres por linha, entrelinha).
TOPO_CARTAO = 380
TOPO_MAXIMO_CARTAO = 218
FUNDO_CARTAO = 556  # acima da borda de baixo da moldura
LETRAS_CARTAO = ((16, 24, 21), (14, 28, 18), (13, 31, 16))


LARGURA_POR_LETRA = 0.58  # a letra de pincel, com o espaçamento: largura ≈ 0,58 × tamanho
LARGURA_SELO = 27  # caracteres do selo de combo (融 共) embaixo do nome de uma opção


def tam_que_cabe(texto: str, tam: int, largura: float) -> int:
    """O maior tamanho (até `tam`, no mínimo 12) em que `texto` cabe em `largura`."""
    if not texto:
        return tam
    return max(12, min(tam, int(largura / (LARGURA_POR_LETRA * len(texto)))))


@dataclass(frozen=True)
class _Cartao:
    fatia: Fatia
    topo: int
    linhas: list[str]
    tam: int
    passo: int
    origem: list[str]


class RoletaScene(IScene):
    def __init__(
        self,
        mesa: Mesa,
        entrada: IInputProvider,
        ao_sair,
        roda_fixa: str | None = None,
        girar=None,
        ao_concluir=None,
        titulo: str = "",
        jornada=None,
    ) -> None:
        """Sem `girar`: caixa de areia (abas, teclas de teste). Com `girar` (modo jornada):
        uma roda só, um giro feito por `girar()` (a Jornada), e `ao_concluir(indice)` no Enter.
        """
        self.mesa = mesa
        self.entrada = entrada
        self.ao_sair = ao_sair
        self.girar_fn = girar
        self.ao_concluir = ao_concluir
        self.titulo = titulo
        self.j = jornada
        self.cores = {r.id: _hex(r.cor) for r in mesa.raridades}
        self.cores_claras = {r: _mistura(c, TINTA, 0.25) for r, c in self.cores.items()}
        self.nomes_raridade = {r.id: r.nome for r in mesa.raridades}
        self.i_roda = ORDEM_RODAS.index(roda_fixa) if roda_fixa else 1
        self.selos = self._amostrar()  # os selos desenhados na mandala
        self.estado = "parado"  # parado | quebrando | girando | escolhendo | resultado
        self.t = 0.0  # tempo no estado atual
        self.relogio = 0.0  # tempo total, para pulsos
        self.giro: Giro | None = None
        self.alvos: list[int] = []  # índices das fatias sorteadas, na ordem de revelação
        self.revelados = 0
        self.inicio = 0  # selo aceso quando o giro atual começou
        self.aceso = 0
        self.escolhida: int | None = None
        self.cursor_escolha = 0  # para jogar de controle: ← → e confirmar
        self.carma_visual = mesa.carma.valor  # o que a tela mostra; acompanha a Mesa no fim do giro
        ordem = list(range(ELOS))
        random.Random(7).shuffle(ordem)  # elos racham numa ordem fixa, espalhada pela corrente
        self.ordem_rachaduras = ordem
        self.cartas = Cartas(sobe=28, lado=True)  # as opções do modo "escolha"
        self.apressar = False  # Enter durante o giro: o resultado já está decidido, pula
        self._pistas: tuple = (None, [])  # (o giro, os selos de combo das opções dele)

    segurar_saida = 0.0

    def animar(self, dt: float) -> None:
        """Só o enfeite anda (a transição chama quando esta tela está saindo)."""
        self.relogio += dt
        self.t += dt
        self.cartas.avancar(dt, self.cursor_escolha, len(self.alvos))

    def assentar(self) -> None:
        """As opções já no lugar (capturas de tela)."""
        self.cartas.avancar(10.0, self.cursor_escolha, len(self.alvos))

    @property
    def jornada(self) -> bool:
        return self.girar_fn is not None

    @property
    def roda(self):
        return self.mesa.rodas[ORDEM_RODAS[self.i_roda]]

    # ------------------------------------------------------------- lógica

    def _amostrar(self) -> list:
        """Os selos da mandala: a roda inteira, ou uma amostra fixa com todas as raridades."""
        fatias = list(self.roda.fatias)
        if len(fatias) <= MAX_SELOS:
            return fatias
        rng = random.Random(self.roda.id)
        por_raridade = {
            r.id: [f for f in fatias if f.raridade == r.id] for r in self.mesa.raridades
        }
        escolha = []
        for lista in por_raridade.values():  # ao menos um selo de cada raridade
            if lista:
                escolha.append(rng.choice(lista))
        resto = [f for f in fatias if f not in escolha]
        escolha += rng.sample(resto, MAX_SELOS - len(escolha))
        rng.shuffle(escolha)
        return escolha

    def _incluir(self, sorteadas) -> None:
        """Garante as fatias sorteadas na mandala, trocando selos que não foram sorteados."""
        ids = {f.id for f in sorteadas}
        livres = [i for i, f in enumerate(self.selos) if f.id not in ids]
        rng = random.Random(len(self.selos) + sum(len(i) for i in ids))
        rng.shuffle(livres)
        for f in sorteadas:
            if all(x.id != f.id for x in self.selos):
                self.selos[livres.pop()] = f

    def _ir(self, estado: str) -> None:
        self.estado = estado
        self.t = 0.0
        if estado == "escolhendo":  # as opções entram uma a uma
            self.cartas = Cartas(sobe=28, lado=True)

    def _duracao(self) -> float:
        if len(self.alvos) > 1:
            return DURACAO_SUBGIRO
        return DURACAO_GIRO * (1.3 if self.giro and self.giro.despertar else 1.0)

    def _comecar_giro(self) -> None:
        self.giro = self.girar_fn() if self.jornada else self.mesa.girar(self.roda.id)
        self._incluir(self.giro.fatias)
        ids = [f.id for f in self.selos]
        self.alvos = [ids.index(f.id) for f in self.giro.fatias]
        self.revelados = 0
        self.inicio = self.aceso
        self.escolhida = None
        self.apressar = False
        if self.giro.despertar:
            som.tocar("despertar")
            som.tocar("corrente")
        self._ir("quebrando" if self.giro.despertar else "girando")

    def _indice_girando(self) -> int:
        n = len(self.selos)
        alvo = self.alvos[self.revelados]
        voltas = 1 if len(self.alvos) > 1 else VOLTAS
        passos = voltas * n + (alvo - self.inicio) % n
        return (self.inicio + int(passos * _ease_out(min(self.t / self._duracao(), 1.0)))) % n

    def update(self, world, delta_time: float) -> None:
        self.cartas.avancar(delta_time, self.cursor_escolha, len(self.alvos))
        delta_time *= OPCOES.velocidade  # a velocidade das animações, das opções
        self.relogio += delta_time
        self.t += delta_time
        e = self.entrada
        som.musica("roleta")
        if e.is_action_pressed("sair"):
            self.ao_sair()
            return
        if self.estado in ("quebrando", "girando") and e.is_action_pressed("confirmar"):
            self.apressar = True  # o sorteio já foi feito: o giro é só espetáculo

        if self.jornada:
            if self.estado == "parado" and e.is_action_pressed("girar"):
                self._comecar_giro()
                return
            if self.estado == "resultado" and e.is_action_pressed("confirmar"):
                self.ao_concluir(self.escolhida or 0)
                return
            if self.estado not in ("quebrando", "girando", "escolhendo"):
                return

        if self.estado in ("parado", "resultado"):
            if e.is_action_pressed("trocar_roda"):
                self.i_roda = (self.i_roda + 1) % len(ORDEM_RODAS)
                self.giro, self.aceso = None, 0
                self.selos = self._amostrar()
                self._ir("parado")
            elif e.is_action_pressed("sofrer_dano"):
                self.mesa.carma.registrar_dano(0.25)
                self.carma_visual = self.mesa.carma.valor
            elif e.is_action_pressed("pagar_custo"):
                self.mesa.carma.registrar_custo()
                self.carma_visual = self.mesa.carma.valor
            elif e.is_action_pressed("girar"):
                self._comecar_giro()

        elif self.estado == "quebrando":
            if self.t >= DURACAO_QUEBRA or self.apressar:
                self.carma_visual = self.mesa.carma.valor
                self._ir("girando")

        elif self.estado == "girando":
            if self.apressar:
                self.t = max(self.t, self._duracao())
            novo = self._indice_girando()
            if novo != self.aceso:
                som.tocar("tique")  # o selo aceso passa para o próximo
            self.aceso = novo
            if self.t >= self._duracao():
                self.aceso = self.alvos[self.revelados]
                som.tocar("parar")
                self.revelados += 1
                if self.revelados < len(self.alvos):
                    self.inicio = self.aceso
                    self._ir("girando")
                else:
                    self.carma_visual = self.mesa.carma.valor
                    ordem = [r.id for r in self.mesa.raridades]
                    melhor = max((f.raridade for f in self.giro.fatias), key=ordem.index)
                    som.tocar(f"revela_{melhor}")
                    if len(self.alvos) > 1:
                        self._ir("escolhendo")
                    else:
                        self.escolhida = 0
                        self._ir("resultado")

        elif self.estado == "escolhendo":
            n = len(self.alvos)
            if e.is_action_pressed("esquerda") or e.is_action_pressed("cima"):
                self.cursor_escolha = (self.cursor_escolha - 1) % n
                self.aceso = self.alvos[self.cursor_escolha]
                som.tocar("mover")
            elif e.is_action_pressed("direita") or e.is_action_pressed("baixo"):
                self.cursor_escolha = (self.cursor_escolha + 1) % n
                self.aceso = self.alvos[self.cursor_escolha]
                som.tocar("mover")
            for i in range(n):
                apertou = e.is_action_pressed(f"escolher_{i + 1}")
                if apertou or (e.is_action_pressed("confirmar") and i == self.cursor_escolha):
                    som.tocar("confirmar")
                    self.escolhida = i
                    self.cursor_escolha = i
                    self.cartas.escolher(i)  # a escolhida carimba antes do resultado
                    self.aceso = self.alvos[i]
                    self._ir("resultado")
                    break

    # ------------------------------------------------------------- desenho

    def render(self, world, renderer: IRenderer) -> None:
        r = renderer
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        self._fundo(r)
        self._enso(r)
        self._corrente(r)
        self._rastro(r)
        self._mandala(r)
        self._revelacao(r)
        self._centro(r)
        if self.jornada:
            self._texto(r, 36, 16, f"{self.roda.kanji} {self.titulo or self.roda.nome}", 26, TINTA)
        else:
            self._abas(r)
        self._painel(r)
        self._controles(r)
        self._despertar(r)
        vfx.vinheta(r, 0.8)
        vfx.grao(r, self.relogio, 120)
        transicoes.revelar(self, r, self.relogio)

    def _texto(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

    def _nome(self, r: IRenderer, x, y, texto, tam, cor, largura, anchor="topleft") -> None:
        """Um nome que encolhe para caber em `largura` (os longos não vazam da carta)."""
        self._texto(r, x, y, texto, tam_que_cabe(texto, tam, largura), cor, anchor)

    def _fundo(self, r: IRenderer) -> None:
        """O santuário da roda: luz de sangue, incenso, um anel de kanji e correntes do alto."""
        cx, cy = CENTRO
        t = self.relogio
        frac = min(1.0, self.carma_visual / self.mesa.carma.config.maximo)
        for k in range(8):  # a luz cresce com o Carma
            r.draw_ui_circle(
                cx, cy, 330 - k * 26, _alpha((110, 12, 16, 255), (5 + k * 2) * (0.6 + frac))
            )
        fatias = self.roda.fatias
        for i in range(36):  # um anel de kanji girando devagar, ao fundo
            a = 2 * math.pi * i / 36 + t * 0.03
            f = fatias[i % len(fatias)]
            self._texto(
                r,
                cx + math.cos(a) * 300,
                cy + math.sin(a) * 300,
                f.kanji,
                15,
                _alpha(TINTA, 18),
                "center",
            )
        for k in range(3):  # fumaça de incenso subindo dos dois lados
            for j in range(6):
                fase = (t * 0.12 + j / 6 + k * 0.33) % 1.0
                x = (40 if k % 2 else 660) + math.sin(fase * 6 + k) * 18 + k * 8
                y = ALTURA - fase * (ALTURA - 40)
                r.draw_ui_circle(x, y, 6 + fase * 22, _alpha(TINTA, 10 * (1 - fase)))
        for x in (24, 646):  # correntes pendendo do alto
            for j in range(9):
                y = 4 + j * 16 + math.sin(t * 1.1 + x) * 2
                if j % 2 == 0:
                    r.draw_ui_circle(x, y, 5, _alpha(FERRO, 90), 2)
                else:
                    r.draw_ui_line(x, y - 7, x, y + 7, _alpha(FERRO, 90), 3)

    def _rastro(self, r: IRenderer) -> None:
        """Enquanto gira, o selo aceso deixa um rastro nos selos por onde passou."""
        if self.estado != "girando":
            return
        n = len(self.selos)
        for k in range(1, 5):
            x, y = self._pos_selo((self.aceso - k) % n, n)
            r.draw_ui_circle(x, y, RAIO_SELO + 12 - k * 2, _alpha(TINTA, 46 - k * 10))

    def _revelacao(self, r: IRenderer) -> None:
        """O momento em que o selo para: cada raridade se revela do seu jeito."""
        f = self._escolhida() if self.estado == "resultado" else None
        if f is None or self.t > 1.4:
            return
        k = self.t / 1.4
        n = len(self.selos)
        x, y = self._pos_selo(self.aceso, n)
        cor = self.cores[f.raridade]
        ordem = [rr.id for rr in self.mesa.raridades]
        nivel = ordem.index(f.raridade)
        if nivel == 0:  # cinza: uma onda de tinta
            r.draw_ui_circle(x, y, RAIO_SELO + 60 * k, _alpha(TINTA, 120 * (1 - k)), 2)
        elif nivel == 1:  # sangue: um respingo
            for i in range(10):
                a = i * 0.63 + 0.4
                d = RAIO_SELO + 70 * _ease_out(k)
                r.draw_ui_circle(
                    x + math.cos(a) * d,
                    y + math.sin(a) * d,
                    5 * (1 - k) + 2,
                    _alpha(cor, 230 * (1 - k)),
                )
            r.draw_ui_circle(x, y, RAIO_SELO + 30 * k, _alpha(cor, 150 * (1 - k)), 3)
        elif nivel == 2:  # maldito: fumaça roxa subindo em espiral
            for i in range(12):
                a = i * 0.52 + self.relogio * 2
                d = RAIO_SELO + 40 * k
                r.draw_ui_circle(
                    x + math.cos(a) * d,
                    y + math.sin(a) * d - 60 * k,
                    8 + 10 * k,
                    _alpha(cor, 120 * (1 - k)),
                )
        else:  # divino: um clarão e raios dourados que atravessam a mandala
            if k < 0.15:
                r.draw_ui_rect(0, 0, LARGURA, ALTURA, _alpha(OURO, 90 * (1 - k / 0.15)))
            for i in range(20):
                a = 2 * math.pi * i / 20 + self.relogio * 0.4
                r.draw_ui_line(
                    x + math.cos(a) * RAIO_SELO,
                    y + math.sin(a) * RAIO_SELO,
                    x + math.cos(a) * (RAIO_SELO + 240 * _ease_out(k)),
                    y + math.sin(a) * (RAIO_SELO + 240 * _ease_out(k)),
                    _alpha(OURO, 160 * (1 - k)),
                    2,
                )

    def _enso(self, r: IRenderer) -> None:
        """O círculo de pincel atrás da mandala: aberto, como no zen."""
        cx, cy = CENTRO
        r.draw_ui_arc(
            cx, cy, RAIO_ENSO, math.radians(115), math.radians(440), _alpha(TINTA, 18), 14
        )
        r.draw_ui_arc(
            cx, cy, RAIO_ENSO - 7, math.radians(125), math.radians(420), _alpha(TINTA, 26), 4
        )

    def _corrente(self, r: IRenderer) -> None:
        cx, cy = CENTRO
        cfg = self.mesa.carma.config
        frac = self.carma_visual / cfg.maximo
        cheio = self.carma_visual >= cfg.maximo
        pity = self.carma_visual > cfg.pity_suave_inicio
        pulso = 0.5 + 0.5 * math.sin(self.relogio * 6)
        rachados = set(self.ordem_rachaduras[: round(frac * ELOS)])
        quebra = self.estado == "quebrando"
        k = _ease_out(min(self.t / DURACAO_QUEBRA, 1.0)) if quebra else 0.0

        for i in range(ELOS):
            a = 2 * math.pi * i / ELOS
            raio = RAIO_CORRENTE
            if cheio and not quebra:
                a += math.sin(self.relogio * 40 + i) * 0.004
                raio += math.sin(self.relogio * 35 + i * 1.7) * 1.5
            cor = FERRO
            if cheio:
                cor = _mistura(FERRO, SANGUE_VIVO, 0.65 + 0.35 * pulso)
            elif pity:
                cor = _mistura(FERRO, SANGUE_VIVO, 0.2 + 0.25 * pulso)
            if quebra:
                raio += k * (160 + (i * 37) % 90)
                a += k * (((i * 13) % 7) - 3) * 0.03
                cor = _alpha(_mistura(cor, OURO, k), 255 * (1 - k))
                if cor[3] == 0:
                    continue

            ca, sa = math.cos(a), math.sin(a)
            px, py = cx + raio * ca, cy + raio * sa
            tx, ty = -sa, ca  # tangente
            comp = 2 * math.pi * raio / ELOS
            if i % 2 == 0:  # elo de frente: um anel alongado
                self._elo(r, px, py, tx, ty, ca, sa, comp * 0.62, 10, cor, 2)
            else:  # elo de lado: só uma barra fina
                self._elo(r, px, py, tx, ty, ca, sa, comp * 0.75, 3.5, cor, 0)
            if i in rachados and not quebra:
                rc = _alpha(SANGUE_VIVO, 230)
                r.draw_ui_line(
                    px - ca * 6 + tx * 2, py - sa * 6 + ty * 2, px + tx * -1, py + ty * -1, rc, 2
                )
                r.draw_ui_line(
                    px + tx * -1, py + ty * -1, px + ca * 6 - tx * 2, py + sa * 6 - ty * 2, rc, 2
                )

    @staticmethod
    def _elo(r, px, py, tx, ty, nx, ny, comp, larg, cor, espessura) -> None:
        h, w = comp / 2, larg / 2
        pontos = [
            (px - tx * h, py - ty * h),
            (px - tx * (h - w) + nx * w, py - ty * (h - w) + ny * w),
            (px + tx * (h - w) + nx * w, py + ty * (h - w) + ny * w),
            (px + tx * h, py + ty * h),
            (px + tx * (h - w) - nx * w, py + ty * (h - w) - ny * w),
            (px - tx * (h - w) - nx * w, py - ty * (h - w) - ny * w),
        ]
        r.draw_ui_polygon(pontos, cor, espessura)

    def _pos_selo(self, i: int, n: int) -> tuple[float, float]:
        a = -math.pi / 2 + 2 * math.pi * i / n  # começa no topo, segue no sentido horário
        return CENTRO[0] + RAIO_SELOS * math.cos(a), CENTRO[1] + RAIO_SELOS * math.sin(a)

    def _mandala(self, r: IRenderer) -> None:
        cx, cy = CENTRO
        fatias = self.selos
        n = len(fatias)
        r.draw_ui_circle(cx, cy, RAIO_SELOS - 52, _alpha(TINTA, 35), 1)
        r.draw_ui_circle(cx, cy, RAIO_SELOS, _alpha(TINTA, 25), 1)
        for i in range(n):
            x, y = self._pos_selo(i, n)
            a = math.atan2(y - cy, x - cx)
            r.draw_ui_line(
                cx + (RAIO_SELOS - 52) * math.cos(a),
                cy + (RAIO_SELOS - 52) * math.sin(a),
                x - RAIO_SELO * math.cos(a),
                y - RAIO_SELO * math.sin(a),
                _alpha(TINTA, 30),
            )

        rastro: dict[int, float] = {}
        if self.estado == "girando":
            for passo, forca in enumerate((90, 50, 22), start=1):
                rastro[(self.aceso - passo) % n] = forca
        marcados = (
            set(self.alvos[: self.revelados]) if self.estado in ("girando", "escolhendo") else set()
        )
        acesos = set()
        if self.estado in ("girando", "resultado"):
            acesos.add(self.aceso)

        for i, f in enumerate(fatias):
            x, y = self._pos_selo(i, n)
            cor = self.cores[f.raridade]
            clara = self.cores_claras[f.raridade]
            if i in acesos:
                r.draw_ui_circle(x, y, RAIO_SELO + 16, _alpha(cor, 45))
                r.draw_ui_circle(x, y, RAIO_SELO + 8, _alpha(cor, 90))
                r.draw_ui_circle(x, y, RAIO_SELO, clara)
                self._texto(r, x, y - 2, f.kanji, 30, FUNDO, "center")
                continue
            if i in rastro:
                r.draw_ui_circle(x, y, RAIO_SELO + 8, _alpha(cor, rastro[i]))
            if i in marcados:
                r.draw_ui_circle(x, y, RAIO_SELO + 10, _alpha(cor, 80))
                fora = math.atan2(y - CENTRO[1], x - CENTRO[0])
                numero = self.alvos.index(i) + 1
                self._texto(
                    r,
                    x + 44 * math.cos(fora),
                    y + 44 * math.sin(fora),
                    str(numero),
                    20,
                    clara,
                    "center",
                )
            r.draw_ui_circle(x, y, RAIO_SELO, LACA)
            r.draw_ui_circle(x, y, RAIO_SELO, cor, 3 if i in marcados else 2)
            kanji_cor = TINTA if f.raridade == self.mesa.ordem[0] else clara
            self._texto(r, x, y - 2, f.kanji, 30, kanji_cor, "center")

    def _escolhida(self):
        if self.giro is None or self.escolhida is None:
            return None
        return self.giro.fatias[self.escolhida]

    def _centro(self, r: IRenderer) -> None:
        cx, cy = CENTRO
        if self.estado == "quebrando":
            return  # o centro é do 覚醒
        f = self._escolhida() if self.estado == "resultado" else None
        if f is None:
            self._texto(r, cx, cy - 14, self.roda.kanji, 110, _alpha(TINTA, 210), "center")
            self._texto(r, cx, cy + 62, self.roda.nome, 24, _alpha(TINTA, 150), "center")
            return
        cor = self.cores_claras[f.raridade]
        if self.giro and self.giro.despertar:
            for k in range(16):  # raios dourados
                a = 2 * math.pi * k / 16 + self.relogio * 0.2
                r.draw_ui_line(
                    cx + 70 * math.cos(a),
                    cy + 70 * math.sin(a),
                    cx + 128 * math.cos(a),
                    cy + 128 * math.sin(a),
                    _alpha(OURO, 90),
                    2,
                )
        self._texto(r, cx, cy - 18, f.kanji, 104, cor, "center")
        self._nome(r, cx, cy + 56, f.nome, 24, TINTA, 230, "center")
        self._texto(r, cx, cy + 86, self.nomes_raridade[f.raridade], 18, cor, "center")

    def _abas(self, r: IRenderer) -> None:
        x = 36
        for k, rid in enumerate(ORDEM_RODAS):
            roda = self.mesa.rodas[rid]
            largura = (
                44 + len(roda.nome) * 12
            )  # o renderer não mede texto; estimativa da fonte de pincel
            atual = k == self.i_roda
            cor = TINTA if atual else _alpha(TINTA, 90)
            self._texto(r, x, 14, roda.kanji, 30, cor)
            self._texto(r, x + 40, 22, roda.nome, 20, cor)
            if atual:
                r.draw_ui_line(x, 54, x + largura, 54, SANGUE_VIVO, 2)
            x += largura + 34

    def _painel(self, r: IRenderer) -> None:
        x = 700
        cfg = self.mesa.carma.config
        valor = self.carma_visual
        self._texto(r, x, 92, "業", 46, OURO)
        self._texto(r, x + 56, 98, "Carma", 24, TINTA)
        self._texto(r, x + 56, 126, f"{valor:.0f} / {cfg.maximo:.0f}", 20, _alpha(TINTA, 170))
        if valor >= cfg.maximo:
            aviso, cor = "transbordando: o próximo giro desperta", SANGUE_VIVO
        elif valor > cfg.pity_suave_inicio:
            aviso, cor = (
                "as correntes cedem: raridades altas sobem",
                _mistura(FERRO, SANGUE_VIVO, 0.6),
            )
        else:
            aviso, cor = "", TINTA
        for j, linha in enumerate(_quebrar(aviso, 26)):
            self._texto(r, x, 160 + j * 20, linha, 16, cor)

        cartao = self._cartao() if self.estado == "resultado" else None
        if cartao is None or cartao.topo >= TOPO_CARTAO:  # o texto longo sobe por cima das Taxas
            self._taxas(r, x)
        if self.giro and (self.estado == "escolhendo" or self._carimbando()):
            self._opcoes(r, x, TOPO_CARTAO)
        elif cartao is not None:
            surge = 1.0
            if len(self.alvos) > 1:  # depois do carimbo, o cartão do resultado aparece
                surge = suave((self.t - Cartas.CARIMBO) / 0.22)
            self._resultado(Camada(r, (x, cartao.topo), 1.0, 0, 10 * (1 - surge), surge), x, cartao)

    def _carimbando(self) -> bool:
        return (
            self.estado == "resultado"
            and len(self.alvos) > 1
            and self.cartas.escolhida is not None
            and self.t < Cartas.CARIMBO
        )

    def _taxas(self, r: IRenderer, x: int) -> None:
        self._texto(r, x, 218, "Taxas", 20, TINTA)
        self._texto(r, x + 246, 222, "publicada · agora", 14, _alpha(TINTA, 120), "topright")
        for j, (rid, (pub, agora)) in enumerate(self.mesa.taxas().items()):
            y = 252 + j * 28
            r.draw_ui_circle(x + 7, y + 10, 6, self.cores[rid])
            self._texto(r, x + 22, y, self.nomes_raridade[rid], 18, TINTA)
            subiu = agora > pub + 0.05
            cor_agora = self.cores_claras[rid] if subiu else _alpha(TINTA, 150)
            self._texto(r, x + 160, y, _pct(pub), 17, _alpha(TINTA, 150), "topright")
            self._texto(r, x + 168, y, "→", 17, _alpha(TINTA, 100))
            self._texto(r, x + 246, y, _pct(agora), 17, cor_agora, "topright")

    def pistas(self) -> list[str]:
        """O selo de combo de cada opção do giro de Técnicas (vazio: nenhum). Só na Jornada."""
        if self.j is None or self.giro is None or self.roda.id != "tecnicas":
            return []
        if self._pistas[0] is not self.giro:
            from karmabound.grimorio import pista
            from karmabound.tela_menus import texto_da_pista

            e, fusoes, grim = self.j.estado, self.j.ctx.fusoes, self.j.grimorio
            textos = [
                texto_da_pista(pista(e, f.id, fusoes), grim, LARGURA_SELO) for f in self.giro.fatias
            ]
            self._pistas = (self.giro, textos)
        return self._pistas[1]

    def _opcoes(self, r: IRenderer, x: int, y: int) -> None:
        if self.giro:
            pistas = self.pistas()
            sai = 1 - self.cartas.u_carimbo()
            self._texto(r, x, y, "Escolha uma técnica", 20, _alpha(TINTA, 255 * sai))
            tela = r
            for j, f in enumerate(self.giro.fatias):
                cor = self.cores_claras[f.raridade]
                yj = y + 34 + j * 52
                foco = self.cartas.foco_de(j)
                r = self.cartas.camada(tela, j, (x + 118, yj + 14))
                if foco > 0.02:  # o destaque desliza entre as opções
                    r.draw_ui_rect(x - 10, yj - 8, 256, 46, _alpha(TINTA, 10 + 16 * foco))
                    r.draw_ui_rect(x - 10, yj - 8, 3, 46, _alpha(cor, 230 * foco))
                self._texto(r, x, yj, f"{j + 1}", 20, _alpha(TINTA, 140))
                self._texto(r, x + 22 + 4 * foco, yj - 4, f.kanji, 26, cor)
                self._nome(r, x + 58 + 4 * foco, yj, f.nome, 18, cor, 190)
                selo = pistas[j] if j < len(pistas) else ""
                if selo:  # 融 peça de uma fusão · 共 forma ou avança uma Ressonância
                    tam = tam_que_cabe(selo, 13, 190)
                    self._texto(r, x + 58, yj + 22, selo, tam, _alpha(OURO, 230))
                elif f.origem:
                    obra = f.origem.split(" · ")[-1]
                    self._texto(r, x + 58, yj + 22, f"※ {obra}", 13, _alpha(TINTA, 110))
                if j == self.cartas.escolhida:
                    self.cartas.selo(tela, x + 6, yj + 12, "決", 20)  # sobre o número

    def _cartao(self) -> _Cartao | None:
        """Onde e em que letra cabe o resultado inteiro: no lugar de sempre se couber; se não,
        o cartão sobe por cima das Taxas e, no limite, a letra diminui. Nada fica cortado."""
        f = self._escolhida()
        if f is None:
            return None
        despertar = 26 if self.giro and self.giro.despertar else 0  # o título do Despertar
        origem = _quebrar(f"※ {f.origem}", 26)[:2] if f.origem else []
        for tam, largura, passo in LETRAS_CARTAO:
            linhas = _quebrar(f.texto, largura)
            altura = despertar + 62 + len(linhas) * passo + 18 * len(origem)
            topo = min(TOPO_CARTAO, FUNDO_CARTAO - altura)
            if topo >= TOPO_MAXIMO_CARTAO:
                return _Cartao(f, topo, linhas, tam, passo, origem)
        sobra = (FUNDO_CARTAO - TOPO_MAXIMO_CARTAO - despertar - 62 - 18 * len(origem)) // passo
        linhas = linhas[:sobra]
        linhas[-1] = linhas[-1].rstrip(" ,.;:") + "…"  # só se nem a letra menor couber
        return _Cartao(f, TOPO_MAXIMO_CARTAO, linhas, tam, passo, origem)

    def _resultado(self, r: IRenderer, x: int, c: _Cartao) -> None:
        f, y = c.fatia, c.topo
        if self.giro and self.giro.despertar:
            self._texto(r, x, y - 6, "覚醒  Despertar", 22, OURO)
            y += 26
        divina = f.raridade == self.mesa.raridades[-1].id
        moldura(r, x - 14, y - 12, LARGURA - 14, ALTURA - 64, self.cores[f.raridade], divina)
        self._nome(r, x, y, f.nome, 24, self.cores_claras[f.raridade], LARGURA - 42 - x)
        self._texto(r, x, y + 30, self.nomes_raridade[f.raridade], 16, self.cores[f.raridade])
        for j, linha in enumerate(c.linhas):
            self._texto(r, x, y + 56 + j * c.passo, linha, c.tam, TINTA)
        yo = y + 62 + len(c.linhas) * c.passo
        for j, linha in enumerate(c.origem):
            self._texto(r, x, yo + j * 18, linha, 13, _alpha(OURO, 190))

    def _controles(self, r: IRenderer) -> None:
        if self.jornada:
            dica = {
                "parado": "espaço gira",
                "escolhendo": "1–3, ou ← → e Enter",
                "resultado": "Enter continua",
            }.get(self.estado, "")
            linhas = [dica, "esc sai"]
        else:
            linhas = ["espaço girar · tab trocar roda", "D dano · C custo · esc sair"]
        for j, linha in enumerate(linhas):
            self._texto(r, 700, ALTURA - 52 + j * 22, linha, 14, _alpha(TINTA, 110))

    def _despertar(self, r: IRenderer) -> None:
        if self.estado != "quebrando":
            return
        k = self.t / DURACAO_QUEBRA
        if k < 0.25:
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, _alpha(OURO, 110 * (1 - k / 0.25)))
        cx, cy = CENTRO
        brilho = 255 * min(1.0, k * 3) * (1 - max(0.0, k - 0.7) / 0.3)
        self._texto(r, cx, cy - 16, "覚醒", 120, _alpha(OURO, brilho), "center")
        self._texto(r, cx, cy + 66, "DESPERTAR", 28, _alpha(OURO, brilho), "center")

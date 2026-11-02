"""Tela da roleta: a mandala de selos, as correntes do Carma e o Despertar.

Só apresentação: todo sorteio passa pela `Mesa`. A cena escolhe o alvo
antes de animar (o resultado já está decidido quando o selo começa a correr).
"""

from __future__ import annotations

import math
import random

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.mesa import Giro, Mesa
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

ORDEM_RODAS = ("destino", "tecnicas", "arco", "reliquias")


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
        self.i_roda = ORDEM_RODAS.index(roda_fixa) if roda_fixa else 0
        self.estado = "parado"  # parado | quebrando | girando | escolhendo | resultado
        self.t = 0.0  # tempo no estado atual
        self.relogio = 0.0  # tempo total, para pulsos
        self.giro: Giro | None = None
        self.alvos: list[int] = []  # índices das fatias sorteadas, na ordem de revelação
        self.revelados = 0
        self.inicio = 0  # selo aceso quando o giro atual começou
        self.aceso = 0
        self.escolhida: int | None = None
        self.carma_visual = mesa.carma.valor  # o que a tela mostra; acompanha a Mesa no fim do giro
        ordem = list(range(ELOS))
        random.Random(7).shuffle(ordem)  # elos racham numa ordem fixa, espalhada pela corrente
        self.ordem_rachaduras = ordem

    @property
    def jornada(self) -> bool:
        return self.girar_fn is not None

    @property
    def roda(self):
        return self.mesa.rodas[ORDEM_RODAS[self.i_roda]]

    # ------------------------------------------------------------- lógica

    def _ir(self, estado: str) -> None:
        self.estado = estado
        self.t = 0.0

    def _duracao(self) -> float:
        if len(self.alvos) > 1:
            return DURACAO_SUBGIRO
        return DURACAO_GIRO * (1.3 if self.giro and self.giro.despertar else 1.0)

    def _comecar_giro(self) -> None:
        self.giro = self.girar_fn() if self.jornada else self.mesa.girar(self.roda.id)
        ids = [f.id for f in self.roda.fatias]
        self.alvos = [ids.index(f.id) for f in self.giro.fatias]
        self.revelados = 0
        self.inicio = self.aceso
        self.escolhida = None
        if self.giro.despertar:
            som.tocar("despertar")
            som.tocar("corrente")
        self._ir("quebrando" if self.giro.despertar else "girando")

    def _indice_girando(self) -> int:
        n = len(self.roda.fatias)
        alvo = self.alvos[self.revelados]
        voltas = 1 if len(self.alvos) > 1 else VOLTAS
        passos = voltas * n + (alvo - self.inicio) % n
        return (self.inicio + int(passos * _ease_out(min(self.t / self._duracao(), 1.0)))) % n

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self.t += delta_time
        e = self.entrada
        som.musica("roleta")
        if e.is_action_pressed("sair"):
            self.ao_sair()
            return

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
            if self.t >= DURACAO_QUEBRA:
                self.carma_visual = self.mesa.carma.valor
                self._ir("girando")

        elif self.estado == "girando":
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
            for i in range(len(self.alvos)):
                if e.is_action_pressed(f"escolher_{i + 1}"):
                    som.tocar("confirmar")
                    self.escolhida = i
                    self.aceso = self.alvos[i]
                    self._ir("resultado")

    # ------------------------------------------------------------- desenho

    def render(self, world, renderer: IRenderer) -> None:
        r = renderer
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        self._enso(r)
        self._corrente(r)
        self._mandala(r)
        self._centro(r)
        if self.jornada:
            self._texto(r, 36, 16, f"{self.roda.kanji} {self.titulo or self.roda.nome}", 26, TINTA)
        else:
            self._abas(r)
        self._painel(r)
        self._controles(r)
        self._despertar(r)
        vfx.revelar(r, self.relogio)

    def _texto(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

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
        fatias = self.roda.fatias
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
        self._texto(r, cx, cy + 56, f.nome, 24, TINTA, "center")
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

        y = 380
        if self.estado == "escolhendo" and self.giro:
            self._texto(r, x, y, "Escolha uma técnica", 20, TINTA)
            for j, f in enumerate(self.giro.fatias):
                cor = self.cores_claras[f.raridade]
                yj = y + 34 + j * 52
                self._texto(r, x, yj, f"{j + 1}", 20, _alpha(TINTA, 140))
                self._texto(r, x + 22, yj - 4, f.kanji, 26, cor)
                self._texto(r, x + 58, yj, f.nome, 18, cor)
                if f.origem:
                    obra = f.origem.split(" · ")[-1]
                    self._texto(r, x + 58, yj + 22, f"※ {obra}", 13, _alpha(TINTA, 110))
            return
        f = self._escolhida() if self.estado == "resultado" else None
        if f is None:
            return
        if self.giro and self.giro.despertar:
            self._texto(r, x, y - 6, "覚醒  Despertar", 22, OURO)
            y += 26
        divina = f.raridade == self.mesa.raridades[-1].id
        moldura(r, x - 14, y - 12, LARGURA - 14, ALTURA - 64, self.cores[f.raridade], divina)
        self._texto(r, x, y, f.nome, 24, self.cores_claras[f.raridade])
        self._texto(r, x, y + 30, self.nomes_raridade[f.raridade], 16, self.cores[f.raridade])
        linhas = _quebrar(f.texto, 24)[:5]
        for j, linha in enumerate(linhas):
            self._texto(r, x, y + 56 + j * 21, linha, 16, TINTA)
        if f.origem:
            yo = y + 62 + len(linhas) * 21
            for j, linha in enumerate(_quebrar(f"※ {f.origem}", 28)[:2]):
                self._texto(r, x, yo + j * 18, linha, 13, _alpha(OURO, 190))

    def _controles(self, r: IRenderer) -> None:
        if self.jornada:
            dica = {
                "parado": "espaço gira",
                "escolhendo": "1, 2 ou 3 escolhe",
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

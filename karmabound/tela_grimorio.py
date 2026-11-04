"""Tela do Grimório: todas as habilidades, roda por roda, com a homenagem de cada uma.

O que ainda não saiu da roleta aparece como ???. À esquerda a lista; à direita
a carta da habilidade, com a moldura da raridade e a origem.
"""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.grimorio import Grimorio
from karmabound.run import Contexto
from karmabound.tela_menus import _Base
from karmabound.visual import (
    ALTURA,
    FERRO,
    LACA,
    LARGURA,
    OURO,
    TINTA,
    alpha,
    hex_cor,
    mistura,
    moldura,
    quebrar,
)

ORDEM_RODAS = ("linhagem", "destino", "tecnicas", "arco", "reliquias", "despertar", "chefes")
NOMES_ABA = {"chefes": ("魔", "Chefes")}  # abas que não são rodas
LINHA = 22
TOPO_LISTA = 118
VISIVEIS = 20  # linhas da lista na tela; o resto rola


@dataclass(frozen=True)
class Entrada:
    id: str
    nome: str
    kanji: str
    raridade: str
    texto: str
    origem: str


def entradas(ctx: Contexto) -> dict[str, list[Entrada]]:
    """As habilidades de cada roda, na ordem da roda (o Golpe abre as Técnicas)."""
    por_roda = {}
    for rid in ORDEM_RODAS:
        fatias = ctx.chefes if rid == "chefes" else ctx.rodas[rid].fatias
        por_roda[rid] = [
            Entrada(f.id, f.nome, f.kanji, f.raridade, f.texto, f.origem) for f in fatias
        ]
    basico = ctx.combate["golpe_basico"]
    golpe = Entrada(
        basico["id"],
        basico["nome"],
        "打",
        "cinza",
        f"{basico['dano']} de dano, e nunca entra em recarga. Todo lutador tem.",
        basico.get("origem", ""),
    )
    por_roda["tecnicas"].insert(0, golpe)
    return por_roda


class GrimorioScene(_Base):
    def __init__(
        self, grimorio: Grimorio, entrada, ao_voltar, ao_sair, ctx: Contexto | None = None
    ):
        super().__init__(entrada, ao_sair)
        self.grimorio = grimorio
        self.ao_voltar = ao_voltar
        self.ctx = ctx or Contexto.padrao()
        self.por_roda = entradas(self.ctx)
        self.cores = {r.id: hex_cor(r.cor) for r in self.ctx.raridades}
        self.nomes_raridade = {r.id: r.nome for r in self.ctx.raridades}
        self.i_roda = 0
        self.cursor = 0
        self.topo = 0  # a primeira linha visível da lista

    @property
    def lista(self) -> list[Entrada]:
        return self.por_roda[ORDEM_RODAS[self.i_roda]]

    def _visto(self, e: Entrada) -> bool:
        return e.id == "golpe_basico" or self.grimorio.viu(e.id)

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        if self._sair():
            return
        e = self.entrada
        som.musica("titulo")
        if e.is_action_pressed("cancelar"):
            self.ao_voltar()
            return
        antes = (self.i_roda, self.cursor)
        if e.is_action_pressed("esquerda"):
            self.i_roda, self.cursor = (self.i_roda - 1) % len(ORDEM_RODAS), 0
        elif e.is_action_pressed("direita"):
            self.i_roda, self.cursor = (self.i_roda + 1) % len(ORDEM_RODAS), 0
        elif e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(self.lista)
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(self.lista)
        if (self.i_roda, self.cursor) != antes:
            som.tocar("mover")
        if self.cursor < self.topo:
            self.topo = self.cursor
        elif self.cursor >= self.topo + VISIVEIS:
            self.topo = self.cursor - VISIVEIS + 1

    # --------------------------------------------------------------- desenho

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        total = sum(len(v) for v in self.por_roda.values())
        vistas = sum(self._visto(e) for v in self.por_roda.values() for e in v)
        self._t(r, 36, 22, "書", 34, OURO)
        self._t(r, 80, 28, "Grimório", 24, TINTA)
        self._t(
            r, LARGURA - 36, 30, f"{vistas} / {total} vistas", 16, alpha(TINTA, 140), "topright"
        )
        self._abas(r)
        self._lista(r)
        self._carta(r, self.lista[self.cursor])
        self._t(
            r,
            LARGURA / 2,
            ALTURA - 26,
            "← → roda · ↑ ↓ habilidade · Backspace volta",
            14,
            alpha(TINTA, 100),
            "center",
        )
        vfx.revelar(r, self.relogio)

    def _abas(self, r: IRenderer) -> None:
        x = 36
        for k, rid in enumerate(ORDEM_RODAS):
            kanji, nome = NOMES_ABA.get(rid) or (
                self.ctx.rodas[rid].kanji,
                self.ctx.rodas[rid].nome,
            )
            atual = k == self.i_roda
            cor = TINTA if atual else alpha(TINTA, 90)
            self._t(r, x, 70, f"{kanji} {nome}", 16, cor)
            largura = 28 + len(nome) * 9
            if atual:
                r.draw_ui_line(x, 94, x + largura, 94, OURO, 2)
            x += largura + 26

    def _lista(self, r: IRenderer) -> None:
        lista = self.lista
        if self.topo > 0:
            self._t(r, 58, TOPO_LISTA - 20, "↑ mais", 13, alpha(TINTA, 110))
        if self.topo + VISIVEIS < len(lista):
            self._t(r, 58, TOPO_LISTA + VISIVEIS * LINHA, "↓ mais", 13, alpha(TINTA, 110))
        for i in range(self.topo, min(len(lista), self.topo + VISIVEIS)):
            e = lista[i]
            y = TOPO_LISTA + (i - self.topo) * LINHA
            visto = self._visto(e)
            cor = self.cores.get(e.raridade, TINTA)
            if i == self.cursor:
                r.draw_ui_rect(30, y - 3, 400, LINHA, alpha(LACA, 255))
                r.draw_ui_polygon([(36, y + 4), (44, y + 9), (36, y + 14)], OURO)
            r.draw_ui_circle(58, y + 9, 5, cor if visto else alpha(FERRO, 160))
            if visto:
                self._t(r, 72, y, e.kanji, 17, mistura(cor, TINTA, 0.3))
                self._t(r, 98, y + 1, e.nome, 16, TINTA if i == self.cursor else alpha(TINTA, 170))
            else:
                self._t(r, 72, y, "？", 17, alpha(TINTA, 70))
                self._t(r, 98, y + 1, "???", 16, alpha(TINTA, 70))

    def _carta(self, r: IRenderer, e: Entrada) -> None:
        x0, y0, x1, y1 = 470, 110, 924, 592
        visto = self._visto(e)
        cor = self.cores.get(e.raridade, TINTA) if visto else FERRO
        r.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 235))
        moldura(r, x0, y0, x1, y1, cor, divina=visto and e.raridade == self.ctx.ordem[-1])
        cx = (x0 + x1) / 2
        if not visto:
            self._t(r, cx, 250, "？", 96, alpha(TINTA, 60), "center")
            self._t(r, cx, 350, "Ainda não saiu da roleta.", 18, alpha(TINTA, 110), "center")
            return
        self._t(r, cx, 196, e.kanji, 96, mistura(cor, TINTA, 0.25), "center")
        self._t(r, cx, 282, e.nome, 28, TINTA, "center")
        self._t(r, cx, 318, self.nomes_raridade.get(e.raridade, e.raridade), 16, cor, "center")
        y = 356
        for linha in quebrar(e.texto, 44)[:6]:
            self._t(r, cx, y, linha, 17, TINTA, "center")
            y += 24
        if e.origem:
            r.draw_ui_line(cx - 120, 528, cx + 120, 528, alpha(cor, 90), 1)
            for k, linha in enumerate(quebrar(f"※ {e.origem}", 46)[:2]):
                self._t(r, cx, 540 + k * 20, linha, 15, alpha(OURO, 200), "center")

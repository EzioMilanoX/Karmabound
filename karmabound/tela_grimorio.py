"""Tela do Grimório: todas as habilidades, roda por roda, com a homenagem de cada uma.

O que ainda não saiu da roleta aparece como ???; o que é de um anime que o Legado
ainda não abriu aparece selado (封). À esquerda a lista; à direita a carta da
habilidade, com a moldura da raridade, a origem e, nas técnicas, a Maestria.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes
from karmabound.aliados import carregar_aliados
from karmabound.fusoes import Fusao, nomes_dos_requisitos
from karmabound.grimorio import Grimorio, fusao_descoberta
from karmabound.legado import MAESTRIA, nivel_maestria
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

ORDEM_RODAS = (
    "linhagem",
    "destino",
    "tecnicas",
    "arco",
    "reliquias",
    "despertar",
    "chefes",
    "viloes",
    "fusoes",
    "aliados",
    "afixos",
)
NOMES_ABA = {  # abas que não são rodas
    "chefes": ("魔", "Chefes"),
    "viloes": ("鬼", "Vilões"),
    "fusoes": ("融", "Fusões"),
    "aliados": ("伴", "Aliados"),
    "afixos": ("強", "Afixos"),
}
# aba -> tipo da entrada
EXTRAS = {"fusoes": "fusao", "aliados": "aliado", "afixos": "afixo", "viloes": "vilao"}
PAPEL_DO_VILAO = {"tenente": 0, "chefe": 1, "final": 2, "secreto": 3}  # -> a cor
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
    tipo: str = ""  # "" (das rodas e chefes) | fusao | aliado | afixo
    fusao: Fusao | None = None  # a receita, numa entrada de fusão


def entradas_extras(ctx: Contexto) -> dict[str, list[Entrada]]:
    """O que se conhece fora da roleta: as fusões, os aliados e os afixos de elite."""
    ordem = ctx.ordem
    fusoes = [
        Entrada(
            f.id,
            f.fatia.nome,
            f.fatia.kanji,
            f.fatia.raridade,
            f.fatia.texto,
            f.fatia.origem,
            "fusao",
            f,
        )
        for f in ctx.fusoes
    ]
    aliados = [
        Entrada(a.id, a.nome, a.kanji, ordem[1], a.texto, a.origem, "aliado")
        for a in carregar_aliados()
    ]
    afixos = []
    if ctx.caminho is not None:
        afixos = [
            Entrada(a.id, a.nome, a.kanji, ordem[2], a.texto, "", "afixo")
            for a in ctx.caminho.afixos.values()
        ]
    viloes = []
    if ctx.elenco is not None:  # o bestiário: quem você já enfrentou
        ordem_papel = sorted(ctx.elenco.viloes, key=lambda v: (PAPEL_DO_VILAO[v.papel], v.anime))
        for v in ordem_papel:
            quem = f"{v.titulo[:1].upper()}{v.titulo[1:]}." if v.titulo else ""
            fala = f" “{v.fala('entrada')}”" if v.fala("entrada") else ""
            raridade = ordem[min(PAPEL_DO_VILAO[v.papel], len(ordem) - 1)]
            viloes.append(Entrada(v.id, v.nome, v.kanji, raridade, quem + fala, v.origem, "vilao"))
    return {"fusoes": fusoes, "aliados": aliados, "afixos": afixos, "viloes": viloes}


def entradas(ctx: Contexto) -> dict[str, list[Entrada]]:
    """As habilidades de cada roda, na ordem da roda (o Golpe abre as Técnicas)."""
    por_roda = {}
    for rid in ORDEM_RODAS:
        if rid in EXTRAS:
            continue
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
        self,
        grimorio: Grimorio,
        entrada,
        ao_voltar,
        ao_sair,
        ctx: Contexto | None = None,
        abertos: frozenset[str] | None = None,
        usos: Counter | None = None,
    ):
        """`ctx`: com as rodas inteiras. `abertos`: os animes que o Legado já abriu (None:
        todos); `usos`: técnica -> usos somados de todas as runs (a Maestria)."""
        super().__init__(entrada, ao_sair)
        self.grimorio = grimorio
        self.ao_voltar = ao_voltar
        self.ctx = ctx or Contexto.padrao()
        self.usos = usos or Counter()
        self.selados: set[str] = set()
        if abertos is not None:  # o que as rodas de agora não têm está selado
            nas_rodas = {
                f.id
                for roda in Contexto.padrao(abertos=abertos).rodas.values()
                for f in roda.fatias
            }
            self.selados = {
                f.id for roda in self.ctx.rodas.values() for f in roda.fatias
            } - nas_rodas
        self.por_roda = {**entradas(self.ctx), **entradas_extras(self.ctx)}
        self.cores = {r.id: hex_cor(r.cor) for r in self.ctx.raridades}
        self.nomes_raridade = {r.id: r.nome for r in self.ctx.raridades}
        self.i_roda = 0
        self.cursor = 0
        self.topo = 0  # a primeira linha visível da lista

    @property
    def lista(self) -> list[Entrada]:
        return self.por_roda[ORDEM_RODAS[self.i_roda]]

    def _visto(self, e: Entrada) -> bool:
        if e.tipo == "fusao":
            return e.fusao is not None and fusao_descoberta(self.grimorio, e.fusao)
        if e.tipo in ("aliado", "afixo"):
            return self.grimorio.conhece(f"{e.tipo}s", e.id)
        if e.tipo == "vilao":
            return self.grimorio.conhece("viloes", e.id)
        return e.id == "golpe_basico" or self.grimorio.viu(e.id)

    def _pista(self, e: Entrada) -> str:
        """De uma fusão ainda não descoberta: uma peça que você já viu na roleta."""
        if e.fusao is None:
            return ""
        nomes = nomes_dos_requisitos(e.fusao)
        for r, nome in zip(e.fusao.requisitos, nomes, strict=True):
            if any(self.grimorio.viu(i) for i in r.ids):
                return nome
        return ""

    def _selado(self, e: Entrada) -> bool:
        return not e.tipo and e.id in self.selados

    def _maestria(self, e: Entrada) -> tuple[int, str]:
        """(nível, 'maestria 12/20'), só nas técnicas que já foram usadas."""
        if ORDEM_RODAS[self.i_roda] != "tecnicas" or not self.usos.get(e.id):
            return 0, ""
        usos = self.usos[e.id]
        n = nivel_maestria(usos)
        if n >= len(MAESTRIA):
            return n, f"maestria plena · {usos} usos"
        return n, f"maestria {usos}/{MAESTRIA[n]}"

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
        transicoes.revelar(self, r, self.relogio)

    def _abas(self, r: IRenderer) -> None:
        """As abas: a atual com o nome; as outras só com o kanji (são dez)."""
        x = 36
        for k, rid in enumerate(ORDEM_RODAS):
            kanji, nome = NOMES_ABA.get(rid) or (
                self.ctx.rodas[rid].kanji,
                self.ctx.rodas[rid].nome,
            )
            atual = k == self.i_roda
            cor = TINTA if atual else alpha(TINTA, 110)
            texto = f"{kanji} {nome}" if atual else kanji
            self._t(r, x, 68, texto, 18 if not atual else 17, cor)
            largura = 28 + len(nome) * 10 if atual else 20
            if atual:
                r.draw_ui_line(x, 94, x + largura, 94, OURO, 2)
            x += largura + 22

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
            selado = self._selado(e)
            if visto:
                self._t(r, 72, y, e.kanji, 17, mistura(cor, TINTA, 0.3))
                self._t(r, 98, y + 1, e.nome, 16, TINTA if i == self.cursor else alpha(TINTA, 170))
                nivel, _ = self._maestria(e)
                if nivel:
                    self._t(r, 424, y + 1, "★" * nivel, 14, OURO, "topright")
                elif selado:
                    self._t(r, 424, y, "封", 15, alpha(TINTA, 90), "topright")
            elif selado:
                self._t(r, 72, y, "封", 17, alpha(TINTA, 60))
                self._t(r, 98, y + 1, "selado", 16, alpha(TINTA, 60))
            else:
                self._t(r, 72, y, "？", 17, alpha(TINTA, 70))
                texto = "???"
                if e.fusao is not None:
                    texto += f"  ·  {len(e.fusao.requisitos)} peças"
                self._t(r, 98, y + 1, texto, 16, alpha(TINTA, 70))

    def _carta(self, r: IRenderer, e: Entrada) -> None:
        x0, y0, x1, y1 = 470, 110, 924, 592
        visto = self._visto(e)
        cor = self.cores.get(e.raridade, TINTA) if visto else FERRO
        r.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 235))
        moldura(r, x0, y0, x1, y1, cor, divina=visto and e.raridade == self.ctx.ordem[-1])
        cx = (x0 + x1) / 2
        if not visto and self._selado(e):
            self._t(r, cx, 250, "封", 96, alpha(TINTA, 60), "center")
            self._t(r, cx, 340, "Selado — abre com Memória.", 18, alpha(TINTA, 110), "center")
            self._t(
                r,
                cx,
                370,
                "Cada run deixa Memória; ela abre animes novos.",
                14,
                alpha(TINTA, 80),
                "center",
            )
            return
        if not visto:
            self._t(r, cx, 250, "？", 96, alpha(TINTA, 60), "center")
            texto = {
                "fusao": "Uma fusão que você ainda não viu nascer.",
                "aliado": "Ainda não lutou do seu lado.",
                "afixo": "Ainda não apareceu numa elite.",
            }.get(e.tipo, "Ainda não saiu da roleta.")
            self._t(r, cx, 350, texto, 18, alpha(TINTA, 110), "center")
            if e.fusao is not None:
                n = len(e.fusao.requisitos)
                self._t(r, cx, 384, f"融  {n} peças", 17, alpha(OURO, 160), "center")
                pista = self._pista(e)
                linha = f"Uma delas: {pista}" if pista else "Nenhuma das peças saiu da roleta."
                self._t(r, cx, 414, linha, 15, alpha(TINTA, 120), "center")
            return
        self._t(r, cx, 196, e.kanji, 96, mistura(cor, TINTA, 0.25), "center")
        self._t(r, cx, 282, e.nome, 28, TINTA, "center")
        if e.fusao is not None:
            self._carta_fusao(r, e, cor, cx)
            return
        rotulo = self.nomes_raridade.get(e.raridade, e.raridade)
        if e.tipo == "aliado":
            rotulo = "Aliado · luta do seu lado"
        elif e.tipo == "afixo":
            rotulo = "Afixo de elite"
        nivel, maestria = self._maestria(e)
        if maestria:
            rotulo += f"  ·  {'★' * nivel}{' ' if nivel else ''}{maestria}"
        elif self._selado(e):
            rotulo += "  ·  封 selado nas rodas"
        self._t(r, cx, 318, rotulo, 16, cor, "center")
        y = 356
        for linha in quebrar(e.texto, 44)[:6]:
            self._t(r, cx, y, linha, 17, TINTA, "center")
            y += 24
        if e.origem:
            r.draw_ui_line(cx - 120, 528, cx + 120, 528, alpha(cor, 90), 1)
            for k, linha in enumerate(quebrar(f"※ {e.origem}", 46)[:2]):
                self._t(r, cx, 540 + k * 20, linha, 15, alpha(OURO, 200), "center")

    def _carta_fusao(self, r: IRenderer, e: Entrada, cor, cx: float) -> None:
        """A fusão descoberta: a raridade, a receita inteira, o texto e a origem."""
        rotulo = self.nomes_raridade.get(e.raridade, e.raridade)
        self._t(r, cx, 316, f"{rotulo}  ·  nasce de uma fusão", 15, cor, "center")
        receita = "  +  ".join(nomes_dos_requisitos(e.fusao))
        y = 344
        for linha in quebrar(f"融  {receita}", 46)[:2]:
            self._t(r, cx, y, linha, 16, alpha(OURO, 220), "center")
            y += 22
        y += 10
        for linha in quebrar(e.texto, 46)[: 5 if y < 400 else 4]:
            self._t(r, cx, y, linha, 16, TINTA, "center")
            y += 22
        if e.origem:
            r.draw_ui_line(cx - 120, 528, cx + 120, 528, alpha(cor, 90), 1)
            for k, linha in enumerate(quebrar(f"※ {e.origem}", 46)[:2]):
                self._t(r, cx, 540 + k * 20, linha, 15, alpha(OURO, 200), "center")

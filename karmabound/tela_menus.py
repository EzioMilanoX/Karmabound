"""Telas de menu da run: título, troca de técnica, Altar dos Votos e fim.

Todas leem e mexem só na `Jornada`; nenhuma decide regra. O Altar mede as
restrições contra o build do jogador (pode levar um ou dois segundos): a tela
desenha "o Altar pesa..." num quadro e mede no seguinte.
"""

from __future__ import annotations

import math
from collections import Counter

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.arenas import _particulas
from karmabound.combate import Tecnica
from karmabound.figuras import desenhar_lutador
from karmabound.jornada import Jornada, PropostaDeVoto
from karmabound.rodas import anime_de, carregar_balanceamento, carregar_raridades, carregar_rodas
from karmabound.rolagem import Rolagem
from karmabound.run import DESCRICAO_JOGO, JOGOS, animes_jogaveis
from karmabound.visual import (
    ALTURA,
    FERRO,
    FONTE_PINCEL,
    FUNDO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    alpha,
    hex_cor,
    mistura,
    quebrar,
)

DURACOES = ("luta", "capitulo", "run")
NOME_DURACAO = {
    "luta": "só esta luta",
    "capitulo": "até o fim do capítulo",
    "run": "o resto da run",
}
DURANTE = {"luta": "Só nesta luta", "capitulo": "Até o fim do capítulo", "run": "Pelo resto da run"}


def _cortar(texto: str, n: int) -> str:
    return texto if len(texto) <= n else texto[: n - 1].rstrip(" ,;:") + "…"


class _Base(IScene):
    def __init__(self, entrada: IInputProvider, ao_sair) -> None:
        self.entrada = entrada
        self.ao_sair = ao_sair
        self.relogio = 0.0

    def _t(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

    def _sair(self) -> bool:
        if self.entrada.is_action_pressed("sair"):
            self.ao_sair()
            return True
        return False

    def _fundo(self, r: IRenderer) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)


# ----------------------------------------------------------------------- título


class TituloScene(_Base):
    def __init__(
        self,
        entrada,
        ao_escolher,
        ao_sair,
        ao_grimorio=None,
        ao_opcoes=None,
        continuar: str | None = None,
        ao_continuar=None,
        ao_diaria=None,
        recorde_diaria: int | None = None,
        ao_cronica=None,
    ) -> None:
        super().__init__(entrada, ao_sair)
        self.ao_cronica = ao_cronica
        self.ao_grimorio = ao_grimorio
        self.ao_opcoes = ao_opcoes
        self.ao_continuar = ao_continuar
        self.ao_diaria = ao_diaria
        bal = carregar_balanceamento()
        cfg = bal["combate"]
        self.modos = [(m, d) for m, d in cfg["dificuldades"].items() if not m.startswith("_")]
        self.jogos = list(JOGOS)
        self.i_jogo = 0
        rodas = carregar_rodas(carregar_raridades(bal))
        self.animes = animes_jogaveis(rodas)
        self.tecnicas_anime = Counter(anime_de(f.origem) for f in rodas["tecnicas"].fatias)
        self.i_anime = 0
        self.continuar = continuar if ao_continuar is not None else None
        self.recorde_diaria = recorde_diaria
        self.itens: list[tuple[str, str, str]] = self._montar_itens()
        padrao = cfg["dificuldade_padrao"]
        self.cursor = (
            0 if continuar else next(i for i, x in enumerate(self.itens) if x[0] == padrao)
        )
        self.ao_escolher = ao_escolher

    @property
    def jogo(self) -> str:
        return self.jogos[self.i_jogo]

    @property
    def anime(self) -> str:
        return self.animes[self.i_anime] if self.jogo == "anime" and self.animes else ""

    def _montar_itens(self) -> list[tuple[str, str, str]]:
        """Cada linha: (o que faz, texto, detalhe à direita)."""
        itens = []
        if self.continuar:
            itens.append(("continuar", "Continuar a run", self.continuar))
        if self.ao_diaria is not None:
            detalhe = (
                f"hoje: {self.recorde_diaria} de 12"
                if self.recorde_diaria is not None
                else "Difícil, a mesma sorte para todos"
            )
            itens.append(("diaria", "Semente do dia", detalhe))
        itens.append(("jogo", f"Modo: ← {JOGOS[self.jogo]} →", DESCRICAO_JOGO[self.jogo]))
        if self.jogo == "anime" and self.animes:
            n = self.tecnicas_anime[self.anime]
            itens.append(("anime", f"Anime: ← {self.anime} →", f"{n} técnicas"))
        itens += [(m, d["nome"], f"~{d['alvo_vitoria']:.0%} vencem") for m, d in self.modos]
        return itens

    def _mudar(self, acao: str, passo: int) -> None:
        if acao == "jogo":
            self.i_jogo = (self.i_jogo + passo) % len(self.jogos)
        elif acao == "anime" and self.animes:
            self.i_anime = (self.i_anime + passo) % len(self.animes)
        else:
            return
        self.itens = self._montar_itens()
        som.tocar("mover")

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        if self._sair():
            return
        e = self.entrada
        if self.ao_grimorio is not None and e.is_action_pressed("grimorio"):
            self.ao_grimorio()
            return
        if self.ao_opcoes is not None and e.is_action_pressed("opcoes"):
            self.ao_opcoes()
            return
        if self.ao_cronica is not None and e.is_action_pressed("cronica"):
            self.ao_cronica()
            return
        som.musica("titulo")
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(self.itens)
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(self.itens)
            som.tocar("mover")
        elif e.is_action_pressed("esquerda"):
            self._mudar(self.itens[self.cursor][0], -1)
        elif e.is_action_pressed("direita"):
            self._mudar(self.itens[self.cursor][0], 1)
        elif e.is_action_pressed("confirmar"):
            acao = self.itens[self.cursor][0]
            if acao in ("jogo", "anime"):
                self._mudar(acao, 1)
                return
            som.tocar("confirmar")
            if acao == "continuar":
                self.ao_continuar()
            elif acao == "diaria":
                self.ao_diaria()
            elif self.jogo == "classico":
                self.ao_escolher(acao)
            else:
                self.ao_escolher(acao, jogo=self.jogo, anime=self.anime)

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        for k in range(6):  # a lua de sangue atrás do ensō
            r.draw_ui_circle(480, 250, 150 - k * 8, alpha((120, 14, 18, 255), 10 + k * 4))
        r.draw_ui_circle(480, 250, 104, alpha((90, 10, 14, 255), 120))
        _particulas(r, t, 26, alpha(TINTA, 40), sobe=False, tam=1.8, vel=14, deriva=24, semente=3)
        self._gotas(r, t)
        # o ensō se desenha no primeiro segundo e depois gira devagar
        traco = min(1.0, t / 1.4)
        ini = 1.9 + t * 0.05
        r.draw_ui_arc(480, 250, 190, ini, ini + 5.6 * traco, alpha(TINTA, 22), 14)
        self._corrente_de_fundo(r, t)
        respira = math.sin(t * 1.6) * 2
        desenhar_lutador(
            r,
            330,
            420 + respira,
            1.25,
            TINTA,
            alpha((255, 255, 255, 255), 190),
            guarda=0.6,
            tempo=t,
        )
        desenhar_lutador(
            r, 630, 420 - respira, 1.25, (74, 18, 16, 255), alpha(TINTA, 220), estilo="oni", tempo=t
        )
        choque = (t % 4.5) / 4.5  # de tempos em tempos, as lâminas se cruzam num clarão
        if choque > 0.93:
            k = (choque - 0.93) / 0.07
            r.draw_ui_line(420, 330, 540, 290, alpha(SANGUE_VIVO, 255 * (1 - k)), 3)
            r.draw_ui_circle(480, 310, 40 * k + 6, alpha((255, 255, 255, 255), 120 * (1 - k)), 2)
        self._t(r, 480, 70, "業", 96, OURO, "center")
        self._t(r, 480, 150, "Karmabound", 52, TINTA, "center")
        self._t(r, 480, 200, "todo azar fica preso ao seu Carma", 18, alpha(TINTA, 150), "center")
        n = len(self.itens)
        y0 = 452 if n <= 4 else 432 if n <= 6 else 414
        passo = min(36, (600 - y0) // n)
        for i, (acao, texto, detalhe) in enumerate(self.itens):
            y = y0 + i * passo
            atual = i == self.cursor
            especial = acao in ("continuar", "diaria", "jogo", "anime")
            cor = (
                (OURO if especial else TINTA) if atual else alpha(OURO if especial else TINTA, 120)
            )
            if atual:
                r.draw_ui_rect(230, y - 4, 500, passo - 3, alpha(LACA, 255))
                r.draw_ui_polygon([(244, y + 3), (254, y + 10), (244, y + 17)], OURO)
            self._t(r, 266, y - 2, texto, 18, cor)
            self._t(r, 718, y + 2, detalhe, 13, alpha(TINTA, 100), "topright")
        self._t(
            r,
            480,
            ALTURA - 28,
            "↑ ↓ escolhe · ← → muda o modo · Enter começa · G grimório · C crônica · O opções",
            14,
            alpha(TINTA, 100),
            "center",
        )
        vfx.vinheta(r, 0.9)
        vfx.grao(r, t, 140)
        vfx.revelar(r, t)

    def _gotas(self, r: IRenderer, t: float) -> None:
        """Tinta escorrendo do alto da tela."""
        for i, x in enumerate((60, 150, 255, 705, 812, 905)):
            ciclo = (t * (0.12 + 0.03 * i) + i * 0.37) % 1.0
            comp = 40 + 160 * ciclo
            r.draw_ui_line(x, 0, x, comp, alpha(TINTA, 26), 3 + i % 2)
            r.draw_ui_circle(x, comp + 4, 4 + i % 2, alpha(TINTA, 40))

    def _corrente_de_fundo(self, r: IRenderer, t: float) -> None:
        """A corrente do Carma atravessa o título, avermelhando aos poucos."""
        y = 268
        pulso = 0.5 + 0.5 * math.sin(t * 1.2)
        for i in range(34):
            x = 20 + i * 28
            cor = mistura(FERRO, SANGUE_VIVO, 0.15 + 0.35 * pulso * (i % 5 == 0))
            if i % 2 == 0:
                r.draw_ui_polygon(
                    [
                        (x - 10, y),
                        (x - 5, y - 5),
                        (x + 5, y - 5),
                        (x + 10, y),
                        (x + 5, y + 5),
                        (x - 5, y + 5),
                    ],
                    alpha(cor, 70),
                    2,
                )
            else:
                r.draw_ui_line(x - 12, y, x + 12, y, alpha(cor, 70), 3)


# ----------------------------------------------------------------------- troca de técnica


class SubstituirScene(_Base):
    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.cores = {r.id: hex_cor(r.cor) for r in jornada.ctx.raridades}
        self.cursor = 0  # para jogar de controle: ↑ ↓ e confirmar

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        if self._sair():
            return
        e = self.entrada
        tecnicas = self.j.jogador.tecnicas
        for i, t in enumerate(tecnicas):
            if e.is_action_pressed(f"tecnica_{i + 1}"):
                som.tocar("confirmar")
                self.j.substituir(t)
                self.ao_concluir()
                return
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(tecnicas)
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(tecnicas)
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            som.tocar("confirmar")
            self.j.substituir(tecnicas[self.cursor])
            self.ao_concluir()
            return
        if e.is_action_pressed("cancelar"):
            self.j.substituir(None)
            self.ao_concluir()

    def _linha(self, r, y, t, fatia, numero: str = "") -> None:
        cor = self.cores.get(t.raridade, TINTA)
        if numero:
            self._t(r, 220, y + 8, numero, 22, alpha(TINTA, 150))
        self._t(r, 260, y, fatia.kanji if fatia else "?", 40, cor)
        self._t(r, 320, y + 4, t.nome, 22, cor)
        for k, linha in enumerate(quebrar(fatia.texto if fatia else "", 68)[:2]):
            self._t(r, 320, y + 32 + k * 18, linha, 15, alpha(TINTA, 150))

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        nova = self.j.pendente
        fatias = self.j.ctx.tecnicas
        self._t(r, 480, 40, "Seus quatro espaços estão cheios", 26, TINTA, "center")
        self._t(r, 220, 100, "Técnica nova", 16, alpha(OURO, 200))
        self._linha(r, 124, Tecnica.de_fatia(nova), nova)
        self._t(r, 220, 214, "Qual sai?", 16, alpha(TINTA, 150))
        for i, t in enumerate(self.j.jogador.tecnicas):
            if i == self.cursor:
                r.draw_ui_rect(200, 234 + i * 74, 560, 68, LACA)
                r.draw_ui_polygon(
                    [(206, 252 + i * 74), (214, 258 + i * 74), (206, 264 + i * 74)], OURO
                )
            self._linha(r, 240 + i * 74, t, fatias.get(t.id), str(i + 1))
        self._t(
            r,
            480,
            ALTURA - 32,
            "1–4 (ou ↑ ↓ e Enter) troca · Backspace descarta a nova",
            15,
            alpha(TINTA, 110),
            "center",
        )


# ----------------------------------------------------------------------- Altar dos Votos


class AltarScene(_Base):
    """Você escolhe as restrições e a duração; o Altar pesa e dá a força do voto; você
    compra os ganhos. Sem números: só se mais um nível ainda cabe. A sobra fica guardada."""

    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.restricoes = list(jornada.ctx.catalogo.restricoes.values())
        self.marcadas: set[str] = set()
        self.duracao = "run"
        self.cursor = 0
        self.pesos: dict[str, float] | None = None
        self.proposta: PropostaDeVoto | None = None
        self.compra: list = []  # os ganhos marcados (um item por nível)
        self.cursor_compra = 0
        self.estado = "pesar"  # pesar | escolher | propor | comprar
        self.quadros = 0
        self.aviso = ""
        self.rol = Rolagem(8)  # restrições: 8 de 44 px, com as 3 ações embaixo
        self.rol_compra = Rolagem(11)  # ganhos: 11 de 34 px, com Jurar e Voltar embaixo

    @property
    def linhas(self) -> list[str]:
        return [r.id for r in self.restricoes] + ["duracao", "pesar", "recusar"]

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self.quadros += 1
        if self._sair():
            return
        if self.estado == "pesar":  # um quadro com "o Altar pesa..." antes de medir
            if self.quadros > 1:
                self.pesos = self.j.pesar_restricoes(self.duracao)
                self.estado = "escolher"
            return
        if self.estado == "propor":
            if self.quadros > 1:
                self.proposta = self.j.propor_voto(sorted(self.marcadas), self.duracao)
                self.compra = list(self.proposta.voto.ganhos)  # a sugestão do Altar
                self.cursor_compra = 0
                self.estado = "comprar"
            return
        e = self.entrada
        if self.estado == "comprar":
            self._comprar(e)
            return
        linhas = self.linhas
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(linhas)
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(linhas)
        elif e.is_action_pressed("confirmar"):
            item = linhas[self.cursor]
            if item == "duracao":
                self.duracao = DURACOES[(DURACOES.index(self.duracao) + 1) % len(DURACOES)]
                self.estado, self.quadros = "pesar", 0
            elif item == "pesar":
                if not self.marcadas:
                    self.aviso = "marque ao menos uma restrição"
                else:
                    self.estado, self.quadros, self.aviso = "propor", 0, ""
            elif item == "recusar":
                self.j.recusar_altar()
                self.ao_concluir()
            elif item in self.marcadas:
                self.marcadas.discard(item)
            elif len(self.marcadas) < 3:
                self.marcadas.add(item)
            else:
                self.aviso = "no máximo 3 restrições por voto"

    # --------------------------------------------------------------- compra

    @property
    def ganhos(self) -> list:
        return list(self.j.ctx.catalogo.ganhos.values())

    @property
    def linhas_compra(self) -> list:
        return [*self.ganhos, "jurar", "voltar"]

    def _niveis(self, g) -> int:
        return sum(1 for x in self.compra if x.id == g.id)

    def _comprar(self, e) -> None:
        linhas = self.linhas_compra
        item = linhas[self.cursor_compra]
        if e.is_action_pressed("cancelar"):
            self.estado = "escolher"
        elif e.is_action_pressed("cima"):
            self.cursor_compra, self.aviso = (self.cursor_compra - 1) % len(linhas), ""
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor_compra, self.aviso = (self.cursor_compra + 1) % len(linhas), ""
            som.tocar("mover")
        elif e.is_action_pressed("esquerda") and not isinstance(item, str):
            if self._niveis(item):  # devolve o último nível desse ganho
                i = max(k for k, x in enumerate(self.compra) if x.id == item.id)
                self.compra.pop(i)
                som.tocar("mover")
        elif e.is_action_pressed("direita") or e.is_action_pressed("confirmar"):
            if item == "jurar":
                som.tocar("confirmar")
                self.j.jurar(self.proposta, self.compra)
                self.ao_concluir()
            elif item == "voltar":
                self.estado = "escolher"
            elif self.proposta.cabe(self.j.ctx, self.compra, item):
                self.compra.append(item)
                som.tocar("confirmar")
            else:
                self.aviso = (
                    "nível máximo" if self._niveis(item) >= item.niveis else "não cabe neste voto"
                )

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        self._t(r, 40, 24, "誓  Altar dos Votos", 30, OURO)
        livres = self.j.ctx.catalogo.limite_ativos - len(self.j.estado.votos.ativos)
        self._t(
            r,
            LARGURA - 40,
            34,
            f"espaços de voto livres: {livres}",
            15,
            alpha(TINTA, 130),
            "topright",
        )
        if self.estado in ("pesar", "propor"):
            texto = (
                "o Altar pesa o seu destino…"
                if self.estado == "pesar"
                else "o Altar mede o voto inteiro…"
            )
            self._t(r, 480, 300, texto, 24, alpha(TINTA, 180), "center")
            return
        if self.estado == "comprar":
            self._tela_compra(r)
            vfx.revelar(r, self.relogio)
            return
        self._t(
            r,
            40,
            76,
            "Escolha até 3 restrições. O valor de cada uma é o que ela tira de VOCÊ, agora.",
            15,
            alpha(TINTA, 150),
        )
        teto = self.j.ctx.catalogo.teto_por_restricao
        n = len(self.restricoes)
        self.rol.seguir(self.cursor if self.cursor < n else None, n)
        self.rol.desenhar(r, 938, 112, 44, n)
        for i in self.rol.faixa(n):
            res = self.restricoes[i]
            y = self.rol.y(i, 112, 44)
            atual = i == self.cursor
            if atual:
                r.draw_ui_rect(30, y - 6, 900, 40, LACA)
            marcada = res.id in self.marcadas
            r.draw_ui_rect(44, y + 4, 18, 18, OURO if marcada else alpha(FERRO, 160))
            self._t(r, 76, y - 2, res.kanji, 26, SANGUE_VIVO if marcada else TINTA)
            self._t(r, 116, y, res.nome, 19, TINTA)
            self._t(r, 300, y + 3, _cortar(res.texto, 44), 15, alpha(TINTA, 140))
            peso = (self.pesos or {}).get(res.id, 0.0)
            if peso <= 0.05:
                rotulo, cor = "não custa nada a você", alpha(TINTA, 90)
            else:
                extra = " (teto)" if peso > teto else ""
                rotulo, cor = f"custa ~{peso:.1f} luta{extra}".replace(".", ","), SANGUE_VIVO
            self._t(r, 920, y + 3, rotulo, 15, cor, "topright")
        base = 112 + min(n, self.rol.visiveis) * 44 + 8
        for k, (item, texto) in enumerate(
            [
                ("duracao", f"Duração: {NOME_DURACAO[self.duracao]}"),
                ("pesar", "Pesar este voto"),
                ("recusar", "Recusar o Altar"),
            ]
        ):
            i = len(self.restricoes) + k
            y = base + k * 34
            if i == self.cursor:
                r.draw_ui_rect(30, y - 6, 420, 32, LACA)
            self._t(r, 52, y - 2, texto, 18, OURO if item == "pesar" else TINTA)
        if self.aviso:
            self._t(r, 920, base + 34, self.aviso, 15, SANGUE_VIVO, "topright")
        self._t(
            r,
            480,
            ALTURA - 26,
            "↑ ↓ move · Enter marca/escolhe · esc sai",
            14,
            alpha(TINTA, 100),
            "center",
        )

    def _tela_compra(self, r: IRenderer) -> None:
        p = self.proposta
        if p is None:
            return
        v = p.voto
        abre = " · ".join(f"{x.kanji} {x.nome}" for x in v.restricoes)
        self._t(
            r, 40, 72, f"Você abre mão de: {abre} — {DURANTE[v.duracao].lower()}", 16, SANGUE_VIVO
        )
        # a força do voto: quanto ainda dá para comprar, sem números
        restante = max(0.0, p.pontos - p.custo(self.j.ctx, self.compra))
        frac = restante / p.pontos if p.pontos > 0 else 0.0
        self._t(r, 40, 102, "força do voto", 15, alpha(TINTA, 140))
        r.draw_ui_rect(160, 106, 420, 12, LACA)
        r.draw_ui_rect(160, 106, 420 * frac, 12, alpha(OURO, 200))
        if self.j.estado.pontos_guardados > 0:
            self._t(r, 596, 102, "(com a força guardada de votos anteriores)", 13, alpha(OURO, 140))
        ganhos = self.ganhos
        ng = len(ganhos)
        self.rol_compra.seguir(self.cursor_compra if self.cursor_compra < ng else None, ng)
        self.rol_compra.desenhar(r, 938, 136, 34, ng)
        for i in self.rol_compra.faixa(ng):
            g = ganhos[i]
            y = self.rol_compra.y(i, 136, 34)
            atual = i == self.cursor_compra
            if atual:
                r.draw_ui_rect(30, y - 5, 900, 32, LACA)
            n = self._niveis(g)
            cabe = p.cabe(self.j.ctx, self.compra, g)
            cor = OURO if n else (TINTA if cabe else alpha(TINTA, 80))
            self._t(r, 52, y - 2, g.kanji, 22, cor)
            self._t(r, 88, y, g.nome, 17, cor)
            self._t(r, 260, y + 2, _cortar(g.texto, 52), 14, alpha(TINTA, 150 if cabe or n else 70))
            if g.niveis > 1:
                for k in range(g.niveis):
                    cheio = k < n
                    r.draw_ui_circle(
                        770 + k * 18,
                        y + 10,
                        6,
                        OURO if cheio else alpha(FERRO, 160),
                        0 if cheio else 1,
                    )
            elif n:
                r.draw_ui_circle(770, y + 10, 6, OURO)
            if not cabe and n < g.niveis:
                self._t(r, 920, y + 2, "não cabe", 13, alpha(TINTA, 90), "topright")
        base = 136 + min(ng, self.rol_compra.visiveis) * 34 + 6
        for k, (item, texto) in enumerate(
            (("jurar", "Jurar este voto"), ("voltar", "Voltar às restrições"))
        ):
            y = base + k * 30
            if self.linhas_compra[self.cursor_compra] == item:
                r.draw_ui_rect(30, y - 5, 420, 28, LACA)
            self._t(r, 52, y - 2, texto, 17, OURO if item == "jurar" else TINTA)
        if self.aviso:
            self._t(r, 920, base, self.aviso, 15, SANGUE_VIVO, "topright")
        self._t(
            r,
            480,
            ALTURA - 26,
            "↑ ↓ move · → ou Enter compra um nível · ← devolve · Backspace volta",
            14,
            alpha(TINTA, 100),
            "center",
        )


# ----------------------------------------------------------------------- fim


class FimScene(_Base):
    def __init__(
        self, jornada: Jornada, entrada, ao_reiniciar, ao_sair, recorde=None, feitos=()
    ) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_reiniciar = ao_reiniciar
        self.recorde = recorde  # o melhor da semente do dia, se era uma
        self.feitos = list(feitos)  # os Feitos conquistados nesta run

    def update(self, world, delta_time: float) -> None:
        if self.relogio == 0.0:
            som.musica(None)
            som.tocar("vitoria" if self.j.fase == "vitoria" else "derrota")
        self.relogio += delta_time
        if self._sair():
            return
        if self.entrada.is_action_pressed("confirmar"):
            self.ao_reiniciar()

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        j = self.j
        t = self.relogio
        venceu = j.fase == "vitoria"
        torre = getattr(j.ctx, "jogo", "classico") == "torre"
        if venceu:  # o ensō dourado se fecha em volta de quem venceu
            traco = min(1.0, t / 1.6)
            r.draw_ui_arc(480, 220, 150, 1.6, 1.6 + 6.0 * traco, alpha(OURO, 120), 10)
            _particulas(r, t, 30, alpha(OURO, 110), sobe=True, tam=2.0, vel=30, semente=5)
            desenhar_lutador(r, 480, 300, 1.5, TINTA, alpha(OURO, 220), guarda=0.3, tempo=t)
            self._t(r, 480, 330, "勝  O torneio é seu", 44, OURO, "center")
        else:  # as correntes fecham sobre quem caiu
            _particulas(r, t, 30, alpha(SANGUE_VIVO, 90), sobe=False, tam=2.0, vel=20, semente=9)
            desenhar_lutador(r, 480, 300, 1.5, (60, 22, 24, 255), alpha(TINTA, 200), tempo=t)
            vfx.correntes_fechando(r, 480, 220, min(1.0, t / 1.4))
            fim = "塔  A torre cobrou o preço" if torre else "敗  Seu destino terminou aqui"
            self._t(r, 480, 330, fim, 40, SANGUE_VIVO, "center")
        modo = j.ctx.combate["dificuldades"][j.modo]["nome"]
        votos = len(j.estado.votos.ativos) + len(j.estado.votos.quebrados)
        vencidas = j.estado.lutas_vencidas
        if torre:
            placar = f"Torre sem fim · {modo} · {vencidas} andares"
            if self.recorde is not None:
                placar += f" · seu melhor: {self.recorde}"
        else:
            jogo = {"anime": f"Mundo de {j.ctx.anime}", "chefes": "Desfile de chefes"}
            prefixo = f"{jogo[j.ctx.jogo]} · " if j.ctx.jogo in jogo else ""
            placar = f"{prefixo}{modo} · {vencidas} de {j.ctx.lutas} lutas vencidas"
        linhas = [
            placar,
            f"Dom: {j.dom.kanji} {j.dom.nome}" if j.dom else "",
            f"Despertares: {j.despertares} · Votos jurados: {votos}",
            "Técnicas: " + ", ".join(t.nome for t in j.jogador.tecnicas),
            ("Relíquias: " + " ".join(x.kanji for x in j.estado.reliquias))
            if j.estado.reliquias
            else "",
            f"Semente do dia ({j.diaria}): seu melhor hoje é {self.recorde} de 12"
            if j.diaria and self.recorde is not None
            else "",
        ]
        for k, linha in enumerate(x for x in linhas if x):
            self._t(r, 480, 400 + k * 28, linha, 17, alpha(TINTA, 170), "center")
        for k, f in enumerate(self.feitos[:3]):  # os Feitos novos, no alto
            brilho = 255 * min(1.0, max(0.0, (t - 0.8 - k * 0.3) / 0.4))
            self._t(
                r,
                480,
                24 + k * 26,
                f"{f.kanji}  Feito: {f.nome}",
                18,
                alpha(OURO, brilho),
                "center",
            )
        self._t(
            r, 480, ALTURA - 30, "Enter volta ao título · esc sai", 15, alpha(TINTA, 110), "center"
        )
        vfx.revelar(r, t)

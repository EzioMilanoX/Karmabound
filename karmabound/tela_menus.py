"""Telas de menu da run: título, troca de técnica, Altar dos Votos, fim e os anúncios.

Todas leem e mexem só na `Jornada`; nenhuma decide regra. O Altar mede as
restrições contra o build do jogador (pode levar um ou dois segundos): a tela
desenha "o Altar pesa..." num quadro e mede no seguinte.

Os anúncios (`FusaoScene`, `AliadoScene`) entram entre duas fases: o Fluxo os mostra
quando uma fusão nasce ou um aliado chega, e eles só chamam `ao_concluir` no fim.
As pistas de combo (融 fusão, 共 Ressonância) vêm de `grimorio.pista`/`perda`; aqui só
viram texto (`texto_da_pista`, `texto_da_perda`, `resumo_do_build`).
"""

from __future__ import annotations

import math
from collections import Counter
from functools import cache

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes, vfx
from karmabound.aliados import Aliado
from karmabound.aliados import aliado as aliado_de
from karmabound.arenas import _particulas
from karmabound.ascensao import carregar_ascensao, niveis_ate
from karmabound.combate import Tecnica
from karmabound.figuras import desenhar_lutador
from karmabound.fusoes import Fusao, nomes_dos_requisitos, tecnicas_de_fusao
from karmabound.grimorio import Grimorio, Perda, Pista, fusao_descoberta, perda, pista
from karmabound.jornada import Jornada, PropostaDeVoto
from karmabound.legado import Fechamento
from karmabound.opcoes import OPCOES
from karmabound.ressonancia import contar_animes, ressonancias_ativas
from karmabound.rodas import (
    Fatia,
    anime_de,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
)
from karmabound.rolagem import Rolagem
from karmabound.run import DESCRICAO_JOGO, JOGOS, animes_jogaveis
from karmabound.transicoes import Camada, Cartas, carimbo, suave
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
    VERDE_JADE,
    alpha,
    ease_out,
    hex_cor,
    mistura,
    moldura,
    quebrar,
)

DURACOES = ("luta", "capitulo", "run")
NOME_DURACAO = {
    "luta": "só esta luta",
    "capitulo": "até o fim do capítulo",
    "run": "o resto da run",
}
DURANTE = {"luta": "Só nesta luta", "capitulo": "Até o fim do capítulo", "run": "Pelo resto da run"}


LARGURA_TEXTO_TROCA = 72  # caracteres por linha na troca de técnica
EXTENSO = {2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete"}


def _cortar(texto: str, n: int) -> str:
    return texto if len(texto) <= n else texto[: n - 1].rstrip(" ,;:") + "…"


# ----------------------------------------------------------------------- pistas de combo

NOME_REQUISITO = {
    "tecnica": "Técnica",
    "dom": "Dom",
    "linhagem": "Linhagem",
    "reliquia": "Relíquia",
    "despertar": "Despertar",
}


@cache
def fatias_por_id() -> dict[str, Fatia]:
    """Toda fatia das rodas inteiras e as técnicas de fusão (o kanji de uma peça)."""
    rodas = carregar_rodas(carregar_raridades(carregar_balanceamento()))
    todas = {f.id: f for roda in rodas.values() for f in roda.fatias}
    return {**todas, **tecnicas_de_fusao()}


def fatias_das_tecnicas(j: Jornada) -> dict[str, Fatia]:
    """As técnicas que podem estar na mão: as das rodas desta run e as de fusão."""
    return {**tecnicas_de_fusao(), **j.ctx.tecnicas}


def _nivel(n: int) -> str:
    return " II" if n >= 2 else ""


def texto_da_pista(p: Pista, grimorio: Grimorio | None, largura: int = 0) -> str:
    """'融 Vazio Púrpura · 共 +Naruto': o selo de uma opção. `largura` (caracteres): o
    texto mais longo que cabe, encurtando primeiro o nome e depois a palavra."""
    fusao: list[str] = []
    if p.fusoes:
        f = p.fusoes[0]
        nome = f.fatia.nome if fusao_descoberta(grimorio, f) else ""
        alvo = nome or "uma fusão…"
        if p.completa:
            fusao = [f"融 completa {alvo}", f"融 {alvo}", "融 completa", "融"]
        else:
            fusao = [f"融 {alvo}", "融 fusão", "融"]
    ress = [f"共 +{p.anime}{_nivel(p.nivel)}", f"共 +{p.anime}", "共"] if p.anime else []
    # na ordem de preferência: o nome da fusão vale mais que o nível da Ressonância
    combos = [" · ".join(x for x in (a, b) if x) for a in fusao or [""] for b in ress or [""]]
    if not largura:
        return combos[0]
    return next((c for c in combos if len(c) <= largura), min(combos, key=len))


def texto_da_perda(p: Perda) -> str:
    """'desfaz 共 Naruto · peça de 融': o aviso de tirar uma técnica."""
    partes = []
    for anime, _antes, depois in p.ressonancias:
        partes.append(f"{'desfaz' if depois == 0 else 'enfraquece'} 共 {anime}")
    if p.fusoes:
        partes.append("peça de 融")
    return " · ".join(partes)


def partes_do_build(j: Jornada) -> list[str]:
    """O canto discreto das telas entre lutas: Ressonâncias, aliado e Ascensão."""
    partes = [f"共 {r.kanji} {r.nome}{_nivel(r.nivel)}" for r in ressonancias_ativas(j.estado)]
    a = aliado_de(j.estado.aliado)
    if a is not None:
        partes.append(f"伴 {a.nome} nível {j.estado.aliado_nivel}")
    if j.ascensao:
        partes.append(f"昇 Ascensão {j.ascensao}")
    return partes


def resumo_do_build(j: Jornada) -> str:
    return " · ".join(partes_do_build(j))


def proxima_ressonancia(j: Jornada) -> tuple[str, int] | None:
    """O anime mais perto de ressoar (e quantas técnicas dele estão na mão)."""
    conta = contar_animes(j.estado)
    ativas = {r.anime for r in ressonancias_ativas(j.estado)}
    resto = [(n, a) for a, n in conta.items() if a not in ativas and n >= 1]
    if not resto:
        return None
    n, a = max(resto)
    return a, n


def fusao_de(j: Jornada, fatia: Fatia) -> Fusao | None:
    """A fusão de que a técnica `fatia` nasceu (a que já nasceu nesta run, de preferência)."""
    candidatas = [f for f in j.ctx.fusoes if f.resultado == fatia.id]
    nascidas = [f for f in candidatas if f.id in j.estado.fusoes_nascidas]
    return (nascidas or candidatas or [None])[0]


def pecas_da_fusao(j: Jornada, fusao: Fusao) -> list[tuple[str, Fatia | None, str]]:
    """(tipo, a fatia da peça, o nome) de cada requisito: a que você tem, num "um de"."""
    e = j.estado
    tem = {t.id for t in e.jogador.tecnicas} | {f.id for f in e.reliquias}
    tem |= {x.id for x in (e.dom, e.linhagem) if x is not None} | set(e.despertares_ids)
    por_id = fatias_por_id()
    nomes = nomes_dos_requisitos(fusao)
    pecas = []
    for r, nome in zip(fusao.requisitos, nomes, strict=True):
        pid = next((i for i in r.ids if i in tem), r.ids[0])
        f = por_id.get(pid)
        pecas.append((r.tipo, f, f.nome if f else nome))
    return pecas


class _Base(IScene):
    segurar_saida = 0.0  # quanto a transição segura esta tela antes de cobri-la (o carimbo)

    def __init__(self, entrada: IInputProvider, ao_sair) -> None:
        self.entrada = entrada
        self.ao_sair = ao_sair
        self.relogio = 0.0

    def animar(self, dt: float) -> None:
        """Só o enfeite anda: a transição chama na tela que está saindo (sem entrada)."""
        self.relogio += dt
        self._animar(dt)

    def _animar(self, dt: float) -> None:
        """As animações da tela (cartas, contagens); o update chama a cada quadro."""

    def assentar(self) -> None:
        """Toda animação de entrada já no fim (capturas de tela)."""
        self._animar(10.0)

    def _t(self, r: IRenderer, x, y, texto, tam, cor, anchor="topleft") -> None:
        r.draw_text(x, y, texto, tam, cor, anchor=anchor, font_id=FONTE_PINCEL)

    def _t_ajustado(self, r: IRenderer, x, y, texto, largura: int, tam, cor) -> None:
        """Uma linha de `largura` caracteres; o que não cabe vai em duas, com letra menor."""
        if len(texto) <= largura:
            self._t(r, x, y, texto, tam, cor)
            return
        menor = tam - 2
        cabe = round(largura * tam / menor)
        linhas = quebrar(texto, cabe)
        if len(linhas) > 2:
            linhas = [linhas[0], _cortar(" ".join(linhas[1:]), cabe)]
        passo = menor + 2
        topo = y + tam / 2 - passo  # as duas linhas centradas onde ficaria a uma
        for k, linha in enumerate(linhas):
            self._t(r, x, topo + k * passo, linha, menor, cor)

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
        abertos: frozenset[str] | None = None,
        legado: list[str] | tuple[str, ...] = (),
        ascensoes: dict[str, int] | None = None,
    ) -> None:
        """`abertos`: os animes que o Legado já abriu (None: todos); `legado`: as linhas
        discretas do canto (a Memória e a Nêmesis à espera); `ascensoes`: a maior
        Ascensão aberta em cada dificuldade (escolher uma dificuldade com Ascensão aberta
        abre a escolha do degrau; ← → muda, Enter começa, Backspace volta)."""
        super().__init__(entrada, ao_sair)
        self.ascensoes = {m: n for m, n in (ascensoes or {}).items() if n > 0}
        self.modo_asc: str | None = None  # a dificuldade cujo degrau se escolhe agora
        self.nivel_asc = 0
        self.t_asc = 0.0  # o painel da Ascensão entrando
        self.ao_cronica = ao_cronica
        self.legado = list(legado)
        self.ao_grimorio = ao_grimorio
        self.ao_opcoes = ao_opcoes
        self.ao_continuar = ao_continuar
        self.ao_diaria = ao_diaria
        bal = carregar_balanceamento()
        cfg = bal["combate"]
        self.modos = [(m, d) for m, d in cfg["dificuldades"].items() if not m.startswith("_")]
        rodas = carregar_rodas(carregar_raridades(bal))
        self.animes = [a for a in animes_jogaveis(rodas) if abertos is None or a in abertos]
        # sem anime aberto que tenha um Mundo próprio, o modo nem aparece
        self.jogos = [g for g in JOGOS if g != "anime" or self.animes]
        self.i_jogo = 0
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
        self.cartas = Cartas(sobe=26, lado=True)  # o menu entra linha a linha
        self.cartas.t = -0.35  # depois do título
        self.y_sel: float | None = None  # a faixa da seleção desliza até o cursor

    def _layout(self) -> tuple[int, int]:
        """(y da primeira linha, passo) do menu."""
        n = len(self.itens)
        y0 = 452 if n <= 4 else 432 if n <= 6 else 414
        return y0, min(36, (600 - y0) // n)

    def _animar(self, dt: float) -> None:
        self.cartas.avancar(dt, self.cursor, len(self.itens))
        y0, passo = self._layout()
        alvo = y0 + self.cursor * passo
        if self.y_sel is None:
            self.y_sel = alvo
        self.y_sel += (alvo - self.y_sel) * (1 - math.exp(-dt * OPCOES.velocidade * 18))

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
        for m, d in self.modos:
            detalhe = f"~{d['alvo_vitoria']:.0%} vencem"
            if self.ascensoes.get(m):
                detalhe += f" · 昇 {self.ascensoes[m]}"
            itens.append((m, d["nome"], detalhe))
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

    def _comecar(self, modo: str, ascensao: int = 0) -> None:
        extra: dict = {}
        if self.jogo != "classico":
            extra = {"jogo": self.jogo, "anime": self.anime}
        if ascensao:
            extra["ascensao"] = ascensao
        self.ao_escolher(modo, **extra)

    def _escolher_ascensao(self, e) -> None:
        """O painel da Ascensão: ← → muda o degrau, Enter começa, Backspace/Esc volta."""
        maximo = self.ascensoes.get(self.modo_asc, 0)
        if e.is_action_pressed("sair") or e.is_action_pressed("cancelar"):
            self.modo_asc = None
            som.tocar("mover")
        elif e.is_action_pressed("esquerda") or e.is_action_pressed("baixo"):
            self.nivel_asc = max(0, self.nivel_asc - 1)
            som.tocar("mover")
        elif e.is_action_pressed("direita") or e.is_action_pressed("cima"):
            self.nivel_asc = min(maximo, self.nivel_asc + 1)
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            som.tocar("confirmar")
            modo, self.modo_asc = self.modo_asc, None
            self._comecar(modo, self.nivel_asc)

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        e = self.entrada
        if self.modo_asc is not None:
            self.t_asc += delta_time * OPCOES.velocidade
            self._escolher_ascensao(e)
            return
        if self._sair():
            return
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
            elif self.ascensoes.get(acao):  # há Ascensão aberta: primeiro o degrau
                self.modo_asc, self.nivel_asc, self.t_asc = acao, self.ascensoes[acao], 0.0
            else:
                self._comecar(acao)

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
        self._brasas(r, t)
        respira = 0.5 + 0.5 * math.sin(t * 1.3)  # o kanji do Carma respira devagar
        self._t(
            r,
            480,
            70,
            "業",
            102 + round(6 * respira),
            alpha(SANGUE_VIVO, 30 + 60 * respira),
            "center",
        )
        self._t(
            r,
            480,
            70,
            "業",
            96 + round(2 * respira),
            mistura(OURO, TINTA, 0.12 * respira),
            "center",
        )
        self._t(r, 480, 150, "Karmabound", 52, TINTA, "center")
        self._t(r, 480, 200, "todo azar fica preso ao seu Carma", 18, alpha(TINTA, 150), "center")
        for k, linha in enumerate(self.legado[:2]):  # o Legado, num canto discreto
            cor = alpha(SANGUE_VIVO, 200) if linha.startswith("Nêmesis") else alpha(TINTA, 120)
            self._t(r, 24, 18 + k * 20, linha, 13, cor)
        y0, passo = self._layout()
        ysel = self.y_sel if self.y_sel is not None else y0 + self.cursor * passo
        entrou = self.cartas.surgiu(self.cursor)
        if entrou > 0:  # a faixa da seleção desliza entre as linhas
            r.draw_ui_rect(230, ysel - 4, 500, passo - 3, alpha(LACA, 255 * entrou))
            r.draw_ui_polygon(
                [(244, ysel + 3), (254, ysel + 10), (244, ysel + 17)], alpha(OURO, 255 * entrou)
            )
        for i, (acao, texto, detalhe) in enumerate(self.itens):
            y = y0 + i * passo
            foco = self.cartas.foco_de(i)
            especial = acao in ("continuar", "diaria", "jogo", "anime")
            cor = alpha(OURO if especial else TINTA, 120 + 135 * foco)
            c = self.cartas.camada(r, i, (480, y))
            self._t(c, 266 + 6 * foco, y - 2, texto, 18, cor)
            self._t(c, 718, y + 2, detalhe, 13, alpha(TINTA, 100), "topright")
        self._t(
            r,
            480,
            ALTURA - 28,
            "↑ ↓ escolhe · ← → muda o modo · Enter começa · G grimório · C crônica · O opções",
            14,
            alpha(TINTA, 100),
            "center",
        )
        if self.modo_asc is not None:
            self._painel_ascensao(r)
        vfx.vinheta(r, 0.9)
        vfx.grao(r, t, 140)
        transicoes.revelar(self, r, t)

    def _painel_ascensao(self, r: IRenderer) -> None:
        """A escolha do degrau: o nível, o que ele faz e tudo o que ele acumula."""
        surge = suave(self.t_asc / 0.2)
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(FUNDO, 170 * surge))
        c = Camada(r, (480, 440), 0.97 + 0.03 * surge, 0, 12 * (1 - surge), surge)
        x0, y0, x1, y1 = 150, 236, 810, 584
        c.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 250))
        moldura(c, x0, y0, x1, y1, OURO)
        modo = self.modo_asc or ""
        maximo = self.ascensoes.get(modo, 0)
        nome_modo = next((d["nome"] for m, d in self.modos if m == modo), modo)
        n = self.nivel_asc
        self._t(c, x0 + 24, y0 + 16, "昇  Ascensão", 24, OURO)
        aberta = f"{nome_modo} · aberta até {maximo}"
        self._t(c, x1 - 24, y0 + 24, aberta, 14, alpha(TINTA, 140), "topright")
        niveis = carregar_ascensao()
        cx = x0 + 74
        if n == 0:
            self._t(c, cx, y0 + 108, "業", 56, alpha(TINTA, 110), "center")
            titulo, texto = "Sem Ascensão", "A run de sempre, sem degrau nenhum."
        else:
            nivel = niveis[n - 1]
            self._t(c, cx, y0 + 108, nivel.kanji, 64, OURO, "center")
            titulo, texto = f"Ascensão {n} · {nivel.nome}", nivel.texto
        self._t(c, x0 + 140, y0 + 68, f"←  {titulo}  →", 20, TINTA)
        for k, linha in enumerate(quebrar(texto, 54)[:2]):
            self._t(c, x0 + 140, y0 + 100 + k * 22, linha, 16, alpha(TINTA, 190))
        acumula = niveis_ate(n)
        if acumula:
            self._t(c, x0 + 24, y0 + 160, "Vale tudo o que vem antes:", 14, alpha(TINTA, 130))
            for k, nv in enumerate(acumula):
                x = x0 + 24 + (k // 5) * 320
                y = y0 + 186 + (k % 5) * 24
                cor = OURO if nv.nivel == n else alpha(TINTA, 170)
                self._t(c, x, y, f"{nv.kanji} {nv.nivel}. {nv.nome}", 15, cor)
        else:
            texto = "Vencer abre o próximo degrau nesta dificuldade."
            self._t(c, x0 + 24, y0 + 170, texto, 14, alpha(TINTA, 130))
        dica = "← → escolhe o degrau · Enter começa · Backspace volta"
        self._t(c, 480, y1 - 26, dica, 13, alpha(TINTA, 120), "center")

    def _brasas(self, r: IRenderer, t: float) -> None:
        """Brasas e cinzas subindo do chão, com um leve tremor de chama."""
        for i in range(22):
            s = i * 7.31
            vida = (t * (0.07 + 0.03 * abs(math.sin(s))) + abs(math.sin(s * 1.9))) % 1.0
            x = (math.sin(s * 3.7) * 0.5 + 0.5) * LARGURA + math.sin(t * 0.9 + s) * 26 * vida
            y = ALTURA + 10 - vida * (ALTURA * 0.85)
            forca = math.sin(vida * math.pi) * (0.7 + 0.3 * math.sin(t * 9 + s))
            if i % 3 == 0:  # cinza: maior, apagada
                r.draw_ui_circle(x, y, 2.4, alpha(FERRO, 70 * forca))
                continue
            cor = mistura(SANGUE_VIVO, OURO, 0.3 + 0.5 * abs(math.sin(s * 2.3)))
            r.draw_ui_circle(x, y, 5.5, alpha(cor, 34 * forca))
            r.draw_ui_circle(x, y, 2.0, alpha(cor, 225 * forca))

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
        self.cartas = Cartas(sobe=36, lado=True)
        self.cartas.t = -0.12  # a técnica nova aparece primeiro
        self.ys: dict[int, float] = {}  # onde cada linha está (desliza até o alvo)
        self.alvos: dict[int, float] = {}
        self.fixo = None  # (nova, técnicas) no momento da escolha: a tela sai mostrando isso
        # a nova é uma fusão que nasceu sem espaço (a Jornada retoma sozinha depois)
        nova = jornada.pendente
        self.fusao = (
            bool(jornada.retomar) and nova is not None and fusao_de(jornada, nova) is not None
        )
        self.pista = pista(jornada.estado, nova.id, jornada.ctx.fusoes) if nova else Pista()
        self.perdas = [
            perda(jornada.estado, t.id, nova.id if nova else "", jornada.ctx.fusoes)
            for t in jornada.jogador.tecnicas
        ]

    @property
    def segurar_saida(self) -> float:
        return 0.14 if self.cartas.escolhida is not None else 0.0

    def _animar(self, dt: float) -> None:
        self.cartas.avancar(dt, self.cursor, len(self.j.jogador.tecnicas))
        puxa = 1 - math.exp(-dt * OPCOES.velocidade * 16)
        for i, alvo in self.alvos.items():
            self.ys[i] = self.ys.get(i, alvo) + (alvo - self.ys.get(i, alvo)) * puxa

    def _sai(self, i: int | None) -> None:
        """Troca a técnica `i` pela nova (None: descarta a nova)."""
        tecnicas = self.j.jogador.tecnicas
        self.fixo = (self.j.pendente, list(tecnicas))
        if i is None:
            self.j.substituir(None)
        else:
            som.tocar("confirmar")
            self.cursor = i
            self.cartas.escolher(i)
            self.j.substituir(tecnicas[i])
        self.ao_concluir()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        e = self.entrada
        tecnicas = self.j.jogador.tecnicas
        for i in range(len(tecnicas)):
            if e.is_action_pressed(f"tecnica_{i + 1}"):
                self._sai(i)
                return
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(tecnicas)
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(tecnicas)
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            self._sai(self.cursor)
            return
        if e.is_action_pressed("cancelar"):
            self._sai(None)

    def _linhas(self, fatia, todas: bool) -> list[str]:
        """O texto da técnica: inteiro, ou só a primeira linha (com … se houver mais)."""
        linhas = quebrar(fatia.texto if fatia else "", LARGURA_TEXTO_TROCA)
        if todas or len(linhas) <= 1:
            return linhas
        return [linhas[0].rstrip(" ,.;:") + "…"]

    def _linha(self, r, y, t, fatia, linhas: list[str], numero: str = "", foco=1.0) -> None:
        cor = self.cores.get(t.raridade, TINTA)
        if numero:
            self._t(r, 220, y + 8, numero, 22, alpha(TINTA, 150))
        kanji = fatia.kanji if fatia else "?"
        if linhas:
            self._t(r, 260, y, kanji, 40, cor)
        else:  # linha compacta, só o nome: o kanji menor, para não invadir a vizinha
            self._t(r, 266, y + 2, kanji, 28, cor)
        self._t(r, 320, y + 4, t.nome, 22, cor)
        for k, linha in enumerate(linhas):  # o texto inteiro da escolhida acende aos poucos
            self._t(r, 320, y + 32 + k * 18, linha, 15, alpha(TINTA, 150 * (1 if k == 0 else foco)))

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        nova, tecnicas = self.fixo or (self.j.pendente, self.j.jogador.tecnicas)
        fatias = fatias_das_tecnicas(self.j)
        n = len(tecnicas)
        cheios = f"Seus {EXTENSO.get(n, str(n))} espaços estão cheios"
        surge = suave((self.cartas.t + 0.12) / 0.3)
        topo = Camada(r, (480, 100), 1.0, 0, -12 * (1 - surge), surge)
        self._t(topo, 480, 40, cheios, 26, TINTA, "center")
        if self.fusao:
            self._t(topo, 220, 92, "融 Fusão nova: escolha o lugar dela", 16, alpha(OURO, 220))
        else:
            self._t(topo, 220, 92, "Técnica nova", 16, alpha(OURO, 200))
            selo = texto_da_pista(self.pista, self.j.grimorio)
            if selo:
                self._t(topo, 900, 92, selo, 15, alpha(OURO, 220), "topright")
        linhas = self._linhas(nova, todas=True)
        self._linha(topo, 114, Tecnica.de_fatia(nova), nova, linhas)
        y = 114 + 32 + len(linhas) * 18 + 12
        self._t(topo, 220, y, "Qual sai?", 16, alpha(TINTA, 150))
        y += 36
        # a escolhida mostra o texto inteiro; as outras, uma linha (ou só o nome, se apertar)
        textos = [
            self._linhas(fatias.get(t.id), todas=i == self.cursor) for i, t in enumerate(tecnicas)
        ]
        if y + sum(38 + 18 * len(ls) for ls in textos) > ALTURA - 48:
            textos = [ls if i == self.cursor else [] for i, ls in enumerate(textos)]
        for i, t in enumerate(tecnicas):
            atual = i == self.cursor
            linhas = textos[i]
            altura = 32 + len(linhas) * 18
            if atual:
                y += 6  # folga para o destaque não raspar nas vizinhas
            self.alvos[i] = y
            ya = self.ys.setdefault(i, y)
            foco = self.cartas.foco_de(i)
            c = self.cartas.camada(r, i, (560, ya + altura / 2))
            if foco > 0.02:
                c.draw_ui_rect(200, ya - 6, 720, altura + 8, alpha(LACA, 255 * foco))
                c.draw_ui_polygon(
                    [(206, ya + 12), (214, ya + 18), (206, ya + 24)], alpha(OURO, 255 * foco)
                )
            self._linha(c, ya, t, fatias.get(t.id), linhas, str(i + 1), foco)
            aviso = texto_da_perda(self.perdas[i]) if i < len(self.perdas) else ""
            if aviso:  # tirar esta desfaz uma Ressonância ou leva uma peça de fusão
                self._t(c, 904, ya + 8, aviso, 13, alpha(SANGUE_VIVO, 150 + 80 * foco), "topright")
            if i == self.cartas.escolhida:
                self.cartas.selo(r, 880, ya + altura / 2, "去")
            y += altura + (12 if atual else 6)
        self._t(
            r,
            480,
            ALTURA - 32,
            f"1–{n} (ou ↑ ↓ e Enter) troca · Backspace descarta a nova",
            15,
            alpha(TINTA, 110),
            "center",
        )


# ----------------------------------------------------------------------- treino


class TreinoScene(_Base):
    """Depois da vitória: 1 de 3 treinos, que ficam pelo resto da run."""

    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.cursor = 0
        self.cartas = Cartas()
        self.fixo = None  # a oferta no momento da escolha (a Jornada a limpa)

    @property
    def segurar_saida(self) -> float:
        return 0.14 if self.cartas.escolhida is not None else 0.0

    def _animar(self, dt: float) -> None:
        self.cartas.avancar(dt, self.cursor, len(self.fixo or self.j.oferta_treino))

    def _escolher(self, i: int) -> None:
        som.tocar("confirmar")
        self.fixo = list(self.j.oferta_treino)
        self.cursor = i
        self.cartas.escolher(i)
        self.j.escolher_treino(i)
        self.ao_concluir()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        e = self.entrada
        n = len(self.j.oferta_treino)
        for i in range(n):
            if e.is_action_pressed(f"escolher_{i + 1}") or e.is_action_pressed(f"tecnica_{i + 1}"):
                self._escolher(i)
                return
        if e.is_action_pressed("esquerda"):
            self.cursor = (self.cursor - 1) % n
            som.tocar("mover")
        elif e.is_action_pressed("direita"):
            self.cursor = (self.cursor + 1) % n
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            self._escolher(self.cursor)

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        _particulas(r, t, 18, alpha(OURO, 60), sobe=True, tam=1.6, vel=18, semente=3)
        self._t(r, 480, 46, "修  Treino", 34, OURO, "center")
        self._t(
            r,
            480,
            92,
            "Os rivais ficam mais fortes a cada luta. Você também: escolha um.",
            17,
            alpha(TINTA, 170),
            "center",
        )
        oferta = self.fixo or self.j.oferta_treino
        largura, altura, folga = 260, 300, 30
        x0 = 480 - (len(oferta) * largura + (len(oferta) - 1) * folga) / 2
        pulso = self.cartas.pulso()
        for i, tr in enumerate(oferta):
            x, y = x0 + i * (largura + folga), 150
            foco = self.cartas.foco_de(i)
            c = self.cartas.camada(r, i, (x + largura / 2, y + altura / 2))
            c.draw_ui_rect(x, y, largura, altura, alpha(LACA, 110 + 145 * foco))
            if foco > 0.02:  # a borda da escolhida pulsa
                borda = alpha(OURO, (150 + 105 * pulso) * foco)
                c.draw_ui_rect(x, y, largura, 3, borda)
                c.draw_ui_rect(x, y + altura - 3, largura, 3, borda)
            cor = mistura(TINTA, OURO, foco)
            cx = x + largura / 2
            self._t(c, cx, y + 60, tr.kanji, 64, cor, "center")
            self._t(c, cx, y + 124, tr.nome, 20, cor, "center")
            for k, linha in enumerate(quebrar(tr.texto, 26)[:3]):
                self._t(c, cx, y + 162 + k * 22, linha, 16, alpha(TINTA, 190), "center")
            for k, linha in enumerate(quebrar(tr.origem, 30)[:2]):
                self._t(c, cx, y + 254 + k * 16, linha, 12, alpha(TINTA, 110), "center")
            self._t(c, x + 14, y + 10, str(i + 1), 18, alpha(TINTA, 120))
            if i == self.cartas.escolhida:
                self.cartas.selo(r, x + largura - 26, y + 30, "修")
        jg = self.j.jogador
        estado = (
            f"Vida {jg.vida}/{jg.vida_max} · Velocidade {jg.velocidade} · "
            f"Percepção {jg.percepcao} · Dano +{jg.dano_run}"
        )
        self._t(r, 480, 492, estado, 17, alpha(TINTA, 160), "center")
        build = resumo_do_build(self.j)
        if build:  # as Ressonâncias, o aliado e a Ascensão, discretos
            self._t(r, 480, 522, build, 14, alpha(OURO, 160), "center")
        self._t(
            r,
            480,
            ALTURA - 32,
            "1–3 (ou ← → e Enter) escolhe",
            15,
            alpha(TINTA, 110),
            "center",
        )
        transicoes.revelar(self, r, t)


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
        self.cartas = self._linhas_animadas()
        self.cartas_compra = self._linhas_animadas()
        self.t_anim = 0.0  # o relógio do enfeite (na velocidade das opções)
        self.marcou: dict[str, float] = {}  # quando cada restrição/ganho foi marcado (o carimbo)

    @staticmethod
    def _linhas_animadas() -> Cartas:
        c = Cartas(sobe=30, lado=True)
        c.ATRASO = 0.035  # muitas linhas: o escalonamento é mais curto
        return c

    @property
    def segurar_saida(self) -> float:
        return 0.16 if self.cartas_compra.escolhida is not None else 0.0

    def _animar(self, dt: float) -> None:
        self.t_anim += dt * OPCOES.velocidade
        self.cartas.avancar(dt, self.cursor, len(self.linhas))
        self.cartas_compra.avancar(dt, self.cursor_compra, len(self.linhas_compra))

    def _pop(self, chave: str) -> float:
        """A escala da marca recém-feita: cresce e assenta."""
        if chave not in self.marcou:
            return 1.0
        return carimbo((self.t_anim - self.marcou[chave]) / 0.26)

    @property
    def linhas(self) -> list[str]:
        return [r.id for r in self.restricoes] + ["duracao", "pesar", "recusar"]

    def _pode_medir(self) -> bool:
        """Mede depois de um quadro com "o Altar pesa...". Na primeira vez, quando o Fluxo
        cuida da entrada, espera a tinta abrir: a medida trava a tela por um ou dois
        segundos, e a frase precisa estar à vista (não a transição congelada no meio)."""
        if self.quadros <= 1:
            return False
        primeira = self.pesos is None and getattr(self, "sem_revelar", False)
        return not primeira or self.relogio * OPCOES.velocidade >= 0.45

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        self.quadros += 1
        if self._sair():
            return
        if self.estado == "pesar":  # um quadro com "o Altar pesa..." antes de medir
            if self._pode_medir():
                primeira = self.pesos is None
                self.pesos = self.j.pesar_restricoes(self.duracao)
                self.estado = "escolher"
                if primeira:  # as linhas entram agora, não durante a espera
                    self.cartas = self._linhas_animadas()
            return
        if self.estado == "propor":
            if self.quadros > 1:
                self.proposta = self.j.propor_voto(sorted(self.marcadas), self.duracao)
                self.compra = list(self.proposta.voto.ganhos)  # a sugestão do Altar
                self.cursor_compra = 0
                self.estado = "comprar"
                self.cartas_compra = self._linhas_animadas()
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
                self.marcou[item] = self.t_anim
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
                self.cartas_compra.escolher(self.cursor_compra)
                self.j.jurar(self.proposta, self.compra)
                self.ao_concluir()
            elif item == "voltar":
                self.estado = "escolher"
            elif self.proposta.cabe(self.j.ctx, self.compra, item):
                self.compra.append(item)
                self.marcou[item.id] = self.t_anim
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
            transicoes.revelar(self, r, self.relogio)
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
        tela = r
        for i in self.rol.faixa(n):
            res = self.restricoes[i]
            y = self.rol.y(i, 112, 44)
            r = self.cartas.camada(tela, i, (480, y + 14), ordem=i - self.rol.topo)
            foco = self.cartas.foco_de(i)
            if foco > 0.02:  # o destaque desliza de uma linha para a outra
                r.draw_ui_rect(30, y - 6, 900, 40, alpha(LACA, 255 * foco))
            marcada = res.id in self.marcadas
            caixa = 18 * (self._pop(res.id) if marcada else 1.0)
            cor_caixa = OURO if marcada else alpha(FERRO, 160)
            r.draw_ui_rect(53 - caixa / 2, y + 13 - caixa / 2, caixa, caixa, cor_caixa)
            self._t(r, 76, y - 2, res.kanji, 26, SANGUE_VIVO if marcada else TINTA)
            self._t(r, 116, y, res.nome, 19, TINTA)
            self._t_ajustado(r, 300, y + 3, res.texto, 44, 15, alpha(TINTA, 140))
            peso = (self.pesos or {}).get(res.id, 0.0)
            if peso <= 0.05:
                rotulo, cor = "não custa nada a você", alpha(TINTA, 90)
            else:
                extra = " (teto)" if peso > teto else ""
                rotulo, cor = f"custa ~{peso:.1f} luta{extra}".replace(".", ","), SANGUE_VIVO
            self._t(r, 920, y + 3, rotulo, 15, cor, "topright")
        r = tela
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
            c = self.cartas.camada(r, i, (240, y + 10), ordem=min(n, self.rol.visiveis) + k)
            foco = self.cartas.foco_de(i)
            if foco > 0.02:
                c.draw_ui_rect(30, y - 6, 420, 32, alpha(LACA, 255 * foco))
            self._t(c, 52 + 6 * foco, y - 2, texto, 18, OURO if item == "pesar" else TINTA)
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
        tela = r
        for i in self.rol_compra.faixa(ng):
            g = ganhos[i]
            y = self.rol_compra.y(i, 136, 34)
            r = self.cartas_compra.camada(tela, i, (480, y + 10), ordem=i - self.rol_compra.topo)
            foco = self.cartas_compra.foco_de(i)
            if foco > 0.02:
                r.draw_ui_rect(30, y - 5, 900, 32, alpha(LACA, 255 * foco))
            n = self._niveis(g)
            cabe = p.cabe(self.j.ctx, self.compra, g)
            cor = OURO if n else (TINTA if cabe else alpha(TINTA, 80))
            self._t(r, 52, y - 2, g.kanji, 22, cor)
            self._t(r, 88, y, g.nome, 17, cor)
            cor_texto = alpha(TINTA, 150 if cabe or n else 70)
            self._t_ajustado(r, 260, y + 2, g.texto, 52, 14, cor_texto)
            pop = self._pop(g.id)  # o último nível comprado cresce e assenta
            if g.niveis > 1:
                for k in range(g.niveis):
                    cheio = k < n
                    r.draw_ui_circle(
                        770 + k * 18,
                        y + 10,
                        6 * (pop if k == n - 1 else 1.0),
                        OURO if cheio else alpha(FERRO, 160),
                        0 if cheio else 1,
                    )
            elif n:
                r.draw_ui_circle(770, y + 10, 6 * pop, OURO)
            if not cabe and n < g.niveis:
                self._t(r, 920, y + 2, "não cabe", 13, alpha(TINTA, 90), "topright")
        r = tela
        base = 136 + min(ng, self.rol_compra.visiveis) * 34 + 6
        for k, (item, texto) in enumerate(
            (("jurar", "Jurar este voto"), ("voltar", "Voltar às restrições"))
        ):
            y = base + k * 30
            i = ng + k
            ordem = min(ng, self.rol_compra.visiveis) + k
            c = self.cartas_compra.camada(r, i, (240, y + 10), ordem=ordem)
            foco = self.cartas_compra.foco_de(i)
            if foco > 0.02:
                c.draw_ui_rect(30, y - 5, 420, 28, alpha(LACA, 255 * foco))
            self._t(c, 52 + 6 * foco, y - 2, texto, 17, OURO if item == "jurar" else TINTA)
            if i == self.cartas_compra.escolhida:
                self.cartas_compra.selo(r, 410, y + 9, "誓", 26)
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
    """O fim da run. Tudo aparece em sequência: o grito, as linhas (as lutas vencidas
    contando), os Feitos e o Legado (a Memória contando). Enter pula a sequência; com
    ela inteira na tela, Enter volta ao título."""

    INICIO = 0.55  # as linhas começam depois do grito do fim
    PASSO = 0.2  # entre uma linha e a próxima
    SURGE = 0.32  # cada linha surgindo
    CONTA = 0.7  # as contagens (lutas vencidas, Memória)

    def __init__(
        self,
        jornada: Jornada,
        entrada,
        ao_reiniciar,
        ao_sair,
        recorde=None,
        feitos=(),
        fechamento: Fechamento | None = None,
        proximo: tuple[str, int] | None = None,
    ) -> None:
        """`fechamento`: o que a run deixou no Legado; `proximo`: o próximo anime a abrir
        e a Memória que falta (None: todos abertos)."""
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_reiniciar = ao_reiniciar
        self.recorde = recorde  # o melhor da semente do dia, se era uma
        self.feitos = list(feitos)  # os Feitos conquistados nesta run
        self.fechamento = fechamento
        self.proximo = proximo
        self.t_seq = 0.0  # o relógio da sequência (na velocidade das opções)
        self.contou = 0  # quantas lutas a contagem já mostrou (um tique a cada uma)

    # --------------------------------------------------------------- a sequência

    def _animar(self, dt: float) -> None:
        self.t_seq += dt * OPCOES.velocidade

    def _agenda(self) -> tuple[list[float], list[float], float, list[float], float]:
        """Quando cada coisa aparece: (linhas, Feitos, título do Legado, linhas do Legado, fim)."""
        n = len(self.linhas())
        linhas = [self.INICIO + k * self.PASSO for k in range(n)]
        t = (linhas[-1] if linhas else self.INICIO) + self.PASSO
        feitos = [t + k * 0.3 for k in range(len(self.feitos[:3]))]
        t = (feitos[-1] + 0.3) if feitos else t
        legado = [t + 0.15 + k * 0.18 for k in range(len(self.linhas_legado()))]
        fim = max([t, *legado, *linhas]) + self.SURGE
        if self.fechamento is not None and legado:
            fim = max(fim, legado[0] + self.CONTA)
        if linhas:
            fim = max(fim, linhas[0] + self.CONTA)
        return linhas, feitos, t, legado, fim

    @property
    def terminou(self) -> bool:
        return self.t_seq >= self._agenda()[-1]

    def _surgiu(self, t0: float) -> float:
        return ease_out(max(0.0, min(1.0, (self.t_seq - t0) / self.SURGE)))

    def _conta(self, t0: float, total: int) -> int:
        """A contagem crescendo de 0 a `total`, começando em `t0`."""
        k = max(0.0, min(1.0, (self.t_seq - t0) / self.CONTA))
        return round(total * ease_out(k))

    def update(self, world, delta_time: float) -> None:
        if self.relogio == 0.0:
            som.musica(None)
            som.tocar("vitoria" if self.j.fase == "vitoria" else "derrota")
        self.relogio += delta_time
        self._animar(delta_time)
        agenda = self._agenda()
        if agenda[0]:
            n = self._conta(agenda[0][0], self.j.estado.lutas_vencidas)
            if n != self.contou:
                self.contou = n
                som.tocar("tique")
        if self._sair():
            return
        if self.entrada.is_action_pressed("confirmar"):
            if self.terminou:
                self.ao_reiniciar()
            else:  # o primeiro Enter só mostra tudo de uma vez
                self.t_seq = agenda[-1]

    # --------------------------------------------------------------- o texto

    def linhas(self, vencidas: int | None = None) -> list[str]:
        """O resumo da run, sem as linhas vazias (`vencidas`: o número da contagem)."""
        j = self.j
        torre = getattr(j.ctx, "jogo", "classico") == "torre"
        modo = j.ctx.combate["dificuldades"][j.modo]["nome"]
        votos = len(j.estado.votos.ativos) + len(j.estado.votos.quebrados)
        if vencidas is None:
            vencidas = j.estado.lutas_vencidas
        if torre:
            placar = f"Torre sem fim · {modo} · {vencidas} andares"
            if self.recorde is not None:
                placar += f" · seu melhor: {self.recorde}"
        else:
            jogo = {"anime": f"Mundo de {j.ctx.anime}", "chefes": "Desfile de chefes"}
            prefixo = f"{jogo[j.ctx.jogo]} · " if j.ctx.jogo in jogo else ""
            placar = f"{prefixo}{modo} · {vencidas} de {j.ctx.lutas} lutas vencidas"
        if getattr(j, "ascensao", 0):
            placar = placar.replace(f"{modo} · ", f"{modo} 昇{j.ascensao} · ", 1)
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
        return [x for x in linhas if x]

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
        else:  # as correntes fecham sobre quem caiu
            _particulas(r, t, 30, alpha(SANGUE_VIVO, 90), sobe=False, tam=2.0, vel=20, semente=9)
            desenhar_lutador(r, 480, 300, 1.5, (60, 22, 24, 255), alpha(TINTA, 200), tempo=t)
            vfx.correntes_fechando(r, 480, 220, min(1.0, t / 1.4))
        grito = suave(self.t_seq / 0.35)  # o grito do fim bate na tela e assenta
        c = Camada(r, (480, 352), carimbo(min(1.0, self.t_seq / 0.45)), 0, 0, grito)
        if venceu:
            self._t(c, 480, 330, "勝  O torneio é seu", 44, OURO, "center")
        else:
            fim = "塔  A torre cobrou o preço" if torre else "敗  Seu destino terminou aqui"
            self._t(c, 480, 330, fim, 40, SANGUE_VIVO, "center")
        quando, feitos, t_legado, legado, _ = self._agenda()
        if quando:
            textos = self.linhas(self._conta(quando[0], j.estado.lutas_vencidas))
            for k, (linha, t0) in enumerate(zip(textos, quando, strict=False)):
                surge = self._surgiu(t0)
                c = Camada(r, (480, 400), 1.0, 0, 12 * (1 - surge), surge)
                self._t(c, 480, 400 + k * 28, linha, 17, alpha(TINTA, 170), "center")
        for k, (f, t0) in enumerate(zip(self.feitos[:3], feitos, strict=False)):  # no alto
            surge = self._surgiu(t0)
            c = Camada(r, (480, 36 + k * 26), carimbo(surge) if surge < 1 else 1.0, 0, 0, surge)
            self._t(c, 480, 24 + k * 26, f"{f.kanji}  Feito: {f.nome}", 18, OURO, "center")
        self._legado(r, t_legado, legado)
        self._t(
            r, 480, ALTURA - 30, "Enter volta ao título · esc sai", 15, alpha(TINTA, 110), "center"
        )
        transicoes.revelar(self, r, t)

    def linhas_legado(self, memoria: int | None = None) -> list[tuple[str, tuple]]:
        """O que ficou para a próxima run, em poucas linhas: (texto, cor).
        `memoria`: o número da contagem (None: o ganho inteiro)."""
        f = self.fechamento
        if f is None:
            return []
        linhas: list[tuple[str, tuple]] = []
        if self.proximo is None:
            resto = "todos os animes abertos"
        else:
            resto = f"próximo anime: {self.proximo[0]}, faltam {self.proximo[1]}"
        ganho = f.memoria if memoria is None else memoria
        linhas.append((f"憶 Memória +{ganho} · {resto}", TINTA))
        if f.animes:
            plural = "Anime aberto" if len(f.animes) == 1 else "Animes abertos"
            linhas.append((f"開 {plural}: {', '.join(f.animes)}", OURO))
        aberta = getattr(f, "ascensao_aberta", 0)
        if aberta:
            linhas.append((f"昇 Ascensão {aberta} aberta", OURO))
        for nivel in (2, 1):
            nomes = [nome for nome, n in f.maestrias if n == nivel]
            if nomes:
                linhas.append((f"{'★' * nivel} Maestria: {', '.join(nomes)}", OURO))
        nome = f.nemesis_nome
        if f.nemesis == "nasceu":
            linhas.append((f"仇 Nêmesis nasceu: {nome} — ela volta na próxima run", SANGUE_VIVO))
        elif f.nemesis == "cresceu":
            linhas.append((f"仇 Nêmesis: {nome} ficou mais forte", SANGUE_VIVO))
        elif f.nemesis == "vingada":
            linhas.append((f"仇 Nêmesis vingada: {nome}", OURO))
        return linhas[:5]

    def _legado(self, r: IRenderer, t_titulo: float, quando: list[float]) -> None:
        """O Legado, dos dois lados da figura (depois de tudo, linha a linha): à esquerda
        a Memória e os animes; à direita a Maestria e a Nêmesis."""
        if self.fechamento is None or not quando:
            return
        memoria = self._conta(quando[0], self.fechamento.memoria)
        linhas = list(zip(self.linhas_legado(memoria), quando, strict=False))
        if not linhas:
            return
        brilho = self._surgiu(t_titulo)
        self._t(r, 36, 104, "遺  O que fica", 18, alpha(OURO, 220 * brilho))
        esquerda = [x for x in linhas if x[0][0][0] in "憶開"]
        direita = [x for x in linhas if x[0][0][0] not in "憶開"]
        for x, y, largura, coluna in ((36, 140, 24, esquerda), (704, 104, 26, direita)):
            for (texto, cor), t0 in coluna:
                surge = self._surgiu(t0)
                c = Camada(r, (x, y), 1.0, -14 * (1 - surge), 0, surge)
                for k, linha in enumerate(quebrar(texto, largura)[:3]):
                    recuo = 0 if k == 0 else 20
                    self._t(c, x + recuo, y, linha, 15, alpha(cor, 200))
                    y += 20
                y += 10


# ----------------------------------------------------------------------- anúncios


class _Anuncio(_Base):
    """Um anúncio entre duas fases: uma sequência que Enter adianta; com ela inteira na
    tela, Enter segue. O selo vermelho carimba quando a sequência chega a `CARIMBA`."""

    CARIMBA = 0.5
    TOTAL = 1.2

    def __init__(self, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.ao_concluir = ao_concluir
        self.t_seq = 0.0  # o relógio da sequência (na velocidade das opções)
        self.selo = Cartas()

    @property
    def terminou(self) -> bool:
        return self.t_seq >= self.TOTAL

    def _animar(self, dt: float) -> None:
        self.t_seq += dt * OPCOES.velocidade
        if self.t_seq >= self.CARIMBA and self.selo.escolhida is None:
            self.selo.escolher(0)
            som.tocar("revela_divino")
        self.selo.avancar(dt, 0, 1)

    def _seguir(self) -> None:
        """Enter com a sequência inteira: o próximo (ou o fim)."""
        self.ao_concluir()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        e = self.entrada
        if e.is_action_pressed("confirmar") or e.is_action_pressed("girar"):
            if self.terminou:
                som.tocar("confirmar")
                self._seguir()
            else:  # o primeiro Enter só mostra tudo de uma vez
                self.t_seq = max(self.t_seq, self.TOTAL)
                self._animar(0.0)

    def _surge(self, t0: float, dur: float = 0.3) -> float:
        return ease_out(max(0.0, min(1.0, (self.t_seq - t0) / dur)))


class FusaoScene(_Anuncio):
    """融合: as peças de uma fusão entram, correm uma para a outra e se fundem; a técnica
    nova carimba no centro (kanji, nome, texto, origem). Uma por vez, se nasceu mais de
    uma. Quem mostra é o Fluxo, entre duas fases; a Jornada já fez a fusão."""

    ENTRAM = 0.5  # as peças surgindo
    CORREM = 0.95  # as peças correm para o centro e somem
    CARIMBA = 1.15  # a técnica nova carimba
    TOTAL = 1.9  # o texto inteiro na tela

    def __init__(self, jornada: Jornada, fatias, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_concluir, ao_sair)
        self.j = jornada
        self.fatias: list[Fatia] = list(fatias)
        self.i = 0
        self.cores = {r.id: hex_cor(r.cor) for r in jornada.ctx.raridades}
        self.nomes_raridade = {r.id: r.nome for r in jornada.ctx.raridades}
        self.pecas = []
        for f in self.fatias:
            fusao = fusao_de(jornada, f)
            self.pecas.append(pecas_da_fusao(jornada, fusao) if fusao else [])

    def _seguir(self) -> None:
        if self.i + 1 < len(self.fatias):
            self.i += 1
            self.t_seq = 0.0
            self.selo = Cartas()
        else:
            self.ao_concluir()

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        f = self.fatias[self.i]
        cor = self.cores.get(f.raridade, OURO)
        clara = mistura(cor, TINTA, 0.25)
        _particulas(r, t, 24, alpha(clara, 70), sobe=True, tam=1.8, vel=22, semente=13)
        self._t(r, 480, 34, "融合  Fusão", 30, OURO, "center")
        if len(self.fatias) > 1:
            self._t(
                r, 900, 44, f"{self.i + 1} de {len(self.fatias)}", 14, alpha(TINTA, 130), "topright"
            )
        pecas = self.pecas[self.i]
        receita = "  +  ".join(nome for _, _, nome in pecas)
        self._t(r, 480, 80, receita, 16, alpha(TINTA, 150 * self._surge(0.1)), "center")
        self._pecas(r, pecas, clara)
        self._nasce(r, f, cor, clara)
        fim = "Enter continua" if self.terminou else "Enter mostra tudo"
        self._t(r, 480, ALTURA - 32, fim, 15, alpha(TINTA, 110), "center")
        transicoes.revelar(self, r, t)

    def _pecas(self, r: IRenderer, pecas, cor) -> None:
        """As peças: entram escalonadas e, depois, correm para o centro e se apagam."""
        n = len(pecas)
        if not n:
            return
        largura, passo, y = 188, 214, 210
        x0 = 480 - passo * (n - 1) / 2
        corre = suave((self.t_seq - self.ENTRAM) / (self.CORREM - self.ENTRAM))
        if corre >= 1:
            return
        for k, (tipo, fatia, nome) in enumerate(pecas):
            surge = self._surge(k * 0.12)
            x = x0 + k * passo
            cx = x + (480 - x) * corre
            c = Camada(
                r,
                (x, y),
                (0.9 + 0.1 * surge) * (1 - 0.6 * corre),
                cx - x,
                18 * (1 - surge),
                surge * (1 - corre),
            )
            c.draw_ui_rect(x - largura / 2, y - 70, largura, 140, alpha(LACA, 240))
            moldura(c, x - largura / 2, y - 70, x + largura / 2, y + 70, alpha(cor, 200))
            kanji = fatia.kanji if fatia else "？"
            self._t(c, x, y - 30, kanji, 44, cor, "center")
            for j, linha in enumerate(quebrar(nome, 20)[:2]):
                self._t(c, x, y + 8 + j * 18, linha, 15, TINTA, "center")
            self._t(c, x, y + 48, NOME_REQUISITO.get(tipo, tipo), 12, alpha(TINTA, 120), "center")
            if k < n - 1 and corre < 0.05:  # o + entre as peças
                self._t(c, x + passo / 2, y - 12, "+", 26, alpha(OURO, 200), "center")
        if corre > 0:  # os fios de luz puxando as peças
            for k in range(n):
                x = x0 + k * passo
                cx = x + (480 - x) * corre
                r.draw_ui_line(cx, y, 480, y, alpha(OURO, 160 * (1 - corre)), 2)

    def _nasce(self, r: IRenderer, f: Fatia, cor, clara) -> None:
        """O clarão, o kanji que carimba e, linha a linha, o que a técnica é."""
        k = (self.t_seq - self.CORREM) / 0.3
        if 0 <= k < 1:  # o clarão onde as peças se encontram
            r.draw_ui_circle(480, 210, 30 + 220 * ease_out(k), alpha(OURO, 150 * (1 - k)), 4)
            r.draw_ui_circle(480, 210, 70 * (1 - k), alpha(clara, 120 * (1 - k)))
            r.draw_ui_circle(480, 210, 26 * (1 - k), alpha((255, 255, 255, 255), 200 * (1 - k)))
        u = (self.t_seq - self.CARIMBA) / 0.45
        if u < 0:
            return
        surge = min(1.0, u * 3)
        c = Camada(
            r,
            (480, 210),
            carimbo(min(1.0, u)) * (1.6 - 0.6 * ease_out(min(1.0, u * 2))),
            0,
            0,
            surge,
        )
        for a in range(12):  # os raios atrás do kanji
            ang = a * math.pi / 6 + self.relogio * 0.3
            c.draw_ui_line(
                480 + 76 * math.cos(ang),
                210 + 76 * math.sin(ang),
                480 + 104 * math.cos(ang),
                210 + 104 * math.sin(ang),
                alpha(cor, 90),
                2,
            )
        self._t(c, 480, 210, f.kanji, 120, clara, "center")
        self.selo.selo(r, 610, 150, "融", 26)
        linhas = quebrar(f.texto, 66)[:4]
        origem = quebrar(f"※ {f.origem}", 70)[:2] if f.origem else []
        y = 334
        partes = [(f.nome, 30, TINTA, 40), (self.nomes_raridade.get(f.raridade, ""), 16, cor, 34)]
        partes += [(x, 17, alpha(TINTA, 220), 24) for x in linhas]
        partes += [(x, 14, alpha(OURO, 200), 20) for x in origem]
        for k, (texto, tam, cor_t, passo) in enumerate(partes):
            s = self._surge(self.CARIMBA + 0.15 + k * 0.06)
            self._t(
                Camada(r, (480, y), 1.0, 0, 8 * (1 - s), s), 480, y, texto, tam, cor_t, "center"
            )
            y += passo + (8 if k == 1 else 0)


class AliadoScene(_Anuncio):
    """伴: alguém passa a lutar do seu lado. A carta do aliado carimba; Enter segue."""

    CARIMBA = 0.45
    TOTAL = 1.0

    def __init__(
        self, jornada: Jornada, aliado: Aliado, entrada, ao_concluir, ao_sair, motivo: str = ""
    ) -> None:
        super().__init__(entrada, ao_concluir, ao_sair)
        self.j = jornada
        self.aliado = aliado
        self.nivel = max(1, jornada.estado.aliado_nivel)
        self.motivo = motivo or "Alguém da estrada decidiu lutar do seu lado."

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        a = self.aliado
        _particulas(r, t, 18, alpha(VERDE_JADE, 60), sobe=True, tam=1.6, vel=16, semente=17)
        self._t(r, 480, 36, "伴  Um aliado", 32, OURO, "center")
        self._t(r, 480, 82, self.motivo, 16, alpha(TINTA, 160 * self._surge(0.05)), "center")
        x0, y0, x1, y1 = 290, 116, 670, 540
        surge = self._surge(0.1, 0.35)
        c = Camada(
            r,
            (480, 330),
            carimbo(min(1.0, max(0.0, self.t_seq - 0.15) / 0.45)),
            0,
            24 * (1 - surge),
            surge,
        )
        c.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 245))
        moldura(c, x0, y0, x1, y1, VERDE_JADE)
        self._t(c, 480, 196, a.kanji, 96, mistura(VERDE_JADE, TINTA, 0.35), "center")
        self._t(c, 480, 270, a.nome, 30, TINTA, "center")
        self._t(
            c,
            480,
            310,
            f"nível {self.nivel} · cresce a cada luta vencida",
            15,
            alpha(VERDE_JADE, 220),
            "center",
        )
        y = 346
        for linha in quebrar(a.texto, 40)[:6]:
            self._t(c, 480, y, linha, 16, alpha(TINTA, 210), "center")
            y += 22
        if a.origem:
            for k, linha in enumerate(quebrar(f"※ {a.origem}", 44)[:2]):
                self._t(c, 480, 494 + k * 18, linha, 14, alpha(OURO, 200), "center")
        self.selo.selo(r, x1 - 34, y0 + 36, "伴", 26)
        self._t(
            r,
            480,
            566,
            "Os rivais nunca o atacam: ele age no começo dos seus turnos.",
            15,
            alpha(TINTA, 150 * self._surge(0.6)),
            "center",
        )
        fim = "Enter continua" if self.terminou else "Enter mostra tudo"
        self._t(r, 480, ALTURA - 32, fim, 15, alpha(TINTA, 110), "center")
        transicoes.revelar(self, r, t)

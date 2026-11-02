"""Telas de menu da run: título, troca de técnica, Altar dos Votos e fim.

Todas leem e mexem só na `Jornada`; nenhuma decide regra. O Altar mede as
restrições contra o build do jogador (pode levar um ou dois segundos): a tela
desenha "o Altar pesa..." num quadro e mede no seguinte.
"""

from __future__ import annotations

import math

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.arenas import _particulas
from karmabound.combate import Tecnica
from karmabound.figuras import desenhar_lutador
from karmabound.jornada import Jornada, PropostaDeVoto
from karmabound.rodas import carregar_balanceamento
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
    ) -> None:
        super().__init__(entrada, ao_sair)
        self.ao_grimorio = ao_grimorio
        self.ao_opcoes = ao_opcoes
        self.ao_continuar = ao_continuar
        self.ao_diaria = ao_diaria
        cfg = carregar_balanceamento()["combate"]
        self.modos = [(m, d) for m, d in cfg["dificuldades"].items() if not m.startswith("_")]
        # cada linha: (o que faz, texto, detalhe à direita)
        self.itens: list[tuple[str, str, str]] = []
        if continuar and ao_continuar is not None:
            self.itens.append(("continuar", "Continuar a run", continuar))
        if ao_diaria is not None:
            detalhe = (
                f"hoje: {recorde_diaria} de 12"
                if recorde_diaria is not None
                else "Difícil, a mesma sorte para todos"
            )
            self.itens.append(("diaria", "Semente do dia", detalhe))
        self.itens += [(m, d["nome"], f"~{d['alvo_vitoria']:.0%} vencem") for m, d in self.modos]
        padrao = cfg["dificuldade_padrao"]
        self.cursor = (
            0 if continuar else next(i for i, x in enumerate(self.itens) if x[0] == padrao)
        )
        self.ao_escolher = ao_escolher

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
        som.musica("titulo")
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(self.itens)
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(self.itens)
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            som.tocar("confirmar")
            acao = self.itens[self.cursor][0]
            if acao == "continuar":
                self.ao_continuar()
            elif acao == "diaria":
                self.ao_diaria()
            else:
                self.ao_escolher(acao)

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
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
        passo = 36 if len(self.itens) <= 4 else max(24, 168 // len(self.itens))
        y0 = 452 if len(self.itens) <= 4 else 432
        for i, (acao, texto, detalhe) in enumerate(self.itens):
            y = y0 + i * passo
            atual = i == self.cursor
            especial = acao in ("continuar", "diaria")
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
            "↑ ↓ escolhe · Enter começa · G grimório · O opções · esc sai",
            14,
            alpha(TINTA, 100),
            "center",
        )
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
            self._linha(r, 240 + i * 74, t, fatias.get(t.id), str(i + 1))
        self._t(
            r,
            480,
            ALTURA - 32,
            "1–4 troca · Backspace descarta a nova",
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
        for i, res in enumerate(self.restricoes):
            y = 112 + i * 44
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
        base = 112 + len(self.restricoes) * 44 + 8
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
        for i, g in enumerate(self.ganhos):
            y = 136 + i * 34
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
        base = 136 + len(self.ganhos) * 34 + 6
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
    def __init__(self, jornada: Jornada, entrada, ao_reiniciar, ao_sair, recorde=None) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_reiniciar = ao_reiniciar
        self.recorde = recorde  # o melhor da semente do dia, se era uma

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
            self._t(r, 480, 330, "敗  Seu destino terminou aqui", 40, SANGUE_VIVO, "center")
        modo = j.ctx.combate["dificuldades"][j.modo]["nome"]
        votos = len(j.estado.votos.ativos) + len(j.estado.votos.quebrados)
        linhas = [
            f"{modo} · {j.estado.lutas_vencidas} de {j.ctx.lutas} lutas vencidas",
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
        self._t(
            r, 480, ALTURA - 30, "Enter volta ao título · esc sai", 15, alpha(TINTA, 110), "center"
        )
        vfx.revelar(r, t)

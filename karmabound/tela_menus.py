"""Telas de menu da run: título, troca de técnica, Altar dos Votos e fim.

Todas leem e mexem só na `Jornada`; nenhuma decide regra. O Altar mede as
restrições contra o build do jogador (pode levar um ou dois segundos): a tela
desenha "o Altar pesa..." num quadro e mede no seguinte.
"""

from __future__ import annotations

from collections import Counter

from ouroboros.bootstrap.scene import IScene
from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

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
    VERDE_JADE,
    alpha,
    hex_cor,
    quebrar,
)

DURACOES = ("luta", "capitulo", "run")
NOME_DURACAO = {
    "luta": "só esta luta",
    "capitulo": "até o fim do capítulo",
    "run": "o resto da run",
}
DURANTE = {"luta": "Só nesta luta", "capitulo": "Até o fim do capítulo", "run": "Pelo resto da run"}


def _lutas(v: float) -> str:
    """'1,5 luta', '3,7 lutas' — sem sinal; quem chama diz se é a mais ou a menos."""
    v = abs(v)
    return f"{v:.1f} luta".replace(".", ",") + ("s" if v >= 2 else "")


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
    def __init__(self, entrada, ao_escolher, ao_sair, ao_grimorio=None) -> None:
        super().__init__(entrada, ao_sair)
        self.ao_grimorio = ao_grimorio
        cfg = carregar_balanceamento()["combate"]
        self.modos = [(m, d) for m, d in cfg["dificuldades"].items() if not m.startswith("_")]
        padrao = cfg["dificuldade_padrao"]
        self.cursor = next(i for i, (m, _) in enumerate(self.modos) if m == padrao)
        self.ao_escolher = ao_escolher

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        if self._sair():
            return
        e = self.entrada
        if self.ao_grimorio is not None and e.is_action_pressed("grimorio"):
            self.ao_grimorio()
            return
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(self.modos)
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(self.modos)
        elif e.is_action_pressed("confirmar"):
            self.ao_escolher(self.modos[self.cursor][0])

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        r.draw_ui_arc(480, 250, 190, 1.9, 7.5, alpha(TINTA, 16), 14)
        desenhar_lutador(r, 330, 420, 1.25, TINTA, alpha((255, 255, 255, 255), 190), guarda=0.6)
        desenhar_lutador(r, 630, 420, 1.25, (60, 22, 24, 255), alpha(TINTA, 220))
        self._t(r, 480, 70, "業", 96, OURO, "center")
        self._t(r, 480, 150, "Karmabound", 52, TINTA, "center")
        self._t(r, 480, 200, "todo azar fica preso ao seu Carma", 18, alpha(TINTA, 150), "center")
        y0 = 452
        for i, (_, d) in enumerate(self.modos):
            y = y0 + i * 36
            atual = i == self.cursor
            cor = TINTA if atual else alpha(TINTA, 110)
            if atual:
                r.draw_ui_rect(330, y - 6, 300, 32, alpha(LACA, 255))
                r.draw_ui_polygon([(344, y + 3), (354, y + 10), (344, y + 17)], OURO)
            self._t(r, 366, y - 2, d["nome"], 20, cor)
            self._t(
                r, 618, y + 2, f"~{d['alvo_vitoria']:.0%} vencem", 14, alpha(TINTA, 90), "topright"
            )
        self._t(
            r,
            480,
            ALTURA - 28,
            "↑ ↓ escolhe · Enter começa · G grimório · esc sai",
            14,
            alpha(TINTA, 100),
            "center",
        )


# ----------------------------------------------------------------------- troca de técnica


class SubstituirScene(_Base):
    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.cores = {r.id: hex_cor(r.cor) for r in jornada.ctx.raridades}

    def update(self, world, delta_time: float) -> None:
        if self._sair():
            return
        e = self.entrada
        tecnicas = self.j.jogador.tecnicas
        for i, t in enumerate(tecnicas):
            if e.is_action_pressed(f"tecnica_{i + 1}"):
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
    """Versão simples: você escolhe as restrições e a duração; o Altar compra os ganhos."""

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
        self.estado = "pesar"  # pesar | escolher | propor | proposta
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
                self.estado = "proposta"
            return
        e = self.entrada
        if self.estado == "proposta":
            if e.is_action_pressed("confirmar") and self.proposta and self.proposta.voto.ganhos:
                self.j.jurar(self.proposta)
                self.ao_concluir()
            elif e.is_action_pressed("cancelar") or e.is_action_pressed("confirmar"):
                self.estado = "escolher"
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
        if self.estado == "proposta":
            self._proposta(r)
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

    def _proposta(self, r: IRenderer) -> None:
        p = self.proposta
        if p is None:
            return
        v = p.voto
        self._t(r, 40, 82, "Você abre mão de:", 17, alpha(TINTA, 150))
        for k, res in enumerate(v.restricoes):
            self._t(r, 60, 112 + k * 30, f"{res.kanji}  {res.nome} — {res.texto}", 18, SANGUE_VIVO)
        y = 112 + len(v.restricoes) * 30 + 16
        self._t(
            r,
            40,
            y,
            f"{DURANTE[v.duracao]}. Para você, isso custa ~{_lutas(p.sacrificio)}; "
            f"cada restrição conta no máximo {_lutas(self.j.ctx.catalogo.teto_por_restricao)}.",
            16,
            alpha(TINTA, 150),
        )
        self._t(
            r,
            40,
            y + 36,
            f"Em troca ({v.pontos:.1f} pontos):".replace(".", ","),
            17,
            alpha(TINTA, 150),
        )
        niveis = Counter(g.id for g in v.ganhos)
        vistos = []
        for g in v.ganhos:
            if g.id in vistos:
                continue
            vistos.append(g.id)
            n = niveis[g.id]
            self._t(
                r,
                60,
                y + 66 + (len(vistos) - 1) * 30,
                f"{g.kanji}  {g.nome}{f' ×{n}' if n > 1 else ''} — {g.texto}",
                18,
                OURO,
            )
        y2 = y + 66 + max(1, len(vistos)) * 30 + 20
        if not v.ganhos:
            self._t(
                r, 60, y + 66, "nada: o sacrifício não paga nenhum ganho", 18, alpha(TINTA, 120)
            )
        cor = VERDE_JADE if p.saldo > 0 else SANGUE_VIVO
        self._t(
            r,
            40,
            y2,
            f"Estimativa do Altar: {_lutas(p.saldo)} vencida(s) "
            f"{'a mais' if p.saldo > 0 else 'a menos'} no resto da run",
            19,
            cor,
        )
        for k, linha in enumerate(
            quebrar(
                "Quebrar um voto depois custa os ganhos, metade da vida e todo o Carma, "
                "e exige jurar um voto de quebra.",
                90,
            )
        ):
            self._t(r, 40, y2 + 34 + k * 20, linha, 14, alpha(TINTA, 110))
        dica = "Enter jura · Backspace volta" if v.ganhos else "Enter ou Backspace volta"
        self._t(r, 480, ALTURA - 26, dica, 15, alpha(TINTA, 130), "center")


# ----------------------------------------------------------------------- fim


class FimScene(_Base):
    def __init__(self, jornada: Jornada, entrada, ao_reiniciar, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_reiniciar = ao_reiniciar

    def update(self, world, delta_time: float) -> None:
        if self._sair():
            return
        if self.entrada.is_action_pressed("confirmar"):
            self.ao_reiniciar()

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        j = self.j
        venceu = j.fase == "vitoria"
        if venceu:
            desenhar_lutador(r, 480, 300, 1.5, TINTA, alpha(OURO, 220), guarda=0.3)
            self._t(r, 480, 330, "勝  O torneio é seu", 44, OURO, "center")
        else:
            desenhar_lutador(r, 480, 300, 1.5, (60, 22, 24, 255), alpha(TINTA, 200))
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
        ]
        for k, linha in enumerate(x for x in linhas if x):
            self._t(r, 480, 400 + k * 28, linha, 17, alpha(TINTA, 170), "center")
        self._t(
            r, 480, ALTURA - 30, "Enter volta ao título · esc sai", 15, alpha(TINTA, 110), "center"
        )

"""Telas do caminho entre as lutas: as três portas e a encruzilhada.

Leem e mexem só na `Jornada` (`escolher_caminho`, `escolher_encruzilhada`); nenhuma
decide regra. O visual segue o do Treino: cartas com o kanji grande, o nome e o texto.
"""

from __future__ import annotations

import math

from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes
from karmabound.arenas import _particulas
from karmabound.caminho import Porta
from karmabound.jornada import Jornada
from karmabound.tela_menus import _Base, partes_do_build
from karmabound.transicoes import Camada, Cartas
from karmabound.visual import (
    ALTURA,
    FERRO,
    LACA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    VERDE_JADE,
    alpha,
    mistura,
    quebrar,
)

COR_PORTA = {
    "rival": TINTA,
    "bando": mistura(TINTA, SANGUE_VIVO, 0.35),
    "elite": OURO,
    "evento": mistura(TINTA, FERRO, 0.35),
    "nemesis": SANGUE_VIVO,
}


def cor_da_vida(frac: float):
    """Verde inteiro, tinta no meio, sangue quando falta."""
    if frac < 0.4:
        return SANGUE_VIVO
    return VERDE_JADE if frac > 0.75 else TINTA


class _Escolha(_Base):
    """O que as duas telas do caminho dividem: a Jornada e o estado do jogador."""

    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.cursor = 0
        self.cartas = Cartas()
        self.cartas.LEVANTA = 6  # pouco: a barra de vida mora logo acima das portas
        self.fixo = None  # o que estava na tela no momento da escolha (a Jornada já andou)

    @property
    def segurar_saida(self) -> float:
        return 0.14 if self.cartas.escolhida is not None else 0.0

    def _n(self) -> int:
        return 0

    def _animar(self, dt: float) -> None:
        self.cartas.avancar(dt, self.cursor, self._n())

    def _apertou_numero(self, n: int) -> int | None:
        e = self.entrada
        for i in range(n):
            if e.is_action_pressed(f"escolher_{i + 1}") or e.is_action_pressed(f"tecnica_{i + 1}"):
                return i
        return None

    def _onde(self) -> str:
        """'Capítulo 2 · luta 3 de 4' (na Torre, o andar)."""
        est = self.j.estado
        if self.j.ctx.jogo == "torre":
            return f"Andar {est.proxima_luta}"
        return f"Capítulo {est.capitulo} · luta {est.luta_no_capitulo} de {est.tamanho_capitulo}"

    def _vida(self, r: IRenderer, cx: float, y: float) -> None:
        """Vida (com uma barrinha) e Carma: o que pesa na hora de escolher."""
        jg = self.j.jogador
        frac = jg.vida / jg.vida_max if jg.vida_max else 0.0
        cor = cor_da_vida(frac)
        largura = 220
        x = cx - largura / 2
        r.draw_ui_rect(x, y + 26, largura, 6, alpha(FERRO, 120))
        r.draw_ui_rect(x, y + 26, largura * max(0.0, min(1.0, frac)), 6, alpha(cor, 220))
        carma = self.j.carma
        texto = f"Vida {jg.vida}/{jg.vida_max}"
        if carma is not None:
            texto += f" · Carma {carma.valor:.0f}/{carma.config.maximo:.0f}"
        self._t(r, cx, y, texto, 17, alpha(cor, 230), "center")


# ----------------------------------------------------------------------- as portas


class CaminhoScene(_Escolha):
    """Antes da luta: 1 de 3 portas (rival, bando, elite, encruzilhada ou a Nêmesis)."""

    def _n(self) -> int:
        return len(self.fixo or self.j.oferta_caminho)

    def _escolher(self, i: int) -> None:
        som.tocar("confirmar")
        self.fixo = (tuple(self.j.oferta_caminho), self._onde(), tuple(self.j.proximas_portas))
        self.cursor = i
        self.cartas.escolher(i)
        self.j.escolher_caminho(i)
        self.ao_concluir()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        n = len(self.j.oferta_caminho)
        if not n:
            return
        i = self._apertou_numero(n)
        if i is not None:
            self._escolher(i)
            return
        e = self.entrada
        if e.is_action_pressed("esquerda"):
            self.cursor = (self.cursor - 1) % n
            som.tocar("mover")
        elif e.is_action_pressed("direita"):
            self.cursor = (self.cursor + 1) % n
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            self._escolher(self.cursor)

    # --------------------------------------------------------------- desenho

    def _nome_nemesis(self) -> str:
        nem = self.j.ctx.nemesis or {}
        return nem.get("nome", "") or "Nêmesis"

    def _rodape_da_carta(self, r: IRenderer, p: Porta, cx: float, y: float, cor) -> None:
        """O que espera atrás da porta: os papéis do bando, o encontro ou quem voltou."""
        papeis = self.j.ctx.caminho.papeis if self.j.ctx.caminho else {}
        if p.papeis:
            passo = 84 if len(p.papeis) == 3 else 96  # 'Comandante' ao lado de 'Curandeiro'
            x0 = cx - passo * (len(p.papeis) - 1) / 2
            for k, pid in enumerate(p.papeis):
                papel = papeis.get(pid)
                if papel is None:
                    continue
                x = x0 + k * passo
                self._t(r, x, y + 14, papel.kanji, 28, cor, "center")
                self._t(r, x, y + 40, papel.nome, 13, alpha(TINTA, 170), "center")
        elif p.tipo == "evento" and p.evento is not None:
            self._t(r, cx, y + 14, p.evento.kanji, 28, cor, "center")
            self._t(r, cx, y + 40, p.evento.nome, 14, alpha(TINTA, 190), "center")
        elif p.tipo == "nemesis":
            for k, linha in enumerate(quebrar(self._nome_nemesis(), 24)[:2]):
                self._t(r, cx, y + 16 + k * 20, linha, 16, alpha(SANGUE_VIVO, 230), "center")

    def _afixos(self) -> str:
        """'Um afixo sorteado ao entrar, entre 吸 棘 速…' (dois a partir de um capítulo)."""
        cam = self.j.ctx.caminho
        if cam is None or not cam.afixos:
            return "Mais forte que um rival; vencer garante uma Relíquia."
        n = cam.elite.get("afixos", 1)
        if self.j.capitulo >= cam.elite.get("afixos_dois_a_partir_do_capitulo", 99):
            n += 1
        quantos = "Um afixo sorteado" if n <= 1 else f"{n} afixos sorteados"
        return f"{quantos} ao entrar, entre {' '.join(a.kanji for a in cam.afixos.values())}"

    def _mapa(self, r: IRenderer, proximas, y: float) -> None:
        """O passo seguinte do capítulo: as portas que vêm depois (ou o chefe)."""
        if self.j.ctx.jogo == "torre" and not proximas:
            return  # a Torre não tem capítulo: o passo seguinte só se vê ao chegar
        itens = [(p.kanji, p.nome, COR_PORTA.get(p.tipo, TINTA)) for p in proximas]
        if not itens:
            itens = [("鬼", "o chefe", SANGUE_VIVO)]
        passo = 116
        x0 = 480 - passo * (len(itens) - 1) / 2 + 30
        self._t(r, x0 - 44, y + 4, "depois ›", 14, alpha(TINTA, 120), "topright")
        for k, (kanji, nome, cor) in enumerate(itens):
            x = x0 + k * passo
            self._t(r, x - 30, y - 2, kanji, 24, alpha(cor, 200))
            self._t(r, x - 2, y + 4, nome, 14, alpha(TINTA, 150))

    def _detalhe(self, r: IRenderer, p: Porta) -> None:
        """Embaixo das cartas, o detalhe da porta escolhida."""
        linhas: list[tuple[str, tuple]] = []
        papeis = self.j.ctx.caminho.papeis if self.j.ctx.caminho else {}
        if p.papeis:
            for pid in dict.fromkeys(p.papeis):  # sem repetir (duas Lâminas: uma linha)
                papel = papeis.get(pid)
                if papel is not None:
                    linhas.append((f"{papel.kanji} {papel.nome}: {papel.texto}", TINTA))
        elif p.tipo == "evento" and p.evento is not None:
            for linha in quebrar(p.evento.texto, 80)[:2]:
                linhas.append((linha, TINTA))
        elif p.tipo == "nemesis":
            vezes = (self.j.ctx.nemesis or {}).get("vezes", 1)
            quantas = "uma vez" if vezes <= 1 else f"{vezes} vezes"
            linhas.append(
                (f"Já te matou {quantas}. Volta mais forte, com o golpe que te matou.", SANGUE_VIVO)
            )
        if p.tipo == "elite":  # os afixos só se revelam ao entrar
            linhas.insert(0, (self._afixos(), OURO))
        for k, (linha, cor) in enumerate(linhas[:3]):
            self._t(r, 480, 462 + k * 24, linha, 15, alpha(cor, 200), "center")

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        _particulas(r, t, 16, alpha(TINTA, 40), sobe=False, tam=1.6, vel=12, deriva=20, semente=7)
        oferta, onde, proximas = self.fixo or (
            self.j.oferta_caminho,
            self._onde(),
            self.j.proximas_portas,
        )
        self._t(r, 480, 40, "岐  O caminho", 34, OURO, "center")
        build = partes_do_build(self.j)  # as Ressonâncias, o aliado e a Ascensão, no canto
        linhas = [" · ".join(build)] if len(" · ".join(build)) <= 40 else build
        for k, linha in enumerate(linhas[:3]):
            self._t(r, 24, 18 + k * 18, linha, 13, alpha(OURO, 150))
        self._t(r, 480, 84, onde, 16, alpha(TINTA, 150), "center")
        self._vida(r, 480, 104)
        largura, altura, folga = 260, 290, 30
        x0 = 480 - (len(oferta) * largura + (len(oferta) - 1) * folga) / 2
        pulso = self.cartas.pulso()
        tela = r
        for i, p in enumerate(oferta):
            x, y = x0 + i * (largura + folga), 156
            foco = self.cartas.foco_de(i)
            r = self.cartas.camada(tela, i, (x + largura / 2, y + altura / 2))
            tipo = COR_PORTA.get(p.tipo, TINTA)
            r.draw_ui_rect(x, y, largura, altura, alpha(LACA, 110 + 145 * foco))
            if foco > 0.02:  # a borda da escolhida pulsa na cor da porta
                borda = alpha(tipo, (150 + 105 * pulso) * foco)
                r.draw_ui_rect(x, y, largura, 3, borda)
                r.draw_ui_rect(x, y + altura - 3, largura, 3, borda)
            if p.tipo == "nemesis" and foco < 0.98:  # a Nêmesis chama mesmo de longe
                r.draw_ui_rect(x, y, largura, 2, alpha(SANGUE_VIVO, 140 * (1 - foco)))
            cor = alpha(tipo, 150 + 105 * foco)
            cx = x + largura / 2
            self._t(r, cx, y + 56, p.kanji, 64, cor, "center")
            self._t(r, cx, y + 118, p.nome, 20, cor, "center")
            for k, linha in enumerate(quebrar(p.texto, 27)[:3]):
                self._t(
                    r,
                    cx,
                    y + 150 + k * 21,
                    linha,
                    15,
                    alpha(TINTA, 130 + 60 * foco),
                    "center",
                )
            if p.papeis or p.tipo in ("evento", "nemesis"):  # há algo atrás da porta
                r.draw_ui_line(cx - 70, y + 220, cx + 70, y + 220, alpha(tipo, 70), 1)
            self._rodape_da_carta(r, p, cx, y + 228, cor)
            self._t(r, x + 14, y + 10, str(i + 1), 18, alpha(TINTA, 120))
            if i == self.cartas.escolhida:
                self.cartas.selo(tela, x + largura - 26, y + 30, "決")
        r = tela
        if oferta:
            troca = self.cartas.u_carimbo()  # o detalhe some junto com as outras portas
            c = Camada(r, (480, 480), 1.0, 0, 0, 1 - troca)
            self._detalhe(c, oferta[self.cursor % len(oferta)])
        self._mapa(r, proximas, 548)
        self._t(
            r,
            480,
            ALTURA - 32,
            f"1–{len(oferta)} (ou ← → e Enter) escolhe a porta · Esc pausa",
            15,
            alpha(TINTA, 110),
            "center",
        )
        transicoes.revelar(self, r, t)


# ----------------------------------------------------------------------- a encruzilhada


class EncruzilhadaScene(_Escolha):
    """A porta sem luta: o encontro e as opções, numa lista. A que custa mais Carma do
    que você tem aparece apagada e não confirma."""

    def __init__(self, jornada: Jornada, entrada, ao_concluir, ao_sair) -> None:
        super().__init__(jornada, entrada, ao_concluir, ao_sair)
        self.aviso = ""
        self.cartas = Cartas(sobe=30, lado=True)
        self.cartas.t = -0.2  # as opções entram depois do encontro
        self.negou = -9.0  # quando uma opção sem Carma foi tentada (ela treme)

    def _n(self) -> int:
        ev = self.fixo[0] if self.fixo else self.j.encruzilhada
        return len(ev.opcoes) if ev is not None else 0

    def _escolher(self, i: int) -> None:
        if not self.j.pode_escolher(i):
            self.cursor = i
            self.aviso = "Carma insuficiente"
            self.negou = self.cartas.t
            return
        som.tocar("confirmar")
        ev = self.j.encruzilhada
        self.fixo = (ev, [self.j.pode_escolher(k) for k in range(len(ev.opcoes))], self._onde())
        self.cursor = i
        self.cartas.escolher(i)
        self.j.escolher_encruzilhada(i)
        self.ao_concluir()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        ev = self.j.encruzilhada
        if ev is None:
            return
        n = len(ev.opcoes)
        i = self._apertou_numero(n)
        if i is not None:
            self._escolher(i)
            return
        e = self.entrada
        if e.is_action_pressed("cima"):
            self.cursor, self.aviso = (self.cursor - 1) % n, ""
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor, self.aviso = (self.cursor + 1) % n, ""
            som.tocar("mover")
        elif e.is_action_pressed("confirmar"):
            self._escolher(self.cursor)

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        t = self.relogio
        _particulas(r, t, 14, alpha(OURO, 40), sobe=True, tam=1.4, vel=10, semente=11)
        if self.fixo:
            ev, cabem, onde = self.fixo
        else:
            ev, onde = self.j.encruzilhada, self._onde()
            cabem = [self.j.pode_escolher(k) for k in range(len(ev.opcoes))] if ev else []
        if ev is None:
            return
        self._t(
            r,
            480,
            34,
            f"岐  Encruzilhada · {onde.lower()}",
            15,
            alpha(TINTA, 130),
            "center",
        )
        self._t(r, 480, 112, ev.kanji, 84, mistura(OURO, TINTA, 0.4), "center")
        self._t(r, 480, 182, ev.nome, 30, TINTA, "center")
        y = 224
        for linha in quebrar(ev.texto, 70)[:2]:
            self._t(r, 480, y, linha, 17, alpha(TINTA, 170), "center")
            y += 24
        y = max(y + 22, 290)
        tela = r
        for i, op in enumerate(ev.opcoes):
            cabe = cabem[i]
            foco = self.cartas.foco_de(i)
            linhas = quebrar(op.texto, 64)[:2]
            altura = 30 + 22 * (len(linhas) - 1)
            r = self.cartas.camada(tela, i, (480, y + altura / 2))
            treme = max(0.0, 1 - (self.cartas.t - self.negou) / 0.3)
            if treme and i == self.cursor:  # sem Carma: a opção treme e não confirma
                r = Camada(r, (0, 0), 1.0, 7 * treme * math.sin(self.cartas.t * 70), 0, 1.0)
            if foco > 0.02:
                r.draw_ui_rect(130, y - 6, 700, altura + 8, alpha(LACA, 255 * foco))
                r.draw_ui_polygon(
                    [(138, y + 4), (146, y + 10), (138, y + 16)],
                    alpha(OURO if cabe else FERRO, 255 * foco),
                )
            cor = mistura(TINTA, OURO, foco) if cabe else alpha(TINTA, 70)
            self._t(r, 160, y, str(i + 1), 18, alpha(TINTA, 120 if cabe else 60))
            for k, linha in enumerate(linhas):
                self._t(r, 190, y + k * 22, linha, 18, cor)
            if not cabe:
                self._t(
                    r, 818, y + 3, "Carma insuficiente", 13, alpha(SANGUE_VIVO, 150), "topright"
                )
            if i == self.cartas.escolhida:
                self.cartas.selo(tela, 800, y + altura / 2 - 2, "決", 24)
            y += altura + 16
        r = tela
        if self.aviso:
            self._t(r, 480, y + 4, self.aviso, 16, SANGUE_VIVO, "center")
        self._vida(r, 480, 530)
        self._t(
            r,
            480,
            ALTURA - 32,
            f"1–{len(ev.opcoes)} (ou ↑ ↓ e Enter) escolhe · Esc pausa",
            15,
            alpha(TINTA, 110),
            "center",
        )
        transicoes.revelar(self, r, t)

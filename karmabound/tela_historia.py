"""As telas do modo História: a cena (linha a linha) e a escolha (o convite, os finais).

`CenaScene` mostra as linhas da fase "cena" da Jornada sobre o cenário do Arco: cada
linha se escreve aos poucos; Enter completa a linha, e com ela inteira passa para a
próxima. Quem fala aparece à esquerda: a figura e o nome do vilão, "Você", ou nada
(narração). Na última linha, Enter segue (`jornada.avancar_cena`).

`EscolhaScene` é uma escolha entre cartas (↑ ↓ ou ← →, Enter): ir além da Roda ou
terminar; Quebrar ou Tomar a Roda.
"""

from __future__ import annotations

import math

from ouroboros.interfaces.input_provider import IInputProvider
from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, transicoes
from karmabound.arenas import desenhar_arena
from karmabound.figuras import desenhar_lutador
from karmabound.historias import Linha
from karmabound.jornada import Jornada
from karmabound.opcoes import OPCOES
from karmabound.run import arco_fixo
from karmabound.tela_luta import cor_do_rival
from karmabound.tela_menus import _Base
from karmabound.visual import (
    ALTURA,
    FUNDO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    alpha,
    ease_out,
    moldura,
    quebrar,
)

LETRAS_POR_SEGUNDO = 55.0  # a linha se escreve nesta velocidade (×  a das animações)
LARGURA_LINHA = 46  # caracteres por linha da cena com quem fala (a caixa começa em x=300)


class CenaScene(_Base):
    def __init__(self, jornada: Jornada, entrada: IInputProvider, ao_concluir, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.j = jornada
        self.ao_concluir = ao_concluir
        self.linhas: tuple[Linha, ...] = tuple(jornada.cena)
        self.i = 0  # a linha da vez
        self.letras = 0.0  # quantas letras dela já apareceram
        arco = jornada.arco or arco_fixo(jornada.estado, jornada.ctx)
        self.arco = arco.id if arco is not None else None

    # ------------------------------------------------------------------ lógica

    @property
    def linha(self) -> Linha:
        return self.linhas[self.i]

    @property
    def inteira(self) -> bool:
        return self.letras >= len(self.linha.texto)

    def _animar(self, dt: float) -> None:
        if self.linhas and not self.inteira:
            self.letras += dt * LETRAS_POR_SEGUNDO * OPCOES.velocidade

    def assentar(self) -> None:
        self.letras = len(self.linha.texto) if self.linhas else 0

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        if not self.linhas:
            self._seguir()
            return
        if self.entrada.is_action_pressed("confirmar"):
            if not self.inteira:
                self.letras = len(self.linha.texto)
            elif self.i + 1 < len(self.linhas):
                self.i += 1
                self.letras = 0.0
                som.tocar("mover")
            else:
                som.tocar("confirmar")
                self._seguir()

    def _seguir(self) -> None:
        self.j.avancar_cena()
        self.ao_concluir()

    # ------------------------------------------------------------------ desenho

    def _quem(self, linha: Linha) -> tuple[str, str, object]:
        """(nome, kanji, vilão) de quem fala ("" na narração)."""
        if linha.quem == "voce":
            return "Você", "", None
        elenco = self.j.ctx.elenco
        v = elenco.get(linha.quem) if elenco is not None and linha.quem else None
        if v is None:
            return "", "", None
        return v.nome, v.kanji, v

    def render(self, world, r: IRenderer) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        desenhar_arena(r, self.arco, self.relogio)
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(FUNDO, 120))  # o cenário fica atrás
        h = self.j.ctx.historia
        cap = self.j.capitulo_da_cena(self.j.capitulo)
        topo = cap.nome if cap is not None else (h.nome if h is not None else "")
        if topo:
            self._t(r, 480, 34, topo, 22, alpha(OURO, 220), "center")
        if not self.linhas:
            return
        nome, kanji, vilao = self._quem(self.linha)
        if vilao is not None:  # quem fala, de pé à esquerda
            respira = math.sin(self.relogio * 1.6) * 2
            cor = cor_do_rival(vilao, vilao.estilo)
            desenhar_lutador(
                r,
                190,
                420 + respira,
                1.25,
                alpha(cor, 255),
                alpha(TINTA, 220),
                estilo=vilao.estilo or "espadachim",
                tempo=self.relogio,
            )
        elif self.linha.quem == "voce":
            desenhar_lutador(
                r,
                190,
                420,
                1.15,
                alpha(TINTA, 230),
                alpha((255, 255, 255, 255), 160),
                tempo=self.relogio,
                costas=True,
            )
        # a caixa do texto
        x0, y0, x1, y1 = 300 if nome else 120, 380, 860, 560
        r.draw_ui_rect(x0, y0, x1 - x0, y1 - y0, alpha(LACA, 235))
        moldura(
            r,
            x0,
            y0,
            x1,
            y1,
            SANGUE_VIVO if vilao is not None and vilao.papel != "tenente" else OURO,
        )
        y = y0 + 22
        if nome:
            self._t(r, x0 + 24, y, f"{kanji}  {nome}".strip(), 22, OURO)
            y += 38
        texto = self.linha.texto[: int(self.letras)]
        largura = LARGURA_LINHA if nome else LARGURA_LINHA + 18  # a narração ocupa a caixa larga
        cor = TINTA if nome else alpha(TINTA, 215)
        for linha in quebrar(texto, largura)[:4]:
            self._t(r, x0 + 24, y, linha, 19, cor)
            y += 26
        # o rodapé: em que linha está, e o que Enter faz
        self._t(
            r,
            x1 - 16,
            y1 - 26,
            f"{self.i + 1}/{len(self.linhas)}",
            13,
            alpha(TINTA, 110),
            "topright",
        )
        if self.inteira:
            pisca = 0.5 + 0.5 * math.sin(self.relogio * 4)
            ultimo = self.i + 1 >= len(self.linhas)
            dica = "Enter segue" if ultimo else "Enter"
            self._t(r, 480, ALTURA - 30, dica, 15, alpha(TINTA, 90 + 60 * pisca), "center")
        transicoes.revelar(self, r, self.relogio)


class EscolhaScene(_Base):
    """Uma escolha entre cartas grandes. `opcoes`: (kanji, nome, texto) de cada uma;
    `ao_escolher(indice)` é chamado com Enter."""

    def __init__(
        self,
        titulo: str,
        subtitulo: str,
        opcoes: list[tuple[str, str, str]],
        entrada: IInputProvider,
        ao_escolher,
        ao_sair,
        arco: str | None = None,
    ) -> None:
        super().__init__(entrada, ao_sair)
        self.titulo, self.subtitulo, self.opcoes = titulo, subtitulo, opcoes
        self.ao_escolher = ao_escolher
        self.cursor = 0
        self.arco = arco
        self.surge = 0.0

    def _animar(self, dt: float) -> None:
        self.surge = min(1.0, self.surge + dt * OPCOES.velocidade * 2.2)

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        self._animar(delta_time)
        if self._sair():
            return
        e = self.entrada
        n = len(self.opcoes)
        for menos in ("cima", "esquerda"):
            if e.is_action_pressed(menos):
                self.cursor = (self.cursor - 1) % n
                som.tocar("mover")
        for mais in ("baixo", "direita"):
            if e.is_action_pressed(mais):
                self.cursor = (self.cursor + 1) % n
                som.tocar("mover")
        if e.is_action_pressed("confirmar"):
            som.tocar("confirmar")
            self.ao_escolher(self.cursor)

    def render(self, world, r: IRenderer) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        if self.arco:
            desenhar_arena(r, self.arco, self.relogio)
            r.draw_ui_rect(0, 0, LARGURA, ALTURA, alpha(FUNDO, 150))
        self._t(r, 480, 60, self.titulo, 34, OURO, "center")
        self._t(r, 480, 108, self.subtitulo, 17, alpha(TINTA, 170), "center")
        n = len(self.opcoes)
        largura, folga = 300, 40
        x = 480 - (n * largura + (n - 1) * folga) / 2
        sobe = 30 * (1 - ease_out(self.surge))
        for k, (kanji, nome, texto) in enumerate(self.opcoes):
            foco = k == self.cursor
            x0, y0 = x + k * (largura + folga), 170 + sobe
            x1, y1 = x0 + largura, y0 + 340
            r.draw_ui_rect(x0, y0, largura, y1 - y0, alpha(LACA, 240 if foco else 190))
            moldura(r, x0, y0, x1, y1, SANGUE_VIVO if foco else alpha(TINTA, 90))
            cor = OURO if foco else alpha(TINTA, 150)
            self._t(r, x0 + largura / 2, y0 + 30, kanji, 72, cor, "center")
            self._t(
                r,
                x0 + largura / 2,
                y0 + 130,
                nome,
                24,
                TINTA if foco else alpha(TINTA, 170),
                "center",
            )
            yy = y0 + 176
            for linha in quebrar(texto, 30)[:6]:
                self._t(
                    r, x0 + largura / 2, yy, linha, 15, alpha(TINTA, 200 if foco else 130), "center"
                )
                yy += 22
        self._t(r, 480, ALTURA - 32, "← →  escolher · Enter", 15, alpha(TINTA, 110), "center")
        transicoes.revelar(self, r, self.relogio)

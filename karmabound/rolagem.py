"""Rolagem de lista pelo teclado: a janela segue o cursor e uma barra mostra onde você está.

O jogo não tem mouse; a lista rola quando o cursor passa da borda da janela.
"""

from __future__ import annotations

from dataclasses import dataclass

from ouroboros.interfaces.renderer import IRenderer

from karmabound.visual import FERRO, OURO, alpha


@dataclass
class Rolagem:
    visiveis: int  # quantas linhas cabem na tela
    topo: int = 0  # a primeira linha visível

    def seguir(self, cursor: int | None, total: int) -> None:
        """Mantém o cursor dentro da janela (None: o cursor está fora da lista)."""
        if cursor is not None and 0 <= cursor < total:
            if cursor < self.topo:
                self.topo = cursor
            elif cursor >= self.topo + self.visiveis:
                self.topo = cursor - self.visiveis + 1
        self.topo = max(0, min(self.topo, total - self.visiveis))

    def faixa(self, total: int) -> range:
        return range(self.topo, min(total, self.topo + self.visiveis))

    def y(self, i: int, y0: float, linha: float) -> float:
        return y0 + (i - self.topo) * linha

    def desenhar(self, r: IRenderer, x: float, y0: float, linha: float, total: int) -> None:
        """A barra de rolagem: só aparece quando a lista não cabe."""
        if total <= self.visiveis:
            return
        altura = self.visiveis * linha - 8
        r.draw_ui_rect(x, y0 - 4, 4, altura, alpha(FERRO, 110))
        alca = max(24.0, altura * self.visiveis / total)
        pos = (altura - alca) * self.topo / (total - self.visiveis)
        r.draw_ui_rect(x, y0 - 4 + pos, 4, alca, alpha(OURO, 200))

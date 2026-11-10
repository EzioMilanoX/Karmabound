"""A tela dos votos no menu (pacto.py): jure restrições, compre ganhos, veja o que libera.

Uma lista só: as restrições em cima (Enter marca e desmarca), os ganhos embaixo (Enter
compra um nível, Backspace devolve um). ↑ ↓ andam, Esc volta ao título guardando o pacto.
Cada restrição mostra a recompensa que libera ao vencer com ela (完: já liberada).
"""

from __future__ import annotations

from karmabound import pacto, som, transicoes
from karmabound.tela_menus import _Base
from karmabound.visual import ALTURA, FUNDO, LARGURA, OURO, SANGUE_VIVO, TINTA, alpha
from karmabound.votos import Catalogo

VISIVEIS = 15
LINHA = 30
TOPO = 132


class PactoScene(_Base):
    def __init__(
        self,
        catalogo: Catalogo,
        escolha: dict,
        nomes: dict[str, str],
        liberadas: set[str],
        entrada,
        ao_voltar,
    ) -> None:
        """`escolha`: {"restricoes": [...], "ganhos": [...]} (é editada aqui);
        `nomes`: item -> nome (as recompensas); `liberadas`: as já liberadas."""
        super().__init__(entrada, lambda: ao_voltar(self.escolha))
        self.cat = catalogo
        self.escolha = {
            "restricoes": list(escolha.get("restricoes", [])),
            "ganhos": list(escolha.get("ganhos", [])),
        }
        self.nomes, self.liberadas = nomes, liberadas
        self.linhas = [("r", r) for r in catalogo.restricoes] + [("g", g) for g in catalogo.ganhos]
        self.cursor = 0

    @property
    def pontos(self) -> float:
        return pacto.pontos(self.cat, self.escolha["restricoes"])

    @property
    def gastos(self) -> float:
        return pacto.custo(self.cat, self.escolha["ganhos"])

    def _ajustar(self) -> None:
        """Sem pontos para tudo (tirou uma restrição): os ganhos mais caros saem."""
        while self.escolha["ganhos"] and self.gastos > self.pontos + 1e-9:
            self.escolha["ganhos"].pop()

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        if self._sair():
            return
        e = self.entrada
        if e.is_action_pressed("cima"):
            self.cursor = (self.cursor - 1) % len(self.linhas)
            som.tocar("mover")
        elif e.is_action_pressed("baixo"):
            self.cursor = (self.cursor + 1) % len(self.linhas)
            som.tocar("mover")
        tipo, cid = self.linhas[self.cursor]
        restricoes, ganhos = self.escolha["restricoes"], self.escolha["ganhos"]
        if e.is_action_pressed("confirmar"):
            if tipo == "r" and cid in restricoes:
                restricoes.remove(cid)
                self._ajustar()
            elif tipo == "r" and len(restricoes) < pacto.MAX_RESTRICOES:
                restricoes.append(cid)
            elif tipo == "g" and pacto.cabe(self.cat, restricoes, ganhos, cid):
                ganhos.append(cid)
            else:
                som.tocar("vidro")  # não cabe
                return
            som.tocar("confirmar")
        elif e.is_action_pressed("cancelar") and tipo == "g" and cid in ganhos:
            ganhos.reverse()
            ganhos.remove(cid)  # tira o último nível comprado dele
            ganhos.reverse()
            som.tocar("mover")

    def render(self, world, r) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        self._t(r, 480, 30, "誓  Votos", 32, OURO, "center")
        sobra = self.pontos - self.gastos
        resumo = f"Pontos {self.pontos:.1f} · gastos {self.gastos:.1f} · sobram {sobra:.1f}"
        self._t(r, 480, 76, resumo.replace(".", ","), 16, alpha(TINTA, 190), "center")
        self._t(
            r,
            480,
            100,
            "Restrições dão pontos e liberam um item ao vencer. Pontos compram ganhos.",
            13,
            alpha(TINTA, 120),
            "center",
        )
        inicio = min(max(0, self.cursor - VISIVEIS // 2), max(0, len(self.linhas) - VISIVEIS))
        for k, (tipo, cid) in enumerate(self.linhas[inicio : inicio + VISIVEIS]):
            i = inicio + k
            y = TOPO + k * LINHA
            foco = i == self.cursor
            if foco:
                r.draw_ui_rect(40, y - 4, LARGURA - 80, LINHA - 2, alpha(TINTA, 18))
            if tipo == "r":
                c = self.cat.restricoes[cid]
                marcado = cid in self.escolha["restricoes"]
                caixa = "■" if marcado else "□"
                cor = SANGUE_VIVO if marcado else alpha(TINTA, 200 if foco else 150)
                premio = self.cat.recompensas.get(cid, "")
                nome_premio = self.nomes.get(premio, premio)
                feito = "完 " if premio in self.liberadas else "→ "
                lado = f"{feito}{nome_premio}" if premio else ""
            else:
                c = self.cat.ganhos[cid]
                n = self.escolha["ganhos"].count(cid)
                caixa = f"{n}/{c.niveis}" if c.niveis > 1 else ("■" if n else "□")
                cor = OURO if n else alpha(TINTA, 200 if foco else 150)
                prox = pacto.preco(self.cat, c, n + 1) if n < c.niveis else 0.0
                lado = f"custa {prox:.1f}".replace(".", ",") if n < c.niveis else "no máximo"
            self._t(r, 56, y, caixa, 15, cor)
            self._t(r, 100, y, f"{c.kanji} {c.nome}", 16, cor)
            self._t(r, 330, y + 1, c.texto[:52], 13, alpha(TINTA, 150))
            self._t(r, LARGURA - 56, y + 1, lado, 13, alpha(OURO, 200), "topright")
        rodape = "↑ ↓ escolhe · Enter jura/compra · Backspace devolve · Esc volta"
        self._t(r, 480, ALTURA - 30, rodape, 14, alpha(TINTA, 110), "center")
        transicoes.revelar(self, r, self.relogio)

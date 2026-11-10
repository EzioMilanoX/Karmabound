"""A tela do Laboratório (livre.py): monte a build e o rival, e lute.

↑ ↓ andam, ← → trocam a opção da linha, Enter abre a lista inteira dela (na lista:
← → pulam uma página, Enter escolhe, Esc fecha). "Lutar" começa; Esc volta ao título.
"""

from __future__ import annotations

from karmabound import livre, som, transicoes
from karmabound.tela_menus import _Base
from karmabound.visual import ALTURA, FUNDO, LARGURA, OURO, SANGUE_VIVO, TINTA, alpha

VISIVEIS = 15
LINHA = 28
TOPO = 112


def _nome(op) -> str:
    if op is None:
        return "—"
    if isinstance(op, int):
        return str(op)
    return f"{op.kanji} {op.nome}".strip()


def _detalhe(op) -> str:
    if op is None or isinstance(op, int):
        return ""
    if hasattr(op, "papel"):  # um vilão
        return op.papel + (f" · {op.titulo}" if op.titulo else "")
    return op.raridade + (f" · {op.origem}" if op.origem else "")


class LivreScene(_Base):
    def __init__(self, modo: str | None, escolha: dict, entrada, ao_lutar, ao_voltar) -> None:
        """`escolha`: chave -> id (é editada aqui); `ao_lutar(escolha)` começa a luta."""
        super().__init__(entrada, lambda: ao_voltar(self.escolha))
        self.ao_lutar = ao_lutar
        self.escolha = dict(escolha)
        base = livre.jornada_base(modo)
        self.linhas = list(livre.LINHAS) + [("lutar", "Lutar", None)]
        self.ops = {c: livre.opcoes(base, c, roda) for c, _r, roda in livre.LINHAS}
        self.cursor = len(self.linhas) - 1
        self.lista: str | None = None  # a linha com a lista inteira aberta
        self.i_lista = 0

    def _indice(self, chave: str) -> int:
        atual = self.escolha.get(chave)
        for i, op in enumerate(self.ops[chave]):
            if (op if isinstance(op, int) or op is None else op.id) == atual:
                return i
        return 0

    def _por(self, chave: str, i: int) -> None:
        op = self.ops[chave][i % len(self.ops[chave])]
        self.escolha[chave] = op if isinstance(op, int) or op is None else op.id

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        e = self.entrada
        if self.lista is not None:
            self._na_lista(e)
            return
        if self._sair():
            return
        if e.is_action_pressed("cima") or e.is_action_pressed("baixo"):
            passo = -1 if e.is_action_pressed("cima") else 1
            self.cursor = (self.cursor + passo) % len(self.linhas)
            som.tocar("mover")
            return
        chave = self.linhas[self.cursor][0]
        if chave == "lutar":
            if e.is_action_pressed("confirmar"):
                som.tocar("confirmar")
                self.ao_lutar(dict(self.escolha))
            return
        for acao, passo in (("esquerda", -1), ("direita", 1)):
            if e.is_action_pressed(acao):
                self._por(chave, self._indice(chave) + passo)
                som.tocar("mover")
        if e.is_action_pressed("confirmar") and chave != "capitulo":
            self.lista, self.i_lista = chave, self._indice(chave)
            som.tocar("confirmar")

    def _na_lista(self, e) -> None:
        n = len(self.ops[self.lista])
        if e.is_action_pressed("sair") or e.is_action_pressed("cancelar"):
            self.lista = None
            som.tocar("mover")
            return
        for acao, passo in (
            ("cima", -1),
            ("baixo", 1),
            ("esquerda", -VISIVEIS),
            ("direita", VISIVEIS),
        ):
            if e.is_action_pressed(acao):
                self.i_lista = (self.i_lista + passo) % n
                som.tocar("mover")
        if e.is_action_pressed("confirmar"):
            self._por(self.lista, self.i_lista)
            self.lista = None
            som.tocar("confirmar")

    def render(self, world, r) -> None:
        r.draw_ui_rect(0, 0, LARGURA, ALTURA, FUNDO)
        self._t(r, 480, 30, "研  Laboratório", 32, OURO, "center")
        aviso = "Modo livre: monte a build e o rival. Nada aqui salva nem conta para o Legado."
        self._t(r, 480, 74, aviso, 13, alpha(TINTA, 130), "center")
        if self.lista is not None:
            self._render_lista(r)
        else:
            for k, (chave, rotulo, _roda) in enumerate(self.linhas):
                y = TOPO + k * LINHA
                foco = k == self.cursor
                if foco:
                    r.draw_ui_rect(80, y - 4, LARGURA - 160, LINHA - 2, alpha(TINTA, 18))
                cor = OURO if foco else alpha(TINTA, 190)
                if chave == "lutar":
                    self._t(r, 480, y + 8, "戦  Lutar", 20, SANGUE_VIVO if foco else cor, "center")
                    continue
                op = self.ops[chave][self._indice(chave)]
                self._t(r, 100, y, rotulo, 15, alpha(TINTA, 150))
                self._t(r, 250, y, f"← {_nome(op)} →" if foco else _nome(op), 16, cor)
                self._t(
                    r, LARGURA - 96, y + 1, _detalhe(op)[:44], 12, alpha(TINTA, 120), "topright"
                )
            rodape = "↑ ↓ linha · ← → troca · Enter lista inteira · Esc volta"
            self._t(r, 480, ALTURA - 30, rodape, 14, alpha(TINTA, 110), "center")
        transicoes.revelar(self, r, self.relogio)

    def _render_lista(self, r) -> None:
        ops = self.ops[self.lista]
        rotulo = next(rot for c, rot, _ in self.linhas if c == self.lista)
        self._t(r, 480, 92, f"{rotulo} · {self.i_lista + 1} de {len(ops)}", 15, OURO, "center")
        inicio = min(max(0, self.i_lista - VISIVEIS // 2), max(0, len(ops) - VISIVEIS))
        for k, op in enumerate(ops[inicio : inicio + VISIVEIS]):
            y = TOPO + 12 + k * LINHA
            foco = inicio + k == self.i_lista
            if foco:
                r.draw_ui_rect(80, y - 4, LARGURA - 160, LINHA - 2, alpha(TINTA, 18))
            cor = OURO if foco else alpha(TINTA, 180)
            self._t(r, 100, y, _nome(op), 16, cor)
            self._t(r, LARGURA - 96, y + 1, _detalhe(op)[:52], 12, alpha(TINTA, 120), "topright")
        rodape = "↑ ↓ anda · ← → página · Enter escolhe · Esc fecha"
        self._t(r, 480, ALTURA - 30, rodape, 14, alpha(TINTA, 110), "center")

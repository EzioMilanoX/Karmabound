"""Tela da Crônica: os Feitos (à esquerda) e as últimas runs (à direita)."""

from __future__ import annotations

from ouroboros.interfaces.renderer import IRenderer

from karmabound import som, vfx
from karmabound.cronica import FEITOS, Cronica
from karmabound.rodas import carregar_balanceamento
from karmabound.tela_menus import _Base
from karmabound.visual import (
    ALTURA,
    FERRO,
    LACA,
    LARGURA,
    OURO,
    SANGUE_VIVO,
    TINTA,
    alpha,
    moldura,
    quebrar,
)


class CronicaScene(_Base):
    def __init__(self, cronica: Cronica, entrada, ao_voltar, ao_sair) -> None:
        super().__init__(entrada, ao_sair)
        self.cronica = cronica
        self.ao_voltar = ao_voltar
        modos = carregar_balanceamento()["combate"]["dificuldades"]
        self.nome_modo = {m: d["nome"] for m, d in modos.items() if not m.startswith("_")}

    def update(self, world, delta_time: float) -> None:
        self.relogio += delta_time
        som.musica("titulo")
        e = self.entrada
        if (
            e.is_action_pressed("cancelar")
            or e.is_action_pressed("sair")
            or e.is_action_pressed("confirmar")
        ):
            som.tocar("mover")
            self.ao_voltar()

    def render(self, world, r: IRenderer) -> None:
        self._fundo(r)
        c = self.cronica
        self._t(r, 36, 22, "記", 34, OURO)
        self._t(r, 80, 28, "Crônica", 24, TINTA)
        vencidas = sum(1 for x in c.runs if x["venceu"])
        self._t(
            r,
            LARGURA - 36,
            30,
            f"{len(c.runs)} runs · {vencidas} vitórias",
            16,
            alpha(TINTA, 140),
            "topright",
        )
        # os Feitos, em duas colunas
        self._t(r, 40, 76, f"Feitos  {len(c.feitos)} / {len(FEITOS)}", 18, OURO)
        for i, f in enumerate(FEITOS):
            x = 40 + (i % 2) * 230
            y = 110 + (i // 2) * 72
            feito = f.id in c.feitos
            r.draw_ui_rect(x, y, 216, 62, alpha(LACA, 255))
            moldura(r, x, y, x + 216, y + 62, OURO if feito else FERRO)
            self._t(r, x + 12, y + 10, f.kanji, 30, OURO if feito else alpha(TINTA, 60))
            self._t(r, x + 56, y + 10, f.nome, 15, TINTA if feito else alpha(TINTA, 110))
            for k, linha in enumerate(quebrar(f.texto, 24)[:2]):
                self._t(r, x + 56, y + 30 + k * 14, linha, 11, alpha(TINTA, 130 if feito else 80))
        # as últimas runs
        self._t(r, 520, 76, "Últimas runs", 18, OURO)
        if not c.runs:
            self._t(r, 520, 112, "Nenhuma run terminada ainda.", 15, alpha(TINTA, 110))
        for k, run in enumerate(reversed(c.runs[-12:])):
            y = 110 + k * 36
            cor = OURO if run["venceu"] else SANGUE_VIVO
            marca = "勝" if run["venceu"] else "敗"
            self._t(r, 520, y, marca, 20, cor)
            modo = self.nome_modo.get(run["modo"], run["modo"])
            dia = "  · semente do dia" if run.get("diaria") else ""
            self._t(r, 552, y + 2, f"{modo} · {run['lutas']} lutas{dia}", 15, TINTA)
            detalhe = (
                f"{run['dom'] or 'sem Dom'} · {run['despertares']} Despertar · {run['votos']} votos"
            )
            self._t(r, 552, y + 20, detalhe, 12, alpha(TINTA, 110))
        self._t(r, 480, ALTURA - 26, "Enter ou Backspace volta", 14, alpha(TINTA, 100), "center")
        vfx.vinheta(r, 0.7)
        vfx.revelar(r, self.relogio)

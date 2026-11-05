"""Aliados: um companheiro que luta do seu lado. Regras puras, sem tela.

Um por run. Não é alvo dos rivais (é como uma invocação permanente, com
personalidade): no começo de cada turno seu, a cada `cada` turnos, ele age com a
ação dele — fere o alvo, cura você, ergue bloqueio, expõe o alvo ou o envenena.
Cresce um nível a cada luta vencida. O combate recebe o aliado ao montar a luta
(`run.comecar_luta`); a run guarda só o id e o nível (`EstadoRun.aliado`,
`EstadoRun.aliado_nivel`). Os dados estão em `data/aliados.json`.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from karmabound.rodas import DADOS

ACOES = ("ferir", "curar", "bloquear", "expor", "envenenar")


@dataclass(frozen=True)
class Aliado:
    id: str
    nome: str
    kanji: str
    texto: str
    origem: str
    acao: str  # ferir | curar | bloquear | expor | envenenar
    valor: float  # a força no nível 1
    por_nivel: float  # o que cresce a cada nível
    cada: int = 1  # age a cada N turnos seus

    def valor_no_nivel(self, nivel: int) -> int:
        return max(1, int(self.valor + self.por_nivel * (max(1, nivel) - 1) + 1e-9))


@cache
def _dados(caminho: Path | None = None) -> tuple[int, tuple[Aliado, ...]]:
    d = json.loads((caminho or DADOS / "aliados.json").read_text(encoding="utf-8"))
    aliados = tuple(Aliado(**a) for a in d["aliados"])
    for a in aliados:
        if a.acao not in ACOES:
            raise ValueError(f"aliado {a.id}: ação desconhecida '{a.acao}'")
    return d["nivel_max"], aliados


def carregar_aliados() -> tuple[Aliado, ...]:
    return _dados()[1]


def nivel_maximo() -> int:
    return _dados()[0]


def aliado(aid: str) -> Aliado | None:
    """O aliado de id `aid` (None se vazio ou desconhecido)."""
    return next((a for a in carregar_aliados() if a.id == aid), None)


def sortear_aliado(rng: random.Random, atual: str = "") -> Aliado:
    """Quem chega para lutar ao seu lado (nunca o mesmo que você já tem)."""
    opcoes = [a for a in carregar_aliados() if a.id != atual] or list(carregar_aliados())
    return rng.choice(opcoes)

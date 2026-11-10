"""Os votos vinculativos do menu: jurados antes da run, valem a run inteira.

Você escolhe restrições (as do catálogo de votos) e ganha pontos; os pontos compram
ganhos que valem a run toda. Os preços são fixos, à vista: os valores típicos do
catálogo (`tipico`, medidos por tools/medir_tipicos.py) para uma run de LUTAS_DA_RUN
lutas. Quebrar o voto no meio da run cobra o preço de sempre (votos.py).

O motivo para jurar além do poder: cada restrição tem uma **recompensa** (votos.json,
`recompensa`), um item que só existe por ela. Vencer uma run com a restrição jurada e
sem quebrar o voto libera o item, que passa a sair nas rodas (legado.py, `desbloqueios`).
"""

from __future__ import annotations

from collections import Counter

from karmabound.votos import Catalogo, Clausula, Voto

LUTAS_DA_RUN = 12
MAX_RESTRICOES = 4


def pontos(cat: Catalogo, restricoes: list[str]) -> float:
    """Os pontos de um pacto com estas restrições."""
    escolhidas = [cat.restricoes[r] for r in restricoes if r in cat.restricoes]
    individuais = [r.tipico * LUTAS_DA_RUN for r in escolhidas]
    sacrificio = cat.creditado(sum(individuais), individuais)
    return cat.pontos(sacrificio, "run", escolhidas)


def preco(cat: Catalogo, ganho: Clausula, nivel: int) -> float:
    """O preço do `nivel`-ésimo nível de um ganho."""
    return cat.preco(ganho, ganho.tipico * LUTAS_DA_RUN, nivel)


def custo(cat: Catalogo, ganhos: list[str]) -> float:
    """O custo de todos os níveis comprados (um id repetido = um nível a mais)."""
    total = 0.0
    for gid, n in Counter(ganhos).items():
        g = cat.ganhos[gid]
        total += sum(preco(cat, g, k) for k in range(1, n + 1))
    return total


def cabe(cat: Catalogo, restricoes: list[str], ganhos: list[str], mais: str) -> bool:
    """Se mais um nível de `mais` cabe nos pontos (e ainda há nível a comprar)."""
    g = cat.ganhos[mais]
    if ganhos.count(mais) >= g.niveis:
        return False
    return custo(cat, [*ganhos, mais]) <= pontos(cat, restricoes) + 1e-9


def montar(cat: Catalogo, restricoes: list[str], ganhos: list[str]) -> Voto | None:
    """O voto jurado no começo da run (None sem restrição). Ganhos que não cabem saem."""
    escolhidas = [cat.restricoes[r] for r in restricoes if r in cat.restricoes]
    if not escolhidas:
        return None
    total = pontos(cat, restricoes)
    comprados: list[str] = []
    for gid in ganhos:
        if gid in cat.ganhos and cabe(cat, restricoes, comprados, gid):
            comprados.append(gid)
    voto = Voto(escolhidas, [cat.ganhos[g] for g in comprados], "run", pontos=total)
    voto.sobra = total - custo(cat, comprados)
    return voto

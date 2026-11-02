"""Rodas de sorteio: dados em JSON, sorteio por seed e raridade com pesos."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

DADOS = Path(__file__).parent / "data"
MODOS = ("aceita", "escolha")


@dataclass(frozen=True)
class Raridade:
    id: str
    nome: str
    peso: float
    cor: str


@dataclass(frozen=True)
class Fatia:
    id: str
    nome: str
    raridade: str
    texto: str = ""
    kanji: str = ""
    tags: tuple[str, ...] = ()
    peso: float = 1.0
    combate: dict | None = field(default=None, hash=False, compare=False)  # só técnicas
    evento: str = ""  # ex.: "altar" (o Juramento abre o Altar dos Votos)
    efeito: dict | None = field(default=None, hash=False, compare=False)  # Dons, Relíquias
    tecnica: dict | None = field(default=None, hash=False, compare=False)  # técnica de Dom
    regra: dict | None = field(default=None, hash=False, compare=False)  # Arcos


@dataclass(frozen=True)
class Roda:
    id: str
    nome: str
    modo: str
    opcoes: int
    fatias: tuple[Fatia, ...]
    kanji: str = ""

    def da_raridade(self, raridade: str) -> list[Fatia]:
        return [f for f in self.fatias if f.raridade == raridade]


def carregar_balanceamento(caminho: Path | None = None) -> dict:
    return json.loads((caminho or DADOS / "balanceamento.json").read_text(encoding="utf-8"))


def carregar_raridades(balanceamento: dict) -> list[Raridade]:
    """Raridades da mais comum para a mais rara: a ordem da lista é a ordem de valor."""
    return [Raridade(**r) for r in balanceamento["raridades"]]


def carregar_rodas(raridades: list[Raridade], caminho: Path | None = None) -> dict[str, Roda]:
    bruto = json.loads((caminho or DADOS / "rodas.json").read_text(encoding="utf-8"))
    ids_raridade = {r.id for r in raridades}
    rodas: dict[str, Roda] = {}
    for r in bruto["rodas"]:
        fatias = tuple(Fatia(**{**f, "tags": tuple(f.get("tags", ()))}) for f in r["fatias"])
        roda = Roda(r["id"], r["nome"], r["modo"], r.get("opcoes", 1), fatias, r.get("kanji", ""))
        _validar(roda, ids_raridade)
        rodas[roda.id] = roda
    return rodas


def _validar(roda: Roda, ids_raridade: set[str]) -> None:
    if roda.modo not in MODOS:
        raise ValueError(f"roda {roda.id}: modo '{roda.modo}' inválido (use {MODOS})")
    ids = [f.id for f in roda.fatias]
    if len(ids) != len(set(ids)):
        raise ValueError(f"roda {roda.id}: id de fatia repetido")
    desconhecidas = {f.raridade for f in roda.fatias} - ids_raridade
    if desconhecidas:
        raise ValueError(f"roda {roda.id}: raridade desconhecida {sorted(desconhecidas)}")
    faltando = ids_raridade - {f.raridade for f in roda.fatias}
    if faltando:
        raise ValueError(f"roda {roda.id}: sem fatia de {sorted(faltando)}")


def sortear_raridade(pesos: dict[str, float], rng: random.Random) -> str:
    ids = list(pesos)
    return rng.choices(ids, weights=[pesos[i] for i in ids])[0]


def sortear(
    roda: Roda,
    pesos: dict[str, float],
    rng: random.Random,
    forcar: str | None = None,
    excluir: frozenset[str] = frozenset(),
) -> Fatia:
    """Sorteia a raridade (ou usa `forcar`) e depois uma fatia dela, evitando `excluir`."""
    raridade = forcar or sortear_raridade(pesos, rng)
    candidatas = [f for f in roda.da_raridade(raridade) if f.id not in excluir]
    candidatas = candidatas or roda.da_raridade(raridade)
    return rng.choices(candidatas, weights=[f.peso for f in candidatas])[0]


def sortear_opcoes(roda: Roda, pesos: dict[str, float], rng: random.Random) -> list[Fatia]:
    """Modo "escolha": `roda.opcoes` fatias, sem repetir quando a roda permite."""
    escolhidas: list[Fatia] = []
    for _ in range(roda.opcoes):
        escolhidas.append(sortear(roda, pesos, rng, excluir=frozenset(f.id for f in escolhidas)))
    return escolhidas


def melhor_raridade(fatias: list[Fatia], ordem: list[str]) -> str:
    return max((f.raridade for f in fatias), key=ordem.index)

"""O modo História: campanhas com capítulos fixos, cenas e chefes fixos (data/historias.json).

Cada campanha tem 3 capítulos. Um capítulo fixa o Arco, os rivais com nome das portas
de rival e o chefe, e traz as cenas: `abertura` (antes do Arco), `antes_do_chefe` e
`depois` (depois de vencer o chefe). A campanha do Torneio da Roda tem ainda os dois
finais à escolha (`escolha`), o convite e o capítulo secreto (`alem`).

As campanhas de um anime jogam com as rodas daquele anime, como o Mundo de um anime.
As rodas continuam sorteando poderes: o que a História fixa é o caminho.

Os Arcos que só existem nas campanhas originais (fora da roda) ficam em `arcos`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from karmabound.rodas import DADOS, Fatia

ORIGINAL = "torneio_da_roda"  # a campanha principal (sem anime)
ARCO_ALEM = "alem_da_roda"  # o Arco do capítulo secreto


@dataclass(frozen=True)
class Linha:
    quem: str  # "" narração | "voce" | o id de um vilão
    texto: str


Cena = tuple[Linha, ...]


@dataclass(frozen=True)
class Capitulo:
    nome: str
    arco: str
    chefe: str
    rivais: tuple[str, ...] = ()
    abertura: Cena = ()
    antes_do_chefe: Cena = ()
    depois: Cena = ()


@dataclass(frozen=True)
class Final:
    id: str
    nome: str
    texto: Cena


@dataclass(frozen=True)
class Historia:
    id: str
    nome: str
    anime: str  # "" = original
    kanji: str
    resumo: str
    capitulos: tuple[Capitulo, ...]
    fim: Cena = ()
    derrota: Cena = ()
    escolha: tuple[Final, ...] = ()  # os finais à escolha depois do último chefe
    convite: Cena = ()  # o capítulo secreto chama (só quando ele já está aberto)
    alem: Capitulo | None = None

    def capitulo(self, n: int) -> Capitulo | None:
        """O capítulo `n` (1, 2, 3; o 4 é o secreto, se houver)."""
        if 1 <= n <= len(self.capitulos):
            return self.capitulos[n - 1]
        if n == len(self.capitulos) + 1:
            return self.alem
        return None


def _cena(bruta) -> Cena:
    linhas = []
    for item in bruta or ():
        if isinstance(item, str):
            linhas.append(Linha("", item))
        else:
            linhas.append(Linha(item.get("quem", ""), item["texto"]))
    return tuple(linhas)


def _capitulo(d: dict) -> Capitulo:
    return Capitulo(
        nome=d["nome"],
        arco=d["arco"],
        chefe=d["chefe"],
        rivais=tuple(d.get("rivais", ())),
        abertura=_cena(d.get("abertura")),
        antes_do_chefe=_cena(d.get("antes_do_chefe")),
        depois=_cena(d.get("depois")),
    )


def _historia(d: dict) -> Historia:
    return Historia(
        id=d["id"],
        nome=d["nome"],
        anime=d.get("anime", ""),
        kanji=d.get("kanji", ""),
        resumo=d.get("resumo", ""),
        capitulos=tuple(_capitulo(c) for c in d["capitulos"]),
        fim=_cena(d.get("fim")),
        derrota=_cena(d.get("derrota")),
        escolha=tuple(
            Final(f["id"], f["nome"], _cena(f.get("texto"))) for f in d.get("escolha", ())
        ),
        convite=_cena(d.get("convite")),
        alem=_capitulo(d["alem"]) if d.get("alem") else None,
    )


@cache
def _bruto(caminho: Path) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def carregar_historias(caminho: Path | None = None) -> dict[str, Historia]:
    """As campanhas, na ordem do arquivo (a original primeiro)."""
    bruto = _bruto(caminho or DADOS / "historias.json")
    return {h["id"]: _historia(h) for h in bruto["historias"]}


def carregar_arcos_da_historia(caminho: Path | None = None) -> dict[str, Fatia]:
    """Os Arcos que só existem nas campanhas originais (fora da roda do Arco)."""
    bruto = _bruto(caminho or DADOS / "historias.json")
    arcos = {}
    for a in bruto.get("arcos", ()):
        a = {k: v for k, v in a.items() if k != "arena"}
        arcos[a["id"]] = Fatia(**a)
    return arcos


def linhas_do_classico(caminho: Path | None = None) -> dict[str, Cena]:
    """As cenas do Clássico: o convite para além da Roda e o que se diz lá."""
    bruto = _bruto(caminho or DADOS / "historias.json")
    return {k: _cena(v) for k, v in bruto.get("classico", {}).items()}

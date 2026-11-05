"""Ressonância de anime: técnicas equipadas do mesmo anime se reforçam. Regras puras.

Com `minimo` (3) ou mais técnicas EQUIPADAS do mesmo anime (o anime é o fim da
`origem`, ver `rodas.anime_de`), um bônus temático vale enquanto elas estiverem lá;
com `minimo` + 1, o nível 2 (mais forte, no lugar do 1). O bônus é um `Efeitos` que
entra em `run.efeitos_do_estado` junto dos votos, do Dom e das Relíquias, então é
recalculado sempre que `atualizar_efeitos` roda (depois de receber ou trocar técnica
e das fusões). Anime sem entrada própria usa o bônus genérico.

Dados em `data/ressonancias.json`. A tela lê `ressonancias_ativas(estado)`.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from karmabound.efeitos import Efeitos
from karmabound.rodas import (
    DADOS,
    anime_de,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
    preencher,
)

if TYPE_CHECKING:
    from karmabound.run import EstadoRun

_PADRAO_EFEITOS = {k: v.default for k, v in Efeitos.__dataclass_fields__.items()}


@dataclass(frozen=True)
class Nivel:
    texto: str
    efeito: dict


@dataclass(frozen=True)
class Bonus:
    nome: str
    kanji: str
    niveis: tuple[Nivel, ...]


@dataclass(frozen=True)
class Ressonancia:
    """Uma ressonância ativa, para a tela."""

    anime: str
    nivel: int  # 1 ou 2
    tecnicas: int  # quantas técnicas do anime estão equipadas
    nome: str
    kanji: str
    texto: str


@dataclass(frozen=True)
class Tabela:
    minimo: int
    animes: dict[str, Bonus]
    generico: Bonus

    def bonus(self, anime: str) -> Bonus:
        return self.animes.get(anime, self.generico)


def _bonus(d: dict) -> Bonus:
    niveis = []
    for n in d["niveis"]:
        Efeitos.de_dict(n["efeito"])  # valida os campos já na carga
        texto = preencher(n["texto"], {**_PADRAO_EFEITOS, **n["efeito"]})
        niveis.append(Nivel(texto, dict(n["efeito"])))
    return Bonus(d["nome"], d["kanji"], tuple(niveis))


@lru_cache(maxsize=4)
def _tabela(caminho: Path) -> Tabela:
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    animes = {a: _bonus(b) for a, b in bruto["animes"].items()}
    return Tabela(bruto["minimo"], animes, _bonus(bruto["generico"]))


def carregar_ressonancias(caminho: Path | None = None) -> Tabela:
    return _tabela(caminho or DADOS / "ressonancias.json")


@lru_cache(maxsize=1)
def _anime_por_id() -> dict[str, str]:
    """O anime de toda técnica que pode estar equipada: as das rodas e as de fusão."""
    from karmabound.fusoes import tecnicas_de_fusao

    rodas = carregar_rodas(carregar_raridades(carregar_balanceamento()))
    fatias = [f for roda in rodas.values() for f in roda.fatias]
    fatias += list(tecnicas_de_fusao().values())
    return {f.id: anime_de(f.origem) for f in fatias if anime_de(f.origem)}


def contar_animes(estado: EstadoRun) -> Counter:
    """Quantas técnicas equipadas de cada anime (cada técnica conta uma vez)."""
    animes = _anime_por_id()
    ids = {t.id for t in estado.jogador.tecnicas}
    return Counter(animes[i] for i in ids if i in animes)


def ressonancias_ativas(estado: EstadoRun) -> list[Ressonancia]:
    """As ressonâncias que valem agora (anime, nível, nome, kanji, texto), a mais forte antes."""
    tabela = carregar_ressonancias()
    ativas = []
    for anime, n in contar_animes(estado).most_common():
        if n < tabela.minimo:
            break
        b = tabela.bonus(anime)
        nivel = min(n - tabela.minimo + 1, len(b.niveis))
        ativas.append(Ressonancia(anime, nivel, n, b.nome, b.kanji, b.niveis[nivel - 1].texto))
    return ativas


def efeitos_de_ressonancia(estado: EstadoRun) -> list[Efeitos]:
    """Os Efeitos das ressonâncias ativas (uma parte de `run.efeitos_do_estado`)."""
    tabela = carregar_ressonancias()
    partes = []
    for r in ressonancias_ativas(estado):
        partes.append(Efeitos.de_dict(tabela.bonus(r.anime).niveis[r.nivel - 1].efeito))
    return partes

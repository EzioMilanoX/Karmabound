"""Os vilões: rivais e chefes com nome, falas e técnicas próprias (data/viloes.json).

Como os chefes de um roguelite clássico, cada capítulo sorteia o chefe de uma lista,
e o último é sempre o mesmo:

- **tenente**: um rival comum com nome. Aparece a partir do `capitulo` dele e prefere as
  `tecnicas` da obra dele (as que cabem nas raridades do capítulo).
- **chefe**: chefe do capítulo 1 ou 2 (`capitulo`), com uma técnica-assinatura.
- **final**: o maior vilão de uma obra, com duas assinaturas. No Mundo de um anime ele
  fecha o capítulo 3; no Clássico, entra na lista do capítulo 2.
- O **Dono da Roda** (`final` sem obra) fecha o último capítulo do Clássico, sempre.
- O **Reflexo** (`secreto`) espera além da Roda: o capítulo secreto que abre depois de
  vencer o Dono algumas vezes (ver legado.py). Ele luta com as suas técnicas.

Regras puras, sem tela. A escolha é por seed (o `rng` da run) e evita repetir um vilão
na mesma run enquanto houver outro.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from karmabound.rodas import DADOS, anime_de

PAPEIS = ("tenente", "chefe", "final", "secreto", "meme")  # meme: chefes secretos (memes.py)
DONO = "dono_da_roda"  # o chefe fixo do último capítulo do Clássico
REFLEXO = "reflexo"  # o chefe do capítulo secreto
MECANICA_REFLEXO = "reflexo"  # a mecânica dele: copia as suas técnicas no começo da luta


@dataclass(frozen=True)
class Vilao:
    id: str
    nome: str
    papel: str
    capitulo: int
    titulo: str = ""
    origem: str = ""  # "personagem · obra"; vazio nos vilões do Torneio da Roda
    kanji: str = ""
    estilo: str = "espadachim"
    cor: str = ""
    assinaturas: tuple[str, ...] = ()
    tecnicas: tuple[str, ...] = ()
    falas: dict = field(default_factory=dict, hash=False, compare=False)
    imagens: str = ""  # chefe secreto: a pasta dos quadros em karmabound/data/memes/
    troca: float = 0.5  # chefe secreto: segundos por quadro (tosco de propósito)

    @property
    def anime(self) -> str:
        """A obra dele ("" = original do Torneio da Roda)."""
        return anime_de(self.origem)

    def fala(self, momento: str) -> str:
        """entrada | furia | derrota | vitoria ("" se ele não tem)."""
        return self.falas.get(momento, "")


@dataclass(frozen=True)
class Elenco:
    viloes: tuple[Vilao, ...]
    _por_id: dict = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_por_id", {v.id: v for v in self.viloes})
        ids = [v.id for v in self.viloes]
        repetidos = {i for i in ids if ids.count(i) > 1}
        if repetidos:
            raise ValueError(f"vilões repetidos: {sorted(repetidos)}")
        for v in self.viloes:
            if v.papel not in PAPEIS:
                raise ValueError(f"vilão {v.id}: papel '{v.papel}' não existe")

    def __getitem__(self, vid: str) -> Vilao:
        return self._por_id[vid]

    def get(self, vid: str) -> Vilao | None:
        return self._por_id.get(vid)

    def do_papel(self, papel: str, animes: frozenset[str] | None = None) -> list[Vilao]:
        """Os vilões do papel, das obras em `animes` (None: todas; "" = os originais)."""
        return [
            v for v in self.viloes if v.papel == papel and (animes is None or v.anime in animes)
        ]

    def final_de(self, anime: str) -> Vilao | None:
        return next((v for v in self.do_papel("final", frozenset({anime}))), None)

    @property
    def animes(self) -> list[str]:
        """As obras que têm vilões (sem os originais)."""
        return sorted({v.anime for v in self.viloes if v.anime})


def carregar_viloes(caminho: Path | None = None) -> Elenco:
    bruto = json.loads((caminho or DADOS / "viloes.json").read_text(encoding="utf-8"))
    viloes = []
    for d in bruto["viloes"]:
        d = dict(d)
        d["assinaturas"] = tuple(d.get("assinaturas", ()))
        d["tecnicas"] = tuple(d.get("tecnicas", ()))
        viloes.append(Vilao(**d))
    return Elenco(tuple(viloes))


# ----------------------------------------------------------------------- quem aparece


def _sortear(pool: list[Vilao], vistos: list[str], rng: random.Random) -> Vilao | None:
    """Um da lista, de preferência um que ainda não apareceu nesta run."""
    if not pool:
        return None
    novos = [v for v in pool if v.id not in vistos]
    return rng.choice(novos or pool)


def escolher_chefe(
    elenco: Elenco,
    capitulo: int,
    ultimo: bool,
    rng: random.Random,
    animes: frozenset[str] | None = None,
    anime: str = "",
    vistos: list[str] | None = None,
) -> Vilao | None:
    """O chefe de um capítulo.

    `ultimo`: é o último capítulo da run (o Dono, ou o final do anime). `anime`: no Mundo
    de um anime, só os vilões dele. `animes`: no Clássico, as obras já abertas (os
    originais estão sempre). O Reflexo (além da Roda) a run escolhe sozinha."""
    vistos = vistos or []
    if anime:
        if ultimo or capitulo >= 3:
            return elenco.final_de(anime) or _sortear(
                elenco.do_papel("chefe", frozenset({anime})), vistos, rng
            )
        so = frozenset({anime})
        pool = [v for v in elenco.do_papel("chefe", so) if v.capitulo == capitulo]
        return _sortear(pool or elenco.do_papel("chefe", so), vistos, rng)
    if ultimo:
        return elenco.get(DONO)
    obras = None if animes is None else animes | {""}
    pool = [v for v in elenco.do_papel("chefe", obras) if v.capitulo == min(capitulo, 2)]
    if capitulo >= 2:  # o maior vilão de cada obra também espera no meio do torneio
        pool += [v for v in elenco.do_papel("final", obras) if v.id != DONO]
    return _sortear(pool, vistos, rng)


def escolher_tenente(
    elenco: Elenco,
    capitulo: int,
    rng: random.Random,
    animes: frozenset[str] | None = None,
    anime: str = "",
    vistos: list[str] | None = None,
    lista: tuple[str, ...] = (),
) -> Vilao | None:
    """Um rival comum com nome. `lista`: os da cena (modo História), em ordem; senão os
    tenentes que já podem aparecer neste capítulo (os do capítulo primeiro)."""
    vistos = vistos or []
    if lista:
        ids = [i for i in lista if i not in vistos] or list(lista)
        return elenco.get(ids[0])
    obras = frozenset({anime}) if anime else (None if animes is None else animes | {""})
    pool = [v for v in elenco.do_papel("tenente", obras) if v.capitulo <= capitulo]
    agora = [v for v in pool if v.capitulo == capitulo and v.id not in vistos]
    return _sortear(agora or pool, vistos, rng)

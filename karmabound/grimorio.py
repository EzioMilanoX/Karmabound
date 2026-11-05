"""Grimório: as habilidades que já saíram da roleta, guardadas entre runs.

Um arquivo JSON pequeno com os ids vistos. O caminho padrão é
`~/.karmabound/grimorio.json`; a variável `KARMABOUND_SAVE` troca a pasta (os
testes usam uma pasta temporária). Só a Jornada (uma pessoa jogando) registra:
o piloto automático e o simulador nunca tocam no arquivo.

Além das fatias, o Grimório guarda o que o jogador já conheceu fora da roleta
(`extras`): as fusões que nasceram, os aliados que lutaram com ele e os afixos de
elite que enfrentou. O Fluxo registra esses.

No fim do arquivo, as pistas de combo que as telas de escolha mostram (sem desenhar
nada): se uma técnica é peça que falta numa fusão, se forma ou avança uma
Ressonância, e o que se perde ao tirar uma técnica.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from karmabound.rodas import Fatia

if TYPE_CHECKING:
    from karmabound.fusoes import Fusao
    from karmabound.run import EstadoRun

EXTRAS = ("fusoes", "aliados", "afixos")


def caminho_padrao() -> Path:
    pasta = os.environ.get("KARMABOUND_SAVE") or Path.home() / ".karmabound"
    return Path(pasta) / "grimorio.json"


class Grimorio:
    def __init__(self, caminho: Path | None = None) -> None:
        """`caminho=None`: só em memória (nada é salvo)."""
        self.caminho = caminho
        self.vistos: set[str] = set()
        self.extras: dict[str, set[str]] = {t: set() for t in EXTRAS}
        if caminho is not None and caminho.exists():
            try:
                dados = json.loads(caminho.read_text(encoding="utf-8"))
                self.vistos = set(dados["vistos"])
                for t in EXTRAS:
                    self.extras[t] = set(dados.get(t, []))
            except (ValueError, KeyError, TypeError):
                self.vistos = set()  # arquivo estragado: recomeça em vez de travar o jogo
                self.extras = {t: set() for t in EXTRAS}

    @classmethod
    def padrao(cls) -> Grimorio:
        return cls(caminho_padrao())

    def _salvar(self) -> None:
        if self.caminho is None:
            return
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        dados = {"vistos": sorted(self.vistos)}
        dados.update({t: sorted(ids) for t, ids in self.extras.items() if ids})
        self.caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")

    def ver(self, fatias: Iterable[Fatia]) -> list[Fatia]:
        """Registra as fatias que apareceram; devolve as que eram novas."""
        novas = [f for f in fatias if f.id not in self.vistos]
        if not novas:
            return []
        self.vistos.update(f.id for f in novas)
        self._salvar()
        return novas

    def viu(self, fatia_id: str) -> bool:
        return fatia_id in self.vistos

    def marcar(self, tipo: str, ids: Iterable[str]) -> list[str]:
        """Registra fusões, aliados ou afixos conhecidos (`tipo` em EXTRAS); devolve os novos."""
        conhecidos = self.extras[tipo]
        novos = [i for i in dict.fromkeys(ids) if i and i not in conhecidos]
        if novos:
            conhecidos.update(novos)
            self._salvar()
        return novos

    def conhece(self, tipo: str, id_: str) -> bool:
        return id_ in self.extras.get(tipo, ())


# ----------------------------------------------------------------------- pistas de combo


def fusao_descoberta(grimorio: Grimorio | None, fusao: Fusao) -> bool:
    """Se o jogador já viu esta fusão nascer (numa run qualquer)."""
    if grimorio is None:
        return False
    if grimorio.conhece("fusoes", fusao.id):
        return True
    from karmabound.fusoes import tecnicas_de_fusao  # a técnica que só nasce de fusão

    return fusao.resultado in tecnicas_de_fusao() and grimorio.viu(fusao.resultado)


@cache
def _anime_por_id() -> dict[str, str]:
    from karmabound.ressonancia import _anime_por_id as animes

    return animes()


def nivel_de_ressonancia(anime: str, n: int) -> int:
    """O nível que `n` técnicas equipadas de `anime` dão (0: nenhum)."""
    from karmabound.ressonancia import carregar_ressonancias

    tabela = carregar_ressonancias()
    if not anime or n < tabela.minimo:
        return 0
    return min(n - tabela.minimo + 1, len(tabela.bonus(anime).niveis))


def _contagem(estado: EstadoRun, sai: str = "", entra: str = "") -> Counter:
    """Técnicas equipadas por anime, com `sai` trocado por `entra` (ids; "" = nada)."""
    animes = _anime_por_id()
    ids = {t.id for t in estado.jogador.tecnicas} - {sai}
    if entra:
        ids.add(entra)
    return Counter(animes[i] for i in ids if i in animes)


@dataclass(frozen=True)
class Pista:
    """O que uma técnica faz pelo build, para o selo na tela de escolha."""

    fusoes: tuple[Fusao, ...] = ()  # fusões em que ela é peça que falta (a mais perto antes)
    completa: bool = False  # a primeira das `fusoes` nasce se ela entrar
    anime: str = ""  # a Ressonância que ela forma ou avança ("" = nenhuma)
    nivel: int = 0  # o nível que essa Ressonância teria

    def __bool__(self) -> bool:
        return bool(self.fusoes or self.anime)


def pista(estado: EstadoRun, fatia_id: str, fusoes: Iterable[Fusao], sai: str = "") -> Pista:
    """A pista de uma técnica oferecida (`sai`: a que ela substituiria, se houver)."""
    from karmabound.fusoes import faltam

    equipadas = {t.id for t in estado.jogador.tecnicas} - {sai}
    pecas = []
    if fatia_id not in equipadas:
        for f in fusoes:
            if f.id in estado.fusoes_nascidas:
                continue
            falta = faltam(f, estado)
            if any(r.tipo == "tecnica" and fatia_id in r.ids for r in falta):
                pecas.append((len(falta), f))
    pecas.sort(key=lambda x: x[0])
    anime, nivel = "", 0
    a = _anime_por_id().get(fatia_id, "")
    if a and fatia_id not in equipadas:
        antes = nivel_de_ressonancia(a, _contagem(estado, sai)[a])
        depois = nivel_de_ressonancia(a, _contagem(estado, sai, fatia_id)[a])
        if depois > antes:
            anime, nivel = a, depois
    completa = bool(pecas) and pecas[0][0] == 1
    return Pista(tuple(f for _, f in pecas), completa, anime, nivel)


@dataclass(frozen=True)
class Perda:
    """O que se desfaz ao tirar uma técnica (a tela de troca avisa)."""

    ressonancias: tuple[tuple[str, int, int], ...] = ()  # (anime, nível antes, nível depois)
    fusoes: tuple[Fusao, ...] = ()  # fusões que ainda não nasceram e perdem esta peça

    def __bool__(self) -> bool:
        return bool(self.ressonancias or self.fusoes)


def perda(estado: EstadoRun, sai: str, entra: str, fusoes: Iterable[Fusao]) -> Perda:
    """Trocar `sai` por `entra`: as Ressonâncias que caem e as peças de fusão que se vão."""
    antes, depois = _contagem(estado), _contagem(estado, sai, entra)
    caem = []
    for anime in sorted(antes):
        a = nivel_de_ressonancia(anime, antes[anime])
        d = nivel_de_ressonancia(anime, depois[anime])
        if d < a:
            caem.append((anime, a, d))
    pecas = []
    for f in fusoes:
        if f.id in estado.fusoes_nascidas:
            continue
        if any(r.tipo == "tecnica" and sai in r.ids and entra not in r.ids for r in f.requisitos):
            pecas.append(f)
    return Perda(tuple(caem), tuple(pecas))

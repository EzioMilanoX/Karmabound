"""Fusões: técnicas que nascem quando o jogador junta as peças certas. Regras puras.

Uma fusão tem requisitos: técnica equipada, o Dom, a Linhagem, uma Relíquia ou um
Despertar já disparado nesta run (`EstadoRun.despertares_ids`). Um requisito pode
ser "um de" (uma lista de alternativas). Quando todos estão cumpridos, a técnica
nasce, uma vez por run:

- se algum requisito é técnica equipada, a fusão toma o lugar da PRIMEIRA
  técnica-requisito (as outras ficam);
- se nenhum é técnica, ela entra como técnica nova (`receber_tecnica`): equipa se há
  espaço; se não, o resultado é "cheio" e quem chamou decide o que sai (a Jornada abre
  a fase de substituir; o piloto troca a pior).

`fundir` é o passo: confira depois de tudo que muda o que se tem (técnica recebida ou
trocada, Dom, Linhagem, Relíquia, e no fim da luta, pelo Despertar). Os dados estão em
`data/fusoes.json`: as fusões e as técnicas que só nascem delas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from karmabound.rodas import (
    DADOS,
    Fatia,
    _valores,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
    preencher,
)

if TYPE_CHECKING:
    from karmabound.run import Contexto, EstadoRun

TIPOS = ("tecnica", "dom", "linhagem", "reliquia", "despertar")


@dataclass(frozen=True)
class Requisito:
    tipo: str  # tecnica | dom | linhagem | reliquia | despertar
    ids: tuple[str, ...]  # mais de um: basta um deles


@dataclass(frozen=True)
class Fusao:
    id: str
    requisitos: tuple[Requisito, ...]
    fatia: Fatia  # a técnica que nasce

    @property
    def resultado(self) -> str:
        return self.fatia.id


@dataclass(frozen=True)
class Nascimento:
    """Uma fusão que nasceu agora, para a tela anunciar."""

    fusao: Fusao
    fatia: Fatia
    resultado: str  # "trocou" | "equipada" | "cheio" | "fragmento" | "evoluiu"
    saiu: str = ""  # a técnica-requisito cujo lugar a fusão tomou ("trocou")


def _fatia(f: dict) -> Fatia:
    return Fatia(
        **{**f, "tags": tuple(f.get("tags", ())), "texto": preencher(f["texto"], _valores(f))}
    )


def _requisito(d: dict) -> Requisito:
    if len(d) != 1:
        raise ValueError(f"requisito com mais de um tipo: {d}")
    tipo, ids = next(iter(d.items()))
    if tipo not in TIPOS:
        raise ValueError(f"tipo de requisito desconhecido: {tipo} (use {TIPOS})")
    return Requisito(tipo, tuple(ids) if isinstance(ids, list) else (ids,))


@lru_cache(maxsize=4)
def _carregar(caminho: Path) -> tuple[tuple[Fusao, ...], dict[str, Fatia], dict[str, str]]:
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    proprias = {f["id"]: _fatia(f) for f in bruto["tecnicas"]}
    rodas = carregar_rodas(carregar_raridades(carregar_balanceamento()))
    das_rodas = {f.id: f for roda in rodas.values() for f in roda.fatias}
    repetidas = set(proprias) & set(das_rodas)
    if repetidas:
        raise ValueError(f"técnica de fusão com id que já existe nas rodas: {sorted(repetidas)}")
    fusoes = []
    for d in bruto["fusoes"]:
        rid = d["resultado"]
        fatia = proprias.get(rid) or das_rodas.get(rid)
        if fatia is None or not fatia.combate:
            raise ValueError(f"fusão {d['id']}: resultado '{rid}' não é uma técnica")
        requisitos = tuple(_requisito(r) for r in d["requisitos"])
        for r in requisitos:
            for i in r.ids:
                if i not in das_rodas:
                    raise ValueError(f"fusão {d['id']}: requisito '{i}' não existe nas rodas")
        fusoes.append(Fusao(d["id"], requisitos, fatia))
    nomes = {i: f.nome for i, f in {**das_rodas, **proprias}.items()}
    return tuple(fusoes), proprias, nomes


def carregar_fusoes(caminho: Path | None = None) -> tuple[Fusao, ...]:
    """As fusões, com a técnica que nasce de cada uma já resolvida."""
    return _carregar(caminho or DADOS / "fusoes.json")[0]


def tecnicas_de_fusao(caminho: Path | None = None) -> dict[str, Fatia]:
    """As técnicas que só nascem de fusão (as que não estão nas rodas), por id."""
    return dict(_carregar(caminho or DADOS / "fusoes.json")[1])


# ----------------------------------------------------------------------- regras


def _tem(estado: EstadoRun, r: Requisito) -> bool:
    if r.tipo == "tecnica":
        return any(t.id in r.ids for t in estado.jogador.tecnicas)
    if r.tipo == "dom":
        return estado.dom is not None and estado.dom.id in r.ids
    if r.tipo == "linhagem":
        return estado.linhagem is not None and estado.linhagem.id in r.ids
    if r.tipo == "reliquia":
        return any(f.id in r.ids for f in estado.reliquias)
    return any(i in r.ids for i in estado.despertares_ids)


def cumpre(fusao: Fusao, estado: EstadoRun) -> bool:
    return all(_tem(estado, r) for r in fusao.requisitos)


def faltam(fusao: Fusao, estado: EstadoRun) -> list[Requisito]:
    """Os requisitos que o jogador ainda não tem (para uma dica na tela)."""
    return [r for r in fusao.requisitos if not _tem(estado, r)]


def lugar(fusao: Fusao, estado: EstadoRun) -> int | None:
    """O espaço que a fusão toma: o da primeira técnica-requisito (None: entra como nova)."""
    for r in fusao.requisitos:
        if r.tipo == "tecnica":
            for i, t in enumerate(estado.jogador.tecnicas):
                if t.id in r.ids:
                    return i
    return None


def fundir(estado: EstadoRun, ctx: Contexto) -> list[Nascimento]:
    """O passo: faz nascer toda fusão cumprida que ainda não nasceu nesta run.

    Uma fusão que nasce muda as técnicas (pode cumprir ou desfazer outra): confere de
    novo até nada mais nascer. Um resultado "cheio" fica para quem chamou trocar.
    """
    from karmabound.run import atualizar_efeitos, criar_tecnica, receber_tecnica

    nascidas: list[Nascimento] = []
    mudou = True
    while mudou:
        mudou = False
        for fusao in ctx.fusoes:
            if fusao.id in estado.fusoes_nascidas or not cumpre(fusao, estado):
                continue
            estado.fusoes_nascidas.append(fusao.id)
            tecnicas, fatia = estado.jogador.tecnicas, fusao.fatia
            i = lugar(fusao, estado)
            if i is not None and all(t.id != fatia.id for t in tecnicas):
                saiu = tecnicas[i].id
                tecnicas[i] = criar_tecnica(ctx, fatia)
                estado.fragmentos.pop(saiu, None)
                nascidas.append(Nascimento(fusao, fatia, "trocou", saiu))
            else:  # sem técnica-requisito (ou o resultado já está na mão: vira duplicata)
                nascidas.append(Nascimento(fusao, fatia, receber_tecnica(estado, ctx, fatia)))
            mudou = True
    if nascidas:
        atualizar_efeitos(estado)  # a Ressonância conta as técnicas equipadas
    return nascidas


def nomes_dos_requisitos(fusao: Fusao) -> list[str]:
    """'Olhos que Tudo Veem', 'Vazio Infinito'...: a receita, para a tela (um de: 'A ou B')."""
    nomes = _carregar(DADOS / "fusoes.json")[2]
    return [" ou ".join(nomes.get(i, i) for i in r.ids) for r in fusao.requisitos]

"""Votos vinculativos (blueprint GAM-11 O.A.T.H.): restrições viram poder.

O valor de uma restrição não é tabelado: é o potencial que ela tira do build
atual, medido por `run.medir` (continuações da run com e sem ela). Aqui ficam o
catálogo, a conversão em pontos, a duração e a quebra.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from karmabound.efeitos import Efeitos, somar
from karmabound.rodas import DADOS

DURACOES = ("luta", "capitulo", "run")


class FimDaRun(Exception):
    """Quebrar um voto de quebra encerra a run."""


@dataclass(frozen=True)
class Clausula:
    """Uma restrição ou um ganho do catálogo."""

    id: str
    nome: str
    kanji: str
    categoria: str
    texto: str
    efeito: Efeitos
    niveis: int = 1  # ganhos simples podem ser comprados várias vezes

    @property
    def exclusivo(self) -> bool:
        return self.categoria == "exclusivo"


@dataclass(frozen=True)
class Catalogo:
    restricoes: dict[str, Clausula]
    ganhos: dict[str, Clausula]
    limite_ativos: int
    K: float
    mult_duracao: dict[str, float]
    mult_categoria: dict[str, float]
    vida_perdida_na_quebra: float
    zera_carma_na_quebra: bool
    teto_por_restricao: float = 1.5
    preco_minimo: float = 0.05
    preco_exclusivo: float = 1.25
    preco_cambio: float = 1.0  # escala o poder total dos votos

    def creditado(self, sacrificio_voto: float, individuais: list[float]) -> float:
        """Retorno decrescente por restrição: cada uma credita no máximo `teto_por_restricao`.

        O voto credita o sacrifício medido junto (as restrições interagem), limitado à soma
        dos créditos de cada uma. Uma restrição devastadora sozinha não passa do teto: para
        ir além, é preciso juntar restrições diferentes.
        """
        teto = sum(min(max(s, 0.0), self.teto_por_restricao) for s in individuais)
        return max(0.0, min(sacrificio_voto, teto))

    def pontos(self, sacrificio: float, duracao: str, restricoes: list[Clausula]) -> float:
        """S × (1 + S / K) × duração × categoria, com S já creditado (ver `creditado`).

        S em lutas vencidas a menos no resto da run. A categoria de um voto com várias
        restrições é a média dos multiplicadores de cada uma.
        """
        if sacrificio <= 0 or not restricoes:
            return 0.0
        cat = sum(self.mult_categoria[r.categoria] for r in restricoes) / len(restricoes)
        return sacrificio * (1 + sacrificio / self.K) * self.mult_duracao[duracao] * cat

    def preco(self, ganho: Clausula, beneficio: float, nivel: int) -> float:
        """Preço do `nivel`-ésimo nível de um ganho: o benefício medido do 1º nível × nível."""
        base = max(beneficio, self.preco_minimo) * nivel
        return base * (self.preco_exclusivo if ganho.exclusivo else 1.0) * self.preco_cambio


def carregar_catalogo(caminho: Path | None = None) -> Catalogo:
    d = json.loads((caminho or DADOS / "votos.json").read_text(encoding="utf-8"))

    def clausulas(lista: list[dict]) -> dict[str, Clausula]:
        return {
            x["id"]: Clausula(
                x["id"],
                x["nome"],
                x["kanji"],
                x["categoria"],
                x["texto"],
                Efeitos.de_dict(x["efeito"]),
                x.get("niveis", 1),
            )
            for x in lista
        }

    b = d["bonus"]
    return Catalogo(
        restricoes=clausulas(d["restricoes"]),
        ganhos=clausulas(d["ganhos"]),
        limite_ativos=d["limite_ativos"],
        K=b["K"],
        mult_duracao={k: v["multiplicador"] for k, v in b["duracao"].items()},
        mult_categoria=b["categoria"],
        vida_perdida_na_quebra=d["quebra"]["vida_atual_perdida"],
        zera_carma_na_quebra=d["quebra"]["zera_carma"],
        teto_por_restricao=b["teto_por_restricao"],
        preco_minimo=d["precos"]["minimo"],
        preco_exclusivo=d["precos"]["exclusivo"],
        preco_cambio=d["precos"].get("cambio", 1.0),
    )


@dataclass
class Voto:
    restricoes: list[Clausula]
    ganhos: list[Clausula]
    duracao: str = "run"
    de_quebra: bool = False  # jurado para quebrar outro: quebrá-lo encerra a run
    lutas_restantes: int | None = None  # None = até o fim da run
    pontos: float = 0.0
    sacrificio: float = 0.0

    @property
    def efeitos(self) -> Efeitos:
        return somar([c.efeito for c in self.restricoes + self.ganhos])


def lutas_da_duracao(duracao: str, proxima_luta: int, lutas_por_capitulo: int) -> int | None:
    """Quantas lutas um voto dura, contando a próxima. Capítulo: até o chefe."""
    if duracao not in DURACOES:
        raise ValueError(f"duração '{duracao}' inválida (use {DURACOES})")
    if duracao == "luta":
        return 1
    if duracao == "capitulo":
        return lutas_por_capitulo - (proxima_luta - 1) % lutas_por_capitulo
    return None


@dataclass
class Votos:
    catalogo: Catalogo
    ativos: list[Voto] = field(default_factory=list)
    quebrados: list[Voto] = field(default_factory=list)

    def efeitos(self) -> Efeitos:
        return somar([v.efeitos for v in self.ativos])

    def pode_jurar(self) -> bool:
        return len(self.ativos) < self.catalogo.limite_ativos

    def jurar(self, voto: Voto) -> None:
        if not voto.de_quebra and not self.pode_jurar():
            raise ValueError("limite de votos ativos atingido")
        self.ativos.append(voto)

    def fim_de_luta(self) -> list[Voto]:
        """Desconta uma luta dos votos temporários; devolve os que expiraram (liberam espaço)."""
        expirados = []
        for v in self.ativos:
            if v.lutas_restantes is not None:
                v.lutas_restantes -= 1
                if v.lutas_restantes <= 0:
                    expirados.append(v)
        self.ativos = [v for v in self.ativos if v not in expirados]
        return expirados

    def quebrar(self, voto: Voto, voto_de_quebra: Voto | None, lutador, carma=None) -> None:
        """Quebra `voto`: perde os ganhos dele, sofre a punição e jura `voto_de_quebra`.

        Quebrar um voto de quebra encerra a run (`FimDaRun`). O espaço do voto quebrado é
        liberado e o voto de quebra ocupa um, então o total nunca passa do limite.
        """
        if voto not in self.ativos:
            raise ValueError("só dá para quebrar um voto ativo")
        if voto.de_quebra:
            raise FimDaRun("quebrou um voto de quebra")
        if voto_de_quebra is None or not voto_de_quebra.restricoes:
            raise ValueError("quebrar exige jurar um voto de quebra com ao menos uma restrição")
        self.ativos.remove(voto)
        self.quebrados.append(voto)
        lutador.vida -= round(lutador.vida * self.catalogo.vida_perdida_na_quebra)
        if carma is not None and self.catalogo.zera_carma_na_quebra:
            carma.valor = 0.0
        voto_de_quebra.de_quebra = True
        voto_de_quebra.ganhos = []  # o voto de quebra paga a dívida, não compra poder
        self.ativos.append(voto_de_quebra)
        lutador.aplicar_efeitos(self.efeitos())

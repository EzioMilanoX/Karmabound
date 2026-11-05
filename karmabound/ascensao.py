"""Ascensão: para quem já vence, a mesma run mais dura, um degrau por vez. Regras puras.

Níveis 1 a 10 por dificuldade. Vencer na Ascensão N abre a N+1 naquela dificuldade (o
`Legado` guarda). Cada nível acumula o seu modificador com os de baixo: a Ascensão 4
tem os modificadores 1, 2, 3 e 4. Tudo é aplicado nos dados do `Contexto`
(`aplicar_ascensao`), então o piloto, a simulação e a Jornada jogam a mesma regra.
A semente do dia joga na Ascensão 0.

Dados (nome, kanji, texto e modificador de cada nível) em `data/ascensao.json`.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from karmabound.rodas import DADOS, preencher

if TYPE_CHECKING:
    from karmabound.run import Contexto

# como cada modificador acumula de um nível para o outro
MULTIPLICA = ("vida_rivais_mult", "carma_giro_mult", "encruzilhada_preco", "encruzilhada_cura")
MENOR = ("oferta_treino",)
SOMA = ("cura_entre_lutas", "peso_elite", "chefe_tecnicas", "chance_reliquia")
SOMA += ("percepcao_rivais", "vida_jogador")


@dataclass(frozen=True)
class NivelAscensao:
    nivel: int
    nome: str
    kanji: str
    texto: str
    mod: dict


def _valores(mod: dict) -> dict:
    """Os números do texto (alguns já na forma em que a tela fala)."""
    return {
        **mod,
        "cura_pontos": round(-mod.get("cura_entre_lutas", 0) * 100),
        "reliquia_pontos": round(-mod.get("chance_reliquia", 0) * 100),
        "vida_menos": -mod.get("vida_jogador", 0),
    }


@lru_cache(maxsize=4)
def _carregar(caminho: Path) -> tuple[int, tuple[NivelAscensao, ...]]:
    bruto = json.loads(caminho.read_text(encoding="utf-8"))
    niveis = []
    for i, n in enumerate(bruto["niveis"], start=1):
        desconhecidos = set(n["mod"]) - set(MULTIPLICA + MENOR + SOMA)
        if desconhecidos:
            raise ValueError(f"Ascensão {i}: modificador desconhecido {sorted(desconhecidos)}")
        texto = preencher(n["texto"], _valores(n["mod"]))
        niveis.append(NivelAscensao(i, n["nome"], n["kanji"], texto, dict(n["mod"])))
    return bruto["maximo"], tuple(niveis)


def carregar_ascensao(caminho: Path | None = None) -> tuple[NivelAscensao, ...]:
    """Os níveis, do 1 ao máximo (o índice 0 é a Ascensão 1)."""
    return _carregar(caminho or DADOS / "ascensao.json")[1]


def maximo() -> int:
    return _carregar(DADOS / "ascensao.json")[0]


def niveis_ate(n: int) -> list[NivelAscensao]:
    """Os níveis que valem na Ascensão `n` (todos de 1 a n), para a tela listar."""
    return list(carregar_ascensao()[: max(0, n)])


def modificadores(n: int) -> dict:
    """Os modificadores acumulados da Ascensão `n` (0: nenhum)."""
    total: dict = {}
    for nivel in niveis_ate(n):
        for k, v in nivel.mod.items():
            if k in MULTIPLICA:
                total[k] = total.get(k, 1.0) * v
            elif k in MENOR:
                total[k] = min(total.get(k, v), v)
            else:
                total[k] = total.get(k, 0) + v
    return total


def aplicar_ascensao(ctx: Contexto, n: int) -> Contexto:
    """O Contexto com os modificadores da Ascensão `n` aplicados nos dados."""
    if n <= 0:
        return ctx
    if n > maximo():
        raise ValueError(f"Ascensão {n} não existe (máximo {maximo()})")
    m = modificadores(n)
    combate = copy.deepcopy(ctx.combate)
    rivais = combate["rivais"]
    vida = m.get("vida_rivais_mult", 1.0)
    rivais["vida_base"] *= vida
    rivais["vida_por_luta"] *= vida
    p = m.get("percepcao_rivais", 0)
    rivais["percepcao"] = [rivais["percepcao"][0] + p, rivais["percepcao"][1] + p]
    rivais["chefe_tecnicas_extra"] = rivais.get("chefe_tecnicas_extra", 0)
    rivais["chefe_tecnicas_extra"] += m.get("chefe_tecnicas", 0)
    combate["cura_entre_lutas"] = max(
        0.0, combate["cura_entre_lutas"] + m.get("cura_entre_lutas", 0)
    )
    combate["jogador"]["vida"] = max(1, combate["jogador"]["vida"] + m.get("vida_jogador", 0))
    giro = m.get("carma_giro_mult", 1.0)
    por_giro = {r: v * giro if v > 0 else v for r, v in ctx.config_carma.por_giro.items()}
    mudancas: dict = {
        "combate": combate,
        "config_carma": replace(ctx.config_carma, por_giro=por_giro),
        "oferta_treino": min(ctx.oferta_treino, m.get("oferta_treino", ctx.oferta_treino)),
        "chance_reliquia": max(0.0, ctx.chance_reliquia + m.get("chance_reliquia", 0)),
        "ascensao": n,
    }
    if ctx.caminho is not None:
        mudancas["caminho"] = _caminho(ctx.caminho, m)
    return replace(ctx, **mudancas)


def _caminho(cam, m: dict):
    pesos = dict(cam.pesos)
    if m.get("peso_elite"):
        pesos["elite"] = pesos.get("elite", 0) + m["peso_elite"]
    preco, cura = m.get("encruzilhada_preco", 1.0), m.get("encruzilhada_cura", 1.0)

    def opcao(o):
        return replace(
            o,
            custa_carma=round(o.custa_carma * preco),
            perde_vida_frac=min(0.9, o.perde_vida_frac * preco),
            vida_max=round(o.vida_max * preco) if o.vida_max < 0 else o.vida_max,
            cura=o.cura * cura,
        )

    eventos = tuple(replace(e, opcoes=tuple(opcao(o) for o in e.opcoes)) for e in cam.eventos)
    return replace(cam, pesos=pesos, eventos=eventos)

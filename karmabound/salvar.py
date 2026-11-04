"""A run salva: um espaço só, ao lado do Grimório (`~/.karmabound/run.sav`).

O Fluxo salva a cada fase. No meio de uma luta, o que vale é a foto tirada logo
antes dela (`Jornada.antes_da_luta`): ao continuar, a luta recomeça igual —
mesmo rival, mesma sorte —, então sair de uma luta ruim não sorteia outra.
Vitória ou derrota apagam o arquivo.

É um pickle local, do próprio jogo. Um arquivo de versão antiga ou estragado é
ignorado (a run some), nunca quebra o título.
"""

from __future__ import annotations

import copy
import json
import pickle
from pathlib import Path

from karmabound.grimorio import caminho_padrao
from karmabound.jornada import Jornada
from karmabound.run import JOGOS, Contexto

VERSAO = 1


def caminho() -> Path:
    return caminho_padrao().parent / "run.sav"


def salvar(jornada: Jornada) -> None:
    j = copy.copy(jornada)
    j.luta = None  # a luta tem callbacks e recomeça da foto
    j.grimorio = None
    if jornada.fase == "luta" and jornada.antes_da_luta is not None:
        j.estado, j.rng = pickle.loads(jornada.antes_da_luta)
    destino = caminho()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".tmp")
    temporario.write_bytes(pickle.dumps({"versao": VERSAO, "jornada": j}))
    temporario.replace(destino)  # nunca deixa um save pela metade


def carregar() -> Jornada | None:
    try:
        dados = pickle.loads(caminho().read_bytes())
        if dados.get("versao") != VERSAO:
            return None
        j = dados["jornada"]
        if not isinstance(j, Jornada):
            return None
    except Exception:  # sem arquivo, estragado ou de outra versão do código
        return None
    jogo, anime = getattr(j.ctx, "jogo", "classico"), getattr(j.ctx, "anime", "")
    # os dados de agora: um ajuste de balanceamento vale já
    j.ctx = Contexto.padrao(j.modo, jogo=jogo, anime=anime)
    if j.fase == "luta":
        j._comecar_luta()  # da foto de antes da luta: o mesmo rival
    return j


def apagar() -> None:
    try:
        caminho().unlink()
    except FileNotFoundError:
        pass


def caminho_recordes() -> Path:
    return caminho_padrao().parent / "recordes.json"


def _recordes() -> dict:
    try:
        return json.loads(caminho_recordes().read_text(encoding="utf-8"))
    except Exception:
        return {}


def registrar_diaria(data: str, lutas: int) -> int:
    """Guarda o resultado da semente do dia (fica o melhor); devolve o recorde do dia."""
    recordes = _recordes()
    recordes[data] = max(int(recordes.get(data, 0)), lutas)
    destino = caminho_recordes()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(recordes, indent=2), encoding="utf-8")
    return recordes[data]


def melhor_diaria(data: str) -> int | None:
    v = _recordes().get(data)
    return int(v) if v is not None else None


def resumo() -> str | None:
    """'Difícil · capítulo 2 · luta 6', ou None se não há run salva."""
    j = carregar()
    if j is None:
        return None
    nome = j.ctx.combate["dificuldades"][j.modo]["nome"]
    if j.ctx.jogo == "torre":
        return f"Torre sem fim · {nome} · andar {j.n_luta}"
    if j.ctx.jogo != "classico":
        jogo = j.ctx.anime if j.ctx.jogo == "anime" else JOGOS[j.ctx.jogo]
        return f"{jogo} · {nome} · luta {j.n_luta}"
    return f"{nome} · capítulo {j.capitulo} · luta {j.n_luta}"


def chave_torre(modo: str) -> str:
    return f"torre:{modo}"


def registrar_recorde(chave: str, lutas: int) -> int:
    """O melhor resultado guardado sob `chave` (a data da semente do dia, a Torre...)."""
    return registrar_diaria(chave, lutas)

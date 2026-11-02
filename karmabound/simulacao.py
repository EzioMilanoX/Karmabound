"""Simula runs inteiras para calibrar raridades e Carma.

O modelo de luta é deliberadamente simples (dano e custos aleatórios): serve para
medir o ritmo do Carma e as taxas, não para avaliar o combate.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field, replace

from karmabound.carma import ConfigCarma
from karmabound.mesa import Mesa
from karmabound.rodas import (
    Raridade,
    Roda,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
)


@dataclass(frozen=True)
class FormaDaRun:
    """Run curta (DESIGN.md): 3 capítulos de 3 lutas + chefe."""

    capitulos: int = 3
    lutas_por_capitulo: int = 4
    turnos_por_luta: int = 4
    dano_por_luta: tuple[float, float] = (0.2, 0.7)  # fração da vida perdida, uniforme
    chance_custo_por_turno: float = 0.15
    chance_reliquia_por_luta: float = 1 / 3

    @property
    def lutas(self) -> int:
        return self.capitulos * self.lutas_por_capitulo


@dataclass
class Resultado:
    runs: int
    despertares: Counter = field(default_factory=Counter)  # despertares por run -> nº de runs
    primeira_luta_despertar: list[int] = field(default_factory=list)
    giros_por_run: list[int] = field(default_factory=list)
    raridades_sorteadas: Counter = field(default_factory=Counter)  # giros normais, com pity
    runs_com_divino: int = 0

    @property
    def media_despertares(self) -> float:
        return sum(k * v for k, v in self.despertares.items()) / self.runs


def simular(
    runs: int = 10_000,
    seed: int = 1,
    forma: FormaDaRun | None = None,
    balanceamento: dict | None = None,
) -> Resultado:
    forma = forma or FormaDaRun()
    bal = balanceamento or carregar_balanceamento()
    raridades = carregar_raridades(bal)
    rodas = carregar_rodas(raridades)
    config = ConfigCarma.de_dict(bal["carma"])
    rng = random.Random(seed)
    res = Resultado(runs)
    for _ in range(runs):
        _simular_run(rodas, raridades, config, forma, rng, res)
    return res


def _simular_run(
    rodas: dict[str, Roda],
    raridades: list[Raridade],
    config: ConfigCarma,
    forma: FormaDaRun,
    rng: random.Random,
    res: Resultado,
) -> None:
    mesa = Mesa(rodas, raridades, config, rng)
    carma = mesa.carma
    topo = mesa.ordem[-1]
    giros = despertares = 0
    teve_divino = False
    primeira: int | None = None

    def girar(roda_id: str) -> None:
        nonlocal giros, teve_divino
        # Na run, o Despertar acontece em luta, não no giro.
        giro = mesa.girar(roda_id, permitir_despertar=False)
        res.raridades_sorteadas.update(f.raridade for f in giro.fatias)
        teve_divino |= any(f.raridade == topo for f in giro.fatias)
        giros += 1

    girar("destino")
    luta = 0
    for _ in range(forma.capitulos):
        girar("arco")
        for _ in range(forma.lutas_por_capitulo):
            luta += 1
            dano = rng.uniform(*forma.dano_por_luta)
            for _ in range(forma.turnos_por_luta):
                if carma.transbordando:  # o Despertar só acontece em luta
                    carma.despertar()
                    despertares += 1
                    teve_divino = True
                    primeira = primeira or luta
                carma.registrar_dano(dano / forma.turnos_por_luta)
                if rng.random() < forma.chance_custo_por_turno:
                    carma.registrar_custo()
            girar("tecnicas")
            if rng.random() < forma.chance_reliquia_por_luta:
                girar("reliquias")

    res.despertares[despertares] += 1
    res.giros_por_run.append(giros)
    res.runs_com_divino += teve_divino
    if primeira:
        res.primeira_luta_despertar.append(primeira)


# ---------------------------------------------------------------- com combate real


@dataclass
class ResultadoCombate:
    runs: int
    vitorias: int = 0  # runs que venceram as 12 lutas
    derrota_na_luta: Counter = field(default_factory=Counter)
    transbordos: Counter = field(default_factory=Counter)  # vezes que o Carma encheu, por run
    dano_por_luta: list[float] = field(default_factory=list)  # fração da vida máxima perdida
    turnos_por_luta: list[int] = field(default_factory=list)
    reacoes: int = 0
    golpes_perigosos_recebidos: int = 0

    @property
    def media_transbordos(self) -> float:
        return sum(k * v for k, v in self.transbordos.items()) / self.runs


def simular_com_combate(
    runs: int = 2_000,
    seed: int = 1,
    forma: FormaDaRun | None = None,
    balanceamento: dict | None = None,
    max_turnos: int = 80,
    dificuldade: str | None = None,
    altar=None,
    preparar=None,
) -> ResultadoCombate:
    """Runs inteiras com lutas de verdade (`run.py`), jogador no piloto automático.

    O Despertar ainda não existe: quando o Carma transborda, conta um transbordo e
    zera, para medir onde os Despertares cairiam. `altar`: o que fazer quando sai o
    Juramento (padrão: nada; `run.altar_auto` monta votos, mas é lento).
    `preparar(estado, ctx)`: mexe na run logo depois de criada (forçar um Dom, uma Relíquia).
    """
    from karmabound.run import Contexto, Registro, jogar_run, nova_run

    forma = forma or FormaDaRun()
    ctx = Contexto.padrao(dificuldade, balanceamento)
    ctx = replace(
        ctx,
        capitulos=forma.capitulos,
        lutas_por_capitulo=forma.lutas_por_capitulo,
        chance_reliquia=forma.chance_reliquia_por_luta,
        max_turnos=max_turnos,
    )
    rng = random.Random(seed)
    res = ResultadoCombate(runs)
    reg = Registro(res.dano_por_luta, res.turnos_por_luta)
    for _ in range(runs):
        estado = nova_run(ctx, rng)
        if preparar is not None:
            preparar(estado, ctx)
        estado = jogar_run(estado, ctx, rng, altar=altar, reg=reg)
        if estado.derrotado:
            res.derrota_na_luta[estado.proxima_luta] += 1
        else:
            res.vitorias += 1
        res.transbordos[estado.transbordos] += 1
    res.reacoes = reg.reacoes
    res.golpes_perigosos_recebidos = reg.golpes_perigosos_recebidos
    return res

"""Treino: depois de cada vitória, o jogador escolhe 1 de 3 e fica mais forte pelo resto
da run. Regras puras, sem tela.

A roleta dá a sorte; o treino dá a escolha. É o que faz o jogador crescer junto com os
rivais, que ganham vida a cada luta. Os treinos estão em `data/treinos.json`.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from karmabound.combate import Lutador
from karmabound.rodas import DADOS

# O piloto automático: abaixo disto, respira antes de qualquer outra coisa.
VIDA_PARA_RESPIRAR = 0.45
VELOCIDADE_QUE_BASTA = 4  # acima disso o rival quase nunca começa
PERCEPCAO_QUE_BASTA = 3


@dataclass(frozen=True)
class Treino:
    id: str
    nome: str
    kanji: str
    texto: str
    origem: str = ""
    vida_max: int = 0
    dano: int = 0
    velocidade: int = 0
    percepcao: int = 0
    cura: float = 0.0  # fração da vida máxima, na hora
    carma: float = 0.0


def carregar_treinos(caminho: Path | None = None) -> tuple[tuple[Treino, ...], int]:
    """Os treinos e quantos a oferta mostra."""
    bruto = json.loads((caminho or DADOS / "treinos.json").read_text(encoding="utf-8"))
    return tuple(Treino(**t) for t in bruto["treinos"]), bruto.get("oferta", 3)


def oferecer(treinos: tuple[Treino, ...], n: int, rng: random.Random) -> tuple[Treino, ...]:
    return tuple(rng.sample(treinos, min(n, len(treinos))))


def aplicar(jogador: Lutador, t: Treino) -> None:
    """O treino fica: mexe na base do lutador, que os efeitos não desfazem."""
    if t.vida_max:
        jogador.base_vida_max += t.vida_max
        jogador.vida += t.vida_max
    jogador.base_velocidade += t.velocidade
    jogador.base_percepcao += t.percepcao
    jogador.dano_run += t.dano
    jogador.aplicar_efeitos(jogador.efeitos)
    if t.cura:
        jogador.vida = min(jogador.vida_max, jogador.vida + round(jogador.vida_max * t.cura))
    if t.carma and jogador.carma is not None:
        jogador.carma.ganhar(t.carma * jogador.efeitos.carma_mult)


def escolher_auto(jogador: Lutador, oferta: tuple[Treino, ...]) -> Treino:
    """O piloto: respira se está mal; senão força, corpo, e o resto enquanto ainda vale."""

    def nota(t: Treino) -> float:
        if t.cura:
            return 10 if jogador.vida < jogador.vida_max * VIDA_PARA_RESPIRAR else 0.5
        if t.dano:
            return 5
        if t.vida_max:
            return 4
        if t.velocidade:
            return 3 if jogador.velocidade < VELOCIDADE_QUE_BASTA else 0.2
        if t.percepcao:
            return 2.5 if jogador.percepcao < PERCEPCAO_QUE_BASTA else 0.2
        return 1  # Carma

    return max(oferta, key=nota)

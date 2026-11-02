"""Mesa: uma sessão de giros — rodas, Carma e RNG. Regras puras, sem tela.

A tela da roleta e o simulador giram pela mesma Mesa, então o que a
simulação mede é o que o jogador vê.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from karmabound.carma import Carma, ConfigCarma
from karmabound.rodas import (
    Fatia,
    Raridade,
    Roda,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
    melhor_raridade,
    sortear,
    sortear_opcoes,
)


@dataclass(frozen=True)
class Giro:
    roda: Roda
    fatias: list[Fatia]  # 1 no modo "aceita" e no Despertar; `roda.opcoes` no modo "escolha"
    despertar: bool = False


class Mesa:
    def __init__(
        self,
        rodas: dict[str, Roda],
        raridades: list[Raridade],
        config_carma: ConfigCarma,
        rng: random.Random,
    ) -> None:
        self.rodas = rodas
        self.raridades = raridades
        self.ordem = [r.id for r in raridades]
        self.base = {r.id: r.peso for r in raridades}
        self.carma = Carma(config_carma)
        self.rng = rng

    @classmethod
    def padrao(cls, seed: int | None = None) -> Mesa:
        bal = carregar_balanceamento()
        raridades = carregar_raridades(bal)
        return cls(
            carregar_rodas(raridades),
            raridades,
            ConfigCarma.de_dict(bal["carma"]),
            random.Random(seed),
        )

    def taxas(self) -> dict[str, tuple[float, float]]:
        """Por raridade: (taxa publicada, taxa agora com o pity suave), em %."""
        agora = self.carma.pesos(self.base)
        total_base, total_agora = sum(self.base.values()), sum(agora.values())
        return {
            r: (100 * self.base[r] / total_base, 100 * agora[r] / total_agora) for r in self.ordem
        }

    def girar(
        self, roda_id: str, permitir_despertar: bool = True, forcar_despertar: bool = False
    ) -> Giro:
        """Gira `roda_id`. Com o Carma transbordando (e `permitir_despertar`),
        o giro vira o Despertar: uma fatia garantida da raridade máxima."""
        roda = self.rodas[roda_id]
        if roda.uniforme:  # Roda do Despertar: igual para todas as fatias, fora do Carma
            fatia = self.rng.choices(roda.fatias, weights=[f.peso for f in roda.fatias])[0]
            return Giro(roda, [fatia])
        if forcar_despertar:  # o prêmio de um Despertar feito na luta: o Carma já foi pago
            return Giro(roda, [sortear(roda, self.base, self.rng, forcar=self.ordem[-1])], True)
        if permitir_despertar and self.carma.transbordando:
            self.carma.despertar()
            return Giro(roda, [sortear(roda, self.base, self.rng, forcar=self.ordem[-1])], True)
        pesos = self.carma.pesos(self.base)
        if roda.modo == "escolha":
            fatias = sortear_opcoes(roda, pesos, self.rng)
        else:
            fatias = [sortear(roda, pesos, self.rng)]
        self.carma.registrar_giro(melhor_raridade(fatias, self.ordem))
        return Giro(roda, fatias)

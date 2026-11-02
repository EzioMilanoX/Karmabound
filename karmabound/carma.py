"""Carma: o pity compartilhado entre todas as rodas.

Enche com giros ruins, dano recebido e custos de poder. Acima de um limiar, aumenta
o peso das raridades altas (pity suave). Ao transbordar, trava até o Despertar,
que é o giro garantido da raridade máxima (pity duro).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigCarma:
    maximo: float
    por_giro: dict[str, float]
    por_dano_total: float
    por_custo: float
    pity_suave_inicio: float
    pity_suave_multiplicador: float
    pity_suave_raridades: tuple[str, ...]

    @classmethod
    def de_dict(cls, d: dict) -> ConfigCarma:
        return cls(**{**d, "pity_suave_raridades": tuple(d["pity_suave_raridades"])})


class Carma:
    def __init__(self, config: ConfigCarma, valor: float = 0.0) -> None:
        self.config = config
        self.valor = valor
        self.guardar = False  # Coração Selado: ao encher, vira um Despertar guardado
        self.guardados = 0

    @property
    def transbordando(self) -> bool:
        return self.valor >= self.config.maximo

    def _somar(self, quantia: float) -> None:
        if self.transbordando:
            return  # travado até o Despertar
        novo = max(self.valor + quantia, 0.0)
        if self.guardar and novo >= self.config.maximo:
            self.guardados += 1  # guarda na hora; o excedente continua acumulando
            novo -= self.config.maximo
        self.valor = min(novo, self.config.maximo)

    def ganhar(self, quantia: float) -> None:
        """Carma de recompensa (Rosário de Ossos, Arco do Juízo); respeita a trava."""
        self._somar(quantia)

    def registrar_giro(self, raridade: str) -> None:
        self._somar(self.config.por_giro.get(raridade, 0.0))

    def registrar_dano(self, fracao_da_vida: float) -> None:
        self._somar(fracao_da_vida * self.config.por_dano_total)

    def registrar_custo(self, vezes: float = 1) -> None:
        self._somar(vezes * self.config.por_custo)

    def pesos(self, base: dict[str, float]) -> dict[str, float]:
        """Pesos de raridade com o pity suave aplicado."""
        cfg = self.config
        if self.valor <= cfg.pity_suave_inicio:
            return dict(base)
        fracao = (self.valor - cfg.pity_suave_inicio) / (cfg.maximo - cfg.pity_suave_inicio)
        mult = 1 + min(fracao, 1.0) * (cfg.pity_suave_multiplicador - 1)
        return {r: p * mult if r in cfg.pity_suave_raridades else p for r, p in base.items()}

    def despertar(self) -> None:
        if not self.transbordando:
            raise RuntimeError("Despertar sem Carma transbordando")
        self.valor = 0.0

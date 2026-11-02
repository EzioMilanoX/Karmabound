"""Efeitos que votos (e, no futuro, Dons e Relíquias) aplicam a um lutador.

Valores neutros por padrão; `somar` combina vários. Os atributos (vida,
Velocidade, Percepção) são recalculados a partir da base do lutador por
`aplicar`, então tirar um efeito desfaz exatamente o que ele fez.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace


@dataclass(frozen=True)
class Efeitos:
    vida_max_mult: float = 1.0
    vida_max: int = 0
    velocidade: int = 0
    percepcao: int = 0
    bonus_dano: int = 0
    sem_cura: bool = False
    proibir_tipos: frozenset[str] = field(default_factory=frozenset)
    proibir_basico: bool = False
    percepcao_rival: int = 0
    limite_turnos: int | None = None  # turnos seus
    morte_abaixo: float = 0.0  # fração da vida máxima
    imperceptivel: bool = False
    revide_permanente: int = 0
    carma_mult: float = 1.0
    primeiro_sangue: bool = False
    reviver: int = 0  # vezes na run que volta ao cair
    dano_chefe_mult: float = 1.0
    sangue_frio: bool = False  # sempre reage à surpresa

    @classmethod
    def de_dict(cls, d: dict) -> Efeitos:
        d = dict(d)
        if "proibir_tipo" in d:
            d["proibir_tipos"] = frozenset([d.pop("proibir_tipo")])
        validos = {f.name for f in fields(cls)}
        desconhecidos = set(d) - validos
        if desconhecidos:
            raise ValueError(f"efeito desconhecido: {sorted(desconhecidos)}")
        return cls(**d)


NEUTRO = Efeitos()


def somar(lista: list[Efeitos]) -> Efeitos:
    total = NEUTRO
    for e in lista:
        limites = [x for x in (total.limite_turnos, e.limite_turnos) if x is not None]
        total = replace(
            total,
            vida_max_mult=total.vida_max_mult * e.vida_max_mult,
            vida_max=total.vida_max + e.vida_max,
            velocidade=total.velocidade + e.velocidade,
            percepcao=total.percepcao + e.percepcao,
            bonus_dano=total.bonus_dano + e.bonus_dano,
            sem_cura=total.sem_cura or e.sem_cura,
            proibir_tipos=total.proibir_tipos | e.proibir_tipos,
            proibir_basico=total.proibir_basico or e.proibir_basico,
            percepcao_rival=total.percepcao_rival + e.percepcao_rival,
            limite_turnos=min(limites) if limites else None,
            morte_abaixo=max(total.morte_abaixo, e.morte_abaixo),
            imperceptivel=total.imperceptivel or e.imperceptivel,
            revide_permanente=total.revide_permanente + e.revide_permanente,
            carma_mult=total.carma_mult * e.carma_mult,
            primeiro_sangue=total.primeiro_sangue or e.primeiro_sangue,
            reviver=total.reviver + e.reviver,
            dano_chefe_mult=total.dano_chefe_mult * e.dano_chefe_mult,
            sangue_frio=total.sangue_frio or e.sangue_frio,
        )
    return total

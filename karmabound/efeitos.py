"""Efeitos que votos, Dons e Relíquias aplicam a um lutador.

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
    sem_surpresa: bool = False  # a surpresa do rival não ganha bônus (Sentir a Intenção)
    # Dons e Relíquias
    esquiva: float = 0.0  # chance de um golpe inteiro errar (a única sorte dentro da luta)
    furia: float = 0.0  # dano extra máximo, proporcional à vida perdida
    sombra: float = 0.0  # a sombra repete esta fração de cada golpe
    escudo_inicial: int = 0  # golpes do rival ignorados no começo de cada luta
    cura_inicio: int = 0  # cura no início de cada luta
    salvacao: int = 0  # vezes na run que um golpe fatal deixa com 1 de vida
    carma_por_vitoria: float = 0.0
    bloqueio_mult: float = 1.0
    guarda_despertar: bool = False  # Coração Selado
    guarda_resto: float = 0.0  # Carma que sobra ao guardar um Despertar
    cura_mult: float = 1.0  # multiplica toda cura (entre lutas e no início da luta)
    evolucao_imediata: bool = False  # Fragmento do Deus Cego
    fator_evolucao: float = 1.3  # quanto uma evolução cresce
    basico_golpes: int = 0  # golpes extras do Golpe básico (Corpo Perfeito)
    basico_dano: int = 0
    regen: int = 0  # cura a cada turno seu (Carne que Volta)
    regen_ate: float = 1.0  # ...só enquanto a vida estiver abaixo desta fração
    sangria: int = 0  # vida perdida a cada turno seu (Portões Abertos)
    vida_por_vitoria: float = 0.0  # vida máxima por luta vencida, acumulada (Manto de Peso)
    dano_tecnicas_mult: float = 1.0  # técnicas, não o Golpe (Lâmina Adormecida)
    espacos_extra: int = 0  # espaços de técnica a mais (Fruta Proibida)
    eclipse: int = 0  # Despertares sem Carma na run (Ovo do Eclipse)
    # Expansão (Linhagens, Dons e Relíquias novos)
    drenar: float = 0.0  # cura esta fração de todo dano que você causa
    executar: float = 0.0  # +50% de dano contra quem está abaixo desta fração da vida
    sangrar: int = 0  # todo ataque que fere faz o alvo sangrar isto por 3 turnos dele
    recarga_menos: int = 0  # recargas das técnicas −N (mínimo 1; as de uma vez por luta não)
    primeiro_golpe: float = 0.0  # o primeiro ataque de cada luta causa +esta fração
    ultimo_suspiro: int = 0  # +dano enquanto você está abaixo de 30% da vida
    vida_cheia: int = 0  # +dano enquanto a sua vida está cheia
    dano_marcado: float = 0.0  # +esta fração contra quem tem Marca ou sangra
    bloqueio_inicio: int = 0  # começa cada luta com este bloqueio
    sutileza: int = 0  # +Sutileza em todos os seus golpes (mais difíceis de perceber)
    basico_perfura: bool = False  # o Golpe atravessa bloqueio
    crescer: float = 0.0  # +dano a cada turno seu na luta (acumula; vale a parte inteira)
    dano_mult: float = 1.0  # todo o seu dano
    dano_recebido_mult: float = 1.0  # todo dano que você sofre
    chance_reliquia: float = 0.0  # chance a mais de girar uma Relíquia depois da luta
    sem_despertar: bool = False  # voto: o Despertar fica selado

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
            sem_surpresa=total.sem_surpresa or e.sem_surpresa,
            esquiva=min(0.6, 1 - (1 - total.esquiva) * (1 - e.esquiva)),
            furia=total.furia + e.furia,
            sombra=total.sombra + e.sombra,
            escudo_inicial=total.escudo_inicial + e.escudo_inicial,
            cura_inicio=total.cura_inicio + e.cura_inicio,
            salvacao=total.salvacao + e.salvacao,
            carma_por_vitoria=total.carma_por_vitoria + e.carma_por_vitoria,
            bloqueio_mult=total.bloqueio_mult * e.bloqueio_mult,
            guarda_despertar=total.guarda_despertar or e.guarda_despertar,
            evolucao_imediata=total.evolucao_imediata or e.evolucao_imediata,
            guarda_resto=max(total.guarda_resto, e.guarda_resto),
            cura_mult=total.cura_mult * e.cura_mult,
            fator_evolucao=max(total.fator_evolucao, e.fator_evolucao),
            basico_golpes=total.basico_golpes + e.basico_golpes,
            basico_dano=total.basico_dano + e.basico_dano,
            regen=total.regen + e.regen,
            regen_ate=min(total.regen_ate, e.regen_ate) if e.regen else total.regen_ate,
            sangria=total.sangria + e.sangria,
            vida_por_vitoria=total.vida_por_vitoria + e.vida_por_vitoria,
            dano_tecnicas_mult=total.dano_tecnicas_mult * e.dano_tecnicas_mult,
            espacos_extra=total.espacos_extra + e.espacos_extra,
            eclipse=total.eclipse + e.eclipse,
            drenar=total.drenar + e.drenar,
            executar=max(total.executar, e.executar),
            sangrar=total.sangrar + e.sangrar,
            recarga_menos=total.recarga_menos + e.recarga_menos,
            primeiro_golpe=total.primeiro_golpe + e.primeiro_golpe,
            ultimo_suspiro=total.ultimo_suspiro + e.ultimo_suspiro,
            vida_cheia=total.vida_cheia + e.vida_cheia,
            dano_marcado=total.dano_marcado + e.dano_marcado,
            bloqueio_inicio=total.bloqueio_inicio + e.bloqueio_inicio,
            sutileza=total.sutileza + e.sutileza,
            basico_perfura=total.basico_perfura or e.basico_perfura,
            crescer=total.crescer + e.crescer,
            dano_mult=total.dano_mult * e.dano_mult,
            dano_recebido_mult=total.dano_recebido_mult * e.dano_recebido_mult,
            chance_reliquia=total.chance_reliquia + e.chance_reliquia,
            sem_despertar=total.sem_despertar or e.sem_despertar,
        )
    return total

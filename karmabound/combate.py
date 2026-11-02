"""Combate 1v1 por recarga. Regras puras, sem tela.

- Turnos alternados; quem tem mais Velocidade começa (empate: sorteio).
- A primeira ação da luta é um ataque surpresa: conta como perigosa e, se
  não for percebida, causa dano extra.
- No seu turno você usa uma técnica pronta; ela fica fora por `recarga`
  turnos seus. O Golpe básico nunca entra em recarga.
- Percepção: contra golpe perigoso, se a Percepção do alvo for maior ou
  igual à Sutileza do golpe, ele reage — leva metade e devolve um Golpe.
- O rival anuncia a próxima ação ao fim do turno dele e a cumpre; a
  Percepção do jogador decide quanto disso ele vê.
- O Despertar ainda não entra aqui (efeito e gatilho em aberto no design).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from karmabound.carma import Carma
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.rodas import Fatia


@dataclass(frozen=True)
class Tecnica:
    id: str
    nome: str
    tipo: str  # ataque | defesa | maldita
    raridade: str = "cinza"
    dano: int = 0
    golpes: int = 1
    recarga: int = 0
    sutileza: int = 0
    perigosa: bool = False
    bloqueio: int = 0  # absorve dano dos próximos golpes recebidos
    revide: int = 0  # devolve este dano no próximo golpe recebido
    custo_vida: int = 0  # paga com a própria vida (é um custo de poder: enche o Carma)
    marca: int = 0  # o alvo sofre isto toda vez que usar uma técnica
    fortalecer: int = 0  # +dano em todos os seus golpes pelo resto da luta
    dano_por_carma: float = 0.0  # dano extra = fator × Carma atual

    @classmethod
    def de_dict(cls, d: dict, raridade: str = "cinza") -> Tecnica:
        return cls(**{"raridade": raridade, **{k: v for k, v in d.items() if k != "raridade"}})

    @classmethod
    def de_fatia(cls, fatia: Fatia) -> Tecnica:
        if not fatia.combate:
            raise ValueError(f"fatia {fatia.id} não tem dados de combate")
        return cls(id=fatia.id, nome=fatia.nome, raridade=fatia.raridade, **fatia.combate)


@dataclass
class Lutador:
    nome: str
    vida_max: int
    velocidade: int
    percepcao: int
    tecnicas: list[Tecnica]
    vida: int = -1
    carma: Carma | None = None  # só o jogador tem Carma
    recargas: dict[str, int] = field(default_factory=dict)
    bloqueio: int = 0
    revide: int = 0
    marca: int = 0
    bonus_dano: int = 0
    efeitos: Efeitos = NEUTRO  # votos (e depois Dons/Relíquias) ativos
    chefe: bool = False
    revividas: int = 0  # Segunda Vida já usada nesta run (persiste entre lutas)
    base_vida_max: int = field(init=False)
    base_velocidade: int = field(init=False)
    base_percepcao: int = field(init=False)

    def __post_init__(self) -> None:
        self.base_vida_max = self.vida_max
        self.base_velocidade = self.velocidade
        self.base_percepcao = self.percepcao
        if self.vida < 0:
            self.vida = self.vida_max
        efeitos, self.efeitos = self.efeitos, NEUTRO
        if efeitos is not NEUTRO:
            self.aplicar_efeitos(efeitos)  # parte do neutro, para o Vigor contar como ganho

    def aplicar_efeitos(self, e: Efeitos) -> None:
        """Recalcula os atributos a partir da base: tirar um efeito desfaz o que ele fez."""
        self.vida_max = max(1, round(self.base_vida_max * e.vida_max_mult) + e.vida_max)
        # Só vida máxima GANHA (ex.: Vigor) chega cheia. Uma restrição que acaba devolve o
        # teto, não a vida perdida — senão jurar Corpo Ofertado por uma luta seria uma cura.
        ganho = e.vida_max - self.efeitos.vida_max
        if ganho > 0:
            self.vida += ganho
        self.vida = min(self.vida, self.vida_max)
        self.velocidade = self.base_velocidade + e.velocidade
        self.percepcao = max(0, self.base_percepcao + e.percepcao)
        self.efeitos = e

    @property
    def vivo(self) -> bool:
        return self.vida > 0

    def nova_luta(self) -> None:
        """Zera o que é da luta; a vida continua (persiste na run)."""
        self.recargas.clear()
        self.bloqueio = self.revide = self.marca = self.bonus_dano = 0

    def pronta(self, t: Tecnica) -> bool:
        return self.recargas.get(t.id, 0) == 0

    def sofrer(self, dano: int) -> int:
        dano = max(0, min(dano, self.vida))
        self.vida -= dano
        if self.carma is not None and dano:
            self.carma.registrar_dano(dano / self.vida_max * self.efeitos.carma_mult)
        if self.efeitos.morte_abaixo and self.vida < self.efeitos.morte_abaixo * self.vida_max:
            self.vida = 0  # Fio da Navalha
        if self.vida == 0 and self.revividas < self.efeitos.reviver:
            self.revividas += 1
            self.vida = max(1, round(self.vida_max * 0.3))  # Segunda Vida
        return dano


# Sem nenhuma técnica permitida pronta (ex.: voto Mãos Atadas), o lutador hesita.
HESITAR = Tecnica("hesitar", "Hesitar", "defesa")


@dataclass(frozen=True)
class Acao:
    ator: str
    tecnica: str
    dano: int  # dano total causado ao alvo
    surpresa: bool = False
    reagiu: bool = False  # o alvo percebeu o perigo e reagiu


class Luta:
    def __init__(
        self,
        jogador: Lutador,
        rival: Lutador,
        basico: Tecnica,
        rng: random.Random,
        bonus_surpresa: float = 0.5,
    ) -> None:
        self.jogador, self.rival = jogador, rival
        self.basico = basico
        self.rng = rng
        self.bonus_surpresa = bonus_surpresa
        self.estourou_prazo = False
        if jogador.efeitos.primeiro_sangue:
            self.vez = jogador
        elif jogador.velocidade != rival.velocidade:
            self.vez = jogador if jogador.velocidade > rival.velocidade else rival
        else:
            self.vez = rng.choice((jogador, rival))
        self.abertura = True
        self.turnos = 0
        self.log: list[Acao] = []
        # O rival já chega anunciando: se ele começa, é a emboscada; se não, é a resposta.
        self.intencao_rival: Tecnica | None = escolher_rival(self)

    @property
    def acabou(self) -> bool:
        return self.estourou_prazo or not (self.jogador.vivo and self.rival.vivo)

    @property
    def vencedor(self) -> Lutador | None:
        if not self.acabou:
            return None
        if self.estourou_prazo:
            return self.rival
        return self.jogador if self.jogador.vivo else self.rival

    def prontas(self, lutador: Lutador) -> list[Tecnica]:
        e = lutador.efeitos
        permitidas = [] if e.proibir_basico else [self.basico]
        permitidas += [
            t for t in lutador.tecnicas if lutador.pronta(t) and t.tipo not in e.proibir_tipos
        ]
        return permitidas or [HESITAR]

    def percepcao_contra(self, alvo: Lutador) -> int:
        """Percepção do alvo contra quem o ataca (o Voto Exposto dá Percepção ao rival)."""
        extra = self.jogador.efeitos.percepcao_rival if alvo is self.rival else 0
        return alvo.percepcao + extra

    def outro(self, lutador: Lutador) -> Lutador:
        return self.rival if lutador is self.jogador else self.jogador

    def ver_intencao(self) -> str | Tecnica | None:
        """O que o jogador enxerga da próxima ação do rival: nada, o tipo, ou a técnica."""
        p, t = self.jogador.percepcao, self.intencao_rival
        if t is None or p <= 0:
            return None
        return t.tipo if p == 1 else t

    def turno_rival(self) -> Acao:
        assert self.vez is self.rival
        tecnica = self.intencao_rival
        if tecnica is None or not (tecnica is self.basico or self.rival.pronta(tecnica)):
            tecnica = escolher_rival(self)
        return self.resolver(tecnica)

    def resolver(self, t: Tecnica) -> Acao:
        if self.acabou:
            raise RuntimeError("a luta já acabou")
        ator, alvo = self.vez, self.outro(self.vez)
        if t not in self.prontas(ator):
            raise ValueError(f"{ator.nome} não pode usar {t.nome} agora")

        if ator.marca:
            ator.sofrer(ator.marca)
        if t.custo_vida:
            ator.sofrer(t.custo_vida)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        ator.bonus_dano += t.fortalecer
        ator.bloqueio += t.bloqueio
        ator.revide += t.revide
        alvo.marca += t.marca

        surpresa, reagiu, total = self.abertura, False, 0
        base = t.dano + int(t.dano_por_carma * ator.carma.valor if ator.carma else 0)
        if base > 0 and ator.vivo:
            base += ator.bonus_dano + ator.efeitos.bonus_dano
            if alvo.chefe:
                base = round(base * ator.efeitos.dano_chefe_mult)  # Carrasco
            perigoso = t.perigosa or surpresa
            oculto = ator.efeitos.imperceptivel and t.perigosa
            emboscada = surpresa and ator.efeitos.primeiro_sangue
            sangue_frio = surpresa and alvo.efeitos.sangue_frio
            reagiu = (
                perigoso
                and not (oculto or emboscada)
                and (sangue_frio or self.percepcao_contra(alvo) >= t.sutileza)
            )
            for _ in range(t.golpes):
                dano = base // 2 if reagiu else base
                if surpresa and not reagiu:
                    dano = round(dano * (1 + self.bonus_surpresa))
                absorvido = min(alvo.bloqueio, dano)
                alvo.bloqueio -= absorvido
                total += alvo.sofrer(dano - absorvido)
                if alvo.revide and dano:
                    ator.sofrer(alvo.revide)
                    alvo.revide = 0
                if not alvo.vivo:
                    break
            if reagiu and alvo.vivo:
                ator.sofrer(self.basico.dano)  # o contra-golpe de quem sentiu o perigo

        for tid in list(ator.recargas):
            if ator.recargas[tid] > 0:
                ator.recargas[tid] -= 1
        if t not in (self.basico, HESITAR) and t.recarga:
            ator.recargas[t.id] = t.recarga
        if ator.efeitos.revide_permanente:
            ator.revide = max(ator.revide, ator.efeitos.revide_permanente)  # Pele de Espinhos

        acao = Acao(ator.nome, t.id, total, surpresa, reagiu)
        self.log.append(acao)
        self.abertura = False
        self.turnos += 1
        limite = self.jogador.efeitos.limite_turnos
        if limite and self.turnos >= 2 * limite and self.rival.vivo and self.jogador.vivo:
            self.estourou_prazo = True  # voto Prazo
        self.vez = alvo
        if ator is self.rival and not self.acabou:
            # Anuncia ao fim do próprio turno, para o jogador ver antes de escolher. A técnica
            # anunciada continua pronta até lá: recargas do rival só descem no turno dele.
            self.intencao_rival = escolher_rival(self)
        return acao


def _valor_ofensivo(luta: Luta, ator: Lutador, t: Tecnica) -> float:
    carma = ator.carma.valor if ator.carma else 0.0
    base = t.dano + t.dano_por_carma * carma
    extra = ator.bonus_dano + ator.efeitos.bonus_dano
    return (base + extra) * t.golpes if base > 0 else 0.0


def escolher_rival(luta: Luta) -> Tecnica:
    """IA simples do rival: defende quando está mal, prepara malditas cedo, senão bate forte."""
    rival, rng = luta.rival, luta.rng
    prontas = luta.prontas(rival)
    defesas = [t for t in prontas if t.tipo == "defesa"]
    if defesas and rival.vida < rival.vida_max * 0.4 and rng.random() < 0.5:
        return rng.choice(defesas)
    preparos = [t for t in prontas if t.tipo == "maldita" and _valor_ofensivo(luta, rival, t) == 0]
    if preparos and rng.random() < 0.6:
        return rng.choice(preparos)
    return max(prontas, key=lambda t: (_valor_ofensivo(luta, rival, t), rng.random()))


def escolher_jogador_auto(luta: Luta) -> Tecnica:
    """Piloto automático do jogador (simulação): defende o que vê chegando, senão bate forte."""
    j = luta.jogador
    prontas = luta.prontas(j)
    vista = luta.ver_intencao()
    defesas = [t for t in prontas if t.tipo == "defesa"]
    if isinstance(vista, Tecnica) and vista.perigosa and defesas:
        return max(defesas, key=lambda t: t.bloqueio + t.revide)
    if vista == "ataque" and defesas and j.vida < j.vida_max * 0.35:
        return defesas[0]
    preparos = [t for t in prontas if t.tipo == "maldita" and _valor_ofensivo(luta, j, t) == 0]
    if preparos:
        return preparos[0]
    return max(prontas, key=lambda t: _valor_ofensivo(luta, j, t))


def config_combate(balanceamento: dict, dificuldade: str | None = None) -> dict:
    """A seção `combate` com o modo de dificuldade aplicado (padrão: `dificuldade_padrao`)."""
    cfg = balanceamento["combate"]
    modo = dificuldade or cfg["dificuldade_padrao"]
    if modo not in cfg["dificuldades"] or modo.startswith("_"):
        validos = [m for m in cfg["dificuldades"] if not m.startswith("_")]
        raise ValueError(f"dificuldade '{modo}' não existe (use: {', '.join(validos)})")
    ajuste = cfg["dificuldades"][modo]
    return {
        **cfg,
        "dificuldade": modo,
        "rivais": {**cfg["rivais"], **ajuste.get("rivais", {})},
        "jogador": {**cfg["jogador"], **ajuste.get("jogador", {})},
    }

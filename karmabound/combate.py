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
- Dons e Relíquias entram por `Efeitos` (esquiva, fúria, sombra, escudo...) e
  pela técnica de Dom (`Lutador.tecnica_dom`), que não ocupa espaço.
- O Despertar ainda não entra aqui (efeito e gatilho em aberto no design).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

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
    marca: int = 0  # o alvo sofre isto a cada turno dele; Marcas se somam
    eco: int = 0  # o preço da Marca: quem marca sofre isto a cada turno seu
    fortalecer: int = 0  # +dano em todos os seus golpes pelo resto da luta
    dano_por_carma: float = 0.0  # dano extra = fator × Carma atual
    consome_carma: bool = False  # Julgamento: o Carma vira golpe e zera
    consome_tecnica: bool = False  # Contrato: cada uso destrói outra técnica sua
    cresce_ao_consumir: int = 0  # o demônio cresce: +dano para sempre a cada técnica consumida
    # técnicas de Dom
    copia_rival: bool = False  # Olho Roubado: usa a última técnica do rival
    copia_bonus: float = 1.0  # dano extra do golpe roubado
    cega_proprio: bool = False  # preço: Percepção 0 até o seu próximo turno
    santuario: int = 0  # Santuário: turnos seus de golpes imperceptíveis e +50%
    pular_depois: bool = False  # preço do Santuário: perde um turno quando ele acaba
    turno_extra: bool = False  # Instante Suspenso
    custo_carma: int = 0  # preço em Carma (consome, mesmo travado)
    nivel: int = 1  # duplicatas evoluem a técnica

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
    eco: int = 0
    bonus_dano: int = 0
    efeitos: Efeitos = NEUTRO  # votos (e depois Dons/Relíquias) ativos
    chefe: bool = False
    revividas: int = 0  # Segunda Vida já usada nesta run (persiste entre lutas)
    salvos: int = 0  # Amuleto Rachado já usado nesta run
    tecnica_dom: Tecnica | None = None  # a técnica do Dom: não ocupa espaço
    dano_extra: int = 0  # regra do Arco (Lua de Sangue), vale na luta
    dano_mult: float = 1.0  # regra do Arco (Arco do Juízo, no chefe)
    escudos: int = 0  # golpes ainda ignorados nesta luta (Pele de Cinzas)
    santuario: int = 0  # turnos de Santuário restantes
    pular: int = 0  # turnos que o lutador vai perder
    pular_pendente: bool = False  # perde um turno quando o Santuário acabar
    cego: bool = False  # Percepção 0 até o próximo turno dele
    extras: int = 0  # ações seguidas que ainda restam (Instante Suspenso)
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
        self.bloqueio = self.revide = self.marca = self.eco = self.bonus_dano = 0
        self.santuario = self.pular = 0
        self.pular_pendente = self.cego = False
        self.extras = 0
        self.dano_extra, self.dano_mult = 0, 1.0
        self.escudos = self.efeitos.escudo_inicial
        if self.efeitos.cura_inicio and not self.efeitos.sem_cura:
            cura = round(self.efeitos.cura_inicio * self.efeitos.cura_mult)
            self.vida = min(self.vida_max, self.vida + cura)  # Bandagem

    def pronta(self, t: Tecnica) -> bool:
        return self.recargas.get(t.id, 0) == 0

    def sofrer(self, dano: int) -> int:
        dano = max(0, min(dano, self.vida))
        self.vida -= dano
        if self.carma is not None and dano:
            self.carma.registrar_dano(dano / self.vida_max * self.efeitos.carma_mult)
        if self.efeitos.morte_abaixo and self.vida < self.efeitos.morte_abaixo * self.vida_max:
            self.vida = 0  # Fio da Navalha
        if self.vida == 0 and self.salvos < self.efeitos.salvacao:
            self.salvos += 1
            self.vida = 1  # Amuleto Rachado
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
    destruida: str = ""  # técnica que um Contrato consumiu
    esquivas: int = 0  # golpes que erraram por esquiva
    escudados: int = 0  # golpes ignorados pelo escudo
    sombra: int = 0  # dano da sombra (Sombra Leal)
    copiou: str = ""  # técnica copiada pelo Olho Roubado
    turno_extra: bool = False


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
        if lutador.pular:
            return [HESITAR]  # o preço do Santuário: este turno é perdido
        e = lutador.efeitos
        permitidas = [] if e.proibir_basico else [self.basico]
        candidatas = list(lutador.tecnicas)
        if lutador.tecnica_dom is not None:
            candidatas.append(lutador.tecnica_dom)
        permitidas += [t for t in candidatas if self._pode_usar(lutador, t)]
        return permitidas or [HESITAR]

    def _pode_usar(self, lutador: Lutador, t: Tecnica) -> bool:
        if not lutador.pronta(t) or t.tipo in lutador.efeitos.proibir_tipos:
            return False
        if t.consome_tecnica and len(lutador.tecnicas) < 2:
            return False  # o pacto exige um preço
        if t.custo_carma and (lutador.carma is None or lutador.carma.valor < t.custo_carma):
            return False
        if t.copia_rival and self.ultima_tecnica(self.outro(lutador)) is None:
            return False  # nada para roubar ainda
        return True

    def ultima_tecnica(self, de: Lutador) -> Tecnica | None:
        """A última técnica (não o Golpe) que `de` usou nesta luta."""
        conhecidas = {t.id: t for t in de.tecnicas}
        for acao in reversed(self.log):
            if acao.ator == de.nome and acao.tecnica in conhecidas:
                return conhecidas[acao.tecnica]
        return None

    def percepcao_contra(self, alvo: Lutador) -> int:
        """Percepção do alvo contra quem o ataca (o Voto Exposto dá Percepção ao rival)."""
        if alvo.cego:
            return 0
        extra = self.jogador.efeitos.percepcao_rival if alvo is self.rival else 0
        return alvo.percepcao + extra

    def outro(self, lutador: Lutador) -> Lutador:
        return self.rival if lutador is self.jogador else self.jogador

    def ver_intencao(self) -> str | Tecnica | None:
        """O que o jogador enxerga da próxima ação do rival: nada, o tipo, ou a técnica."""
        p, t = self.jogador.percepcao, self.intencao_rival
        if t is None or p <= 0 or self.jogador.cego:
            return None
        return t.tipo if p == 1 else t

    def turno_rival(self) -> Acao:
        assert self.vez is self.rival
        tecnica = self.intencao_rival
        if tecnica is None or not (tecnica is self.basico or self.rival.pronta(tecnica)):
            tecnica = escolher_rival(self)
        return self.resolver(tecnica)

    def resolver(self, t: Tecnica, sacrificio: Tecnica | None = None) -> Acao:
        """Usa `t`. `sacrificio`: a técnica que um Contrato destrói (padrão: a mais fraca)."""
        if self.acabou:
            raise RuntimeError("a luta já acabou")
        ator, alvo = self.vez, self.outro(self.vez)
        if t not in self.prontas(ator):
            raise ValueError(f"{ator.nome} não pode usar {t.nome} agora")
        ator.cego = False  # a cegueira dura até o próximo turno de quem a sofreu
        if t is HESITAR and ator.pular:
            ator.pular -= 1

        efetiva = t
        if t.copia_rival:
            efetiva = self.ultima_tecnica(alvo)  # Olho Roubado
        if t.custo_carma and ator.carma is not None:
            ator.carma.valor = max(0.0, ator.carma.valor - t.custo_carma)

        if ator.marca:
            ator.sofrer(ator.marca)  # Marca da Maldição
        if ator.eco:
            ator.sofrer(ator.eco)  # o preço de ter marcado alguém
        if efetiva.custo_vida:
            ator.sofrer(efetiva.custo_vida)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        ator.bonus_dano += efetiva.fortalecer
        ator.bloqueio += round(efetiva.bloqueio * ator.efeitos.bloqueio_mult)
        ator.revide += efetiva.revide
        alvo.marca += efetiva.marca
        ator.eco += efetiva.eco
        ativou_santuario = efetiva.santuario > 0
        if ativou_santuario:
            ator.santuario = efetiva.santuario
            ator.pular_pendente = efetiva.pular_depois

        surpresa, reagiu, total = self.abertura, False, 0
        esquivas = escudados = sombra = 0
        base = efetiva.dano + int(efetiva.dano_por_carma * ator.carma.valor if ator.carma else 0)
        if efetiva.consome_carma and ator.carma is not None:
            ator.carma.valor = 0.0  # a dor vira golpe: o Despertar que vinha se vai junto
        if base > 0 and ator.vivo:
            perdida = 1 - max(0, ator.vida) / ator.vida_max
            fervor = round(ator.efeitos.furia * perdida)  # Sangue Fervente
            base += ator.bonus_dano + ator.efeitos.bonus_dano + fervor + ator.dano_extra
            base = round(base * ator.dano_mult * (t.copia_bonus if t.copia_rival else 1.0))
            if alvo.chefe:
                base = round(base * ator.efeitos.dano_chefe_mult)  # Carrasco
            santuario = ator.santuario > 0 and not ativou_santuario
            if santuario:
                base = round(base * 1.5)
            perigoso = efetiva.perigosa or surpresa
            oculto = (ator.efeitos.imperceptivel and efetiva.perigosa) or santuario
            emboscada = surpresa and ator.efeitos.primeiro_sangue
            sangue_frio = surpresa and alvo.efeitos.sangue_frio
            reagiu = (
                perigoso
                and not (oculto or emboscada)
                and (sangue_frio or self.percepcao_contra(alvo) >= efetiva.sutileza)
            )

            def golpear(dano: int) -> int:
                nonlocal esquivas, escudados
                if alvo.efeitos.esquiva and self.rng.random() < alvo.efeitos.esquiva:
                    esquivas += 1  # Reflexo Treinado
                    return 0
                if alvo.escudos:
                    alvo.escudos -= 1  # Pele de Cinzas
                    escudados += 1
                    return 0
                absorvido = min(alvo.bloqueio, dano)
                alvo.bloqueio -= absorvido
                feito = alvo.sofrer(dano - absorvido)
                if alvo.revide and dano:
                    ator.sofrer(alvo.revide)
                    alvo.revide = 0
                return feito

            por_golpe = base // 2 if reagiu else base
            if surpresa and not reagiu:
                por_golpe = round(por_golpe * (1 + self.bonus_surpresa))
            for _ in range(efetiva.golpes):
                total += golpear(por_golpe)
                if not alvo.vivo:
                    break
            if ator.efeitos.sombra and alvo.vivo and ator.vivo:
                sombra = golpear(round(por_golpe * ator.efeitos.sombra))  # Sombra Leal
                total += sombra
            if reagiu and alvo.vivo:
                ator.sofrer(self.basico.dano)  # o contra-golpe de quem sentiu o perigo

        for tid in list(ator.recargas):
            if ator.recargas[tid] > 0:
                ator.recargas[tid] -= 1
        if t not in (self.basico, HESITAR) and t.recarga:
            ator.recargas[t.id] = t.recarga
        if ator.efeitos.revide_permanente:
            ator.revide = max(ator.revide, ator.efeitos.revide_permanente)  # Pele de Espinhos
        if ator.santuario and not ativou_santuario:
            ator.santuario -= 1
            if ator.santuario == 0 and ator.pular_pendente:
                ator.pular, ator.pular_pendente = ator.pular + 1, False

        destruida = ""
        if efetiva.consome_tecnica:
            outras = [x for x in ator.tecnicas if x.id != efetiva.id]
            alvo_pacto = sacrificio if sacrificio in outras else min(outras, key=valor_tecnica)
            ator.tecnicas.remove(alvo_pacto)
            ator.recargas.pop(alvo_pacto.id, None)
            destruida = alvo_pacto.id
            if efetiva.cresce_ao_consumir and efetiva in ator.tecnicas:
                i = ator.tecnicas.index(efetiva)
                ator.tecnicas[i] = replace(efetiva, dano=efetiva.dano + efetiva.cresce_ao_consumir)
        if t.cega_proprio:
            ator.cego = True  # o preço do Olho Roubado
        if t.turno_extra:
            ator.extras += 2  # o Instante não conta: duas ações de verdade depois dele

        extra = ator.extras > 0 and ator.vivo and alvo.vivo
        if extra:
            ator.extras -= 1
        copiou = efetiva.id if t.copia_rival else ""
        acao = Acao(
            ator.nome,
            t.id,
            total,
            surpresa,
            reagiu,
            destruida,
            esquivas,
            escudados,
            sombra,
            copiou,
            extra,
        )
        self.log.append(acao)
        self.abertura = False
        self.turnos += 1
        limite = self.jogador.efeitos.limite_turnos
        if limite and self.turnos >= 2 * limite and self.rival.vivo and self.jogador.vivo:
            self.estourou_prazo = True  # voto Prazo
        if not extra:  # Instante Suspenso: a vez continua com quem agiu
            self.vez = alvo
        if ator is self.rival and not self.acabou:
            # Anuncia ao fim do próprio turno, para o jogador ver antes de escolher. A técnica
            # anunciada continua pronta até lá: recargas do rival só descem no turno dele.
            self.intencao_rival = escolher_rival(self)
        return acao


def _valor_ofensivo(luta: Luta, ator: Lutador, t: Tecnica) -> float:
    if t.copia_rival:
        roubada = luta.ultima_tecnica(luta.outro(ator))
        return _valor_ofensivo(luta, ator, roubada) if roubada else 0.0
    carma = ator.carma.valor if ator.carma else 0.0
    base = t.dano + t.dano_por_carma * carma
    extra = ator.bonus_dano + ator.efeitos.bonus_dano
    return (base + extra) * t.golpes if base > 0 else 0.0


ROMANOS = ("", "", " II", " III", " IV", " V")


def evoluir(t: Tecnica, fator: float = 1.3) -> Tecnica:
    """A técnica no nível seguinte: efeitos ×1,3 (ao menos +1) e recarga −1 (mínimo 1)."""

    def cresce(v: int) -> int:
        return max(v + 1, round(v * fator)) if v else 0

    nivel = t.nivel + 1
    nome = " ".join(p for p in t.nome.split(" ") if p not in ("II", "III", "IV", "V"))
    recarga = t.recarga if t.recarga in (0, 99) else max(1, t.recarga - 1)
    return replace(
        t,
        nivel=nivel,
        nome=nome + ROMANOS[min(nivel, len(ROMANOS) - 1)],
        dano=cresce(t.dano),
        bloqueio=cresce(t.bloqueio),
        revide=cresce(t.revide),
        marca=cresce(t.marca),
        fortalecer=cresce(t.fortalecer),
        recarga=recarga,
    )


def valor_tecnica(t: Tecnica) -> float:
    """Valor bruto de uma técnica, para escolher o que um Contrato sacrifica."""
    return t.dano * t.golpes + t.bloqueio + t.revide + 3 * (t.marca + t.fortalecer)


def _vale_o_preco(luta: Luta, j: Lutador, t: Tecnica) -> bool:
    """Poderes que custam caro só valem na hora certa.

    Carma e técnica consumidos: para fechar a luta ou num chefe. Marca: só em luta que
    ainda vai durar (rival com vida) e sem empilhar além de duas — o preço também se soma.
    """
    if t.marca:
        return luta.rival.vida >= 12 and luta.rival.marca < 2 * t.marca
    if t.santuario:
        return luta.rival.vida >= 20 and j.santuario == 0
    if t.turno_extra:  # sem preço, sempre; com preço em Carma, só se sobra Carma
        return not t.custo_carma or (j.carma is not None and j.carma.valor >= t.custo_carma + 30)
    if not (t.consome_carma or t.consome_tecnica):
        return True
    if t.consome_carma:
        mata = _valor_ofensivo(luta, j, t) >= luta.rival.vida
        return mata or (j.carma is not None and j.carma.valor >= 60)
    return luta.rival.vida >= 20  # Contrato: usa em toda luta que ainda vai durar; o demônio cresce


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
    prontas = [t for t in luta.prontas(j) if _vale_o_preco(luta, j, t)] or luta.prontas(j)
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

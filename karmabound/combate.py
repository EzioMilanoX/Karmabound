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
- Despertar: com o Carma cheio (ou um Despertar guardado), o jogador desperta
  quando quiser — não gasta o turno — ou sozinho, quando um golpe do rival o
  mataria (o golpe é anulado). O tipo sai da Roda do Despertar.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from karmabound.carma import Carma
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.rodas import Fatia
from karmabound.votos_luta import Promessa


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
    livre: bool = False  # não gasta o turno: você usa e ainda age
    custo_carma: int = 0  # preço em Carma (consome, mesmo travado)
    perfura: bool = False  # atravessa bloqueio (Espiral Concentrada)
    absoluto: bool = False  # atravessa bloqueio, escudo e esquiva (Corte do Mundo)
    critico: float = 0.0  # chance de o golpe sair ×2,5 (Clarão Negro)
    sempre_surpresa: bool = False  # todo uso conta como ataque surpresa (Primeiro Trovão)
    selar: int = 0  # a próxima ação do alvo vai para a recarga (Corrente do Julgamento)
    cura: int = 0  # cura quem usa (Mão Curadora)
    escudo: int = 0  # golpes recebidos que passam através (Desvio Dimensional)
    dano_por_dor: float = 0.0  # dano extra = fator × a dor que quem usa sofreu na luta
    teto_dor: int = 0  # o máximo desse extra (0 = sem teto)
    atordoar: int = 0  # turnos que o alvo perde (Lua Ilusória)
    inicia_em_recarga: int = 0  # começa cada luta em recarga (Corte do Mundo)
    # Expansão
    sangrar: int = 0  # o alvo sangra isto a cada turno dele, por 3 turnos (renova e soma)
    drenar: float = 0.0  # cura esta fração do dano causado
    executar: float = 0.0  # dano ×2 se o alvo estiver abaixo desta fração da vida
    enfraquecer: int = 0  # o alvo causa −N em todo golpe pelo resto da luta
    cegar: int = 0  # o alvo não percebe os próximos N golpes (e o jogador cego não lê o rival)
    expor: int = 0  # os próximos N golpes contra o alvo causam +50%
    acelerar: int = 0  # suas outras técnicas em recarga descem N
    dissipar: bool = False  # desfaz bloqueio, revide, escudos e espelho do alvo antes de golpear
    acumula: int = 0  # +N de dano nesta técnica a cada uso, até o fim da luta
    gravidade: float = 0.0  # dano extra = fração da vida atual do alvo (até TETO_GRAVIDADE)
    detonar: int = 0  # consome Marca e sangramento do alvo: +N × o que restava
    combo: int = 0  # +N de dano por técnica sua em recarga
    desespero: float = 0.0  # dano extra = fração da vida que você já perdeu
    bomba: int = 0  # planta um golpe que explode depois de `bomba_turnos` turnos do alvo
    bomba_turnos: int = 2
    instinto: int = 0  # os próximos N ataques do rival têm 60% de errar e revidam
    intocavel: int = 0  # os próximos N turnos do rival não ferem
    fera: int = 0  # por N turnos seus, todo ataque acerta uma vez a mais
    foco: int = 0  # +Percepção até o fim da luta
    silenciar: int = 0  # o alvo só pode usar o Golpe por N turnos dele
    desarmar: int = 0  # o alvo não pode defender por N turnos dele
    espelho: int = 0  # os próximos N golpes recebidos voltam inteiros a quem golpeou
    regenerar: int = 0  # cura N a cada turno seu até o fim da luta
    variacao: int = 0  # dano extra sorteado entre 0 e N
    custo_vida_max: int = 0  # preço: −N de vida máxima pelo resto da run, a cada uso
    nivel: int = 1  # duplicatas evoluem a técnica

    @classmethod
    def de_dict(cls, d: dict, raridade: str = "cinza") -> Tecnica:
        dados = {k: v for k, v in d.items() if k not in ("raridade", "origem")}
        return cls(**{"raridade": raridade, **dados})

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
    forma: int = 0  # turnos de Forma Desperta: dano dobrado, sem recarga
    retrib_golpes: int = 0  # golpes de Retribuição que ainda restam
    retrib_por_golpe: int = 0
    dor: int = 0  # dano sofrido nesta luta (Esfera dos Mil)
    instinto: int = 0  # ataques do rival que o Instinto Puro ainda pode esquivar
    percepcao_luta: int = 0  # Percepção extra só nesta luta (Modo Eremita)
    eclipses: int = 0  # Ovo do Eclipse já usado nesta run
    fera: int = 0  # turnos de Fera Interior: todo ataque acerta uma vez a mais
    intocavel: int = 0  # turnos do rival que não ferem (Vazio Infinito)
    tecnica_linhagem: Tecnica | None = None  # a técnica da Linhagem: não ocupa espaço
    dano_run: int = 0  # +dano pelo resto da run (Despertares que ensinam)
    # Expansão: o que é só da luta (zera em `nova_luta`)
    sangue: int = 0  # sangramento por turno
    sangue_turnos: int = 0
    cegueira: int = 0  # golpes que este lutador ainda não percebe
    exposto: int = 0  # golpes recebidos que ainda causam +50%
    acumulos: dict[str, int] = field(default_factory=dict)
    bombas: list[list[int]] = field(default_factory=list)  # [turnos, dano]
    silencio: int = 0
    desarme: int = 0
    espelho: int = 0
    regen_luta: int = 0
    crescido: float = 0.0  # o quanto o Esquentar já acumulou nesta luta
    drenar_luta: float = 0.0
    absolutos: int = 0  # próximos ataques absolutos (votos e Despertares)
    atacou: bool = False  # já atacou nesta luta (Primeiro Golpe)
    sem_despertar: bool = False  # voto de luta: o Despertar está selado
    proibir_luta: frozenset[str] = frozenset()  # voto de luta: tipos selados
    sem_basico_luta: bool = False
    recarga_menos_luta: int = 0
    imperceptivel_luta: bool = False
    sem_percepcao: bool = False  # voto de luta: a Percepção selada
    percepcao_rival_luta: int = 0  # voto de luta: o que o rival ganha de Percepção
    revelar: float = 0.0  # Revelação: bônus da próxima técnica usada (e dela na luta)
    revelada: str = ""
    revelada_bonus: float = 0.0
    dano_mult_luta: float = 1.0  # votos de luta
    recebido_mult_luta: float = 1.0
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
        self.forma = self.retrib_golpes = self.retrib_por_golpe = 0
        self.dor = self.instinto = self.percepcao_luta = 0
        self.fera = self.intocavel = 0
        self.dano_extra, self.dano_mult = 0, 1.0
        self.sangue = self.sangue_turnos = self.cegueira = self.exposto = 0
        self.acumulos, self.bombas = {}, []
        self.silencio = self.desarme = self.espelho = self.regen_luta = self.absolutos = 0
        self.drenar_luta = self.crescido = 0.0
        self.atacou = self.sem_despertar = self.sem_basico_luta = False
        self.imperceptivel_luta = self.sem_percepcao = False
        self.proibir_luta = frozenset()
        self.recarga_menos_luta = self.percepcao_rival_luta = 0
        self.revelar = self.revelada_bonus = 0.0
        self.revelada = ""
        self.dano_mult_luta = self.recebido_mult_luta = 1.0
        self.escudos = self.efeitos.escudo_inicial
        self.bloqueio = self.efeitos.bloqueio_inicio
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


CRITICO = 2.5  # o Clarão Negro
TETO_GRAVIDADE = 25  # o máximo que a gravidade tira da vida do alvo de uma vez

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
    despertou: str = ""  # Despertar disparado à beira da morte durante esta ação
    critico: bool = False  # o Clarão Negro saiu
    curou: int = 0
    selou: str = ""  # técnica do alvo que a Corrente selou
    atordoou: bool = False
    instintos: int = 0  # ataques esquivados pelo Instinto Puro


class Luta:
    def __init__(
        self,
        jogador: Lutador,
        rival: Lutador,
        basico: Tecnica,
        rng: random.Random,
        bonus_surpresa: float = 0.5,
        ao_despertar=None,
        espacos: int = 4,
        ao_eclipse=None,
        voto_luta=None,
    ) -> None:
        """`ao_despertar()`: gira a Roda do Despertar e devolve a fatia (quem monta a luta
        cuida dos contadores e do giro Divino depois). Sem ela, não há Despertar.
        `ao_eclipse()`: cobra o preço do Ovo do Eclipse (o Dom)."""
        self.jogador, self.rival = jogador, rival
        self.ao_despertar = ao_despertar
        self.ao_eclipse = ao_eclipse
        self._antes_da_liberacao: dict[str, Tecnica] = {}  # técnicas antes do Bankai
        for lutador in (jogador, rival):
            for t in lutador.tecnicas:
                if t.inicia_em_recarga:
                    lutador.recargas[t.id] = max(lutador.recargas.get(t.id, 0), t.inicia_em_recarga)
        self.espacos = espacos  # para o Tomar o Destino saber se precisa trocar uma técnica
        self.dano_recebido = 0  # a dor do jogador nesta luta (base da Retribuição)
        self.vida_inicial = jogador.vida  # Retorno pela Morte volta para cá
        self.ultimo_despertar = None  # a fatia do último Despertar, para a tela
        self.basico = basico
        self.rng = rng
        self.bonus_surpresa = bonus_surpresa
        self.estourou_prazo = False
        self.voto_luta = voto_luta  # o voto de luta que a roleta ofereceu (VotoDeLuta)
        self.voto_jurado = False
        self.promessa: Promessa | None = None
        self.promessa_resultado = ""  # "" | "cumprida" | "quebrada"
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
        sem_basico = e.proibir_basico or lutador.sem_basico_luta
        permitidas = [] if sem_basico else [self.basico]
        if lutador.silencio:
            return permitidas or [HESITAR]  # silenciado: só o Golpe
        candidatas = list(lutador.tecnicas)
        for extra in (lutador.tecnica_dom, lutador.tecnica_linhagem):
            if extra is not None:
                candidatas.append(extra)
        permitidas += [t for t in candidatas if self._pode_usar(lutador, t)]
        return permitidas or [HESITAR]

    def _pode_usar(self, lutador: Lutador, t: Tecnica) -> bool:
        if not lutador.pronta(t) or t.tipo in lutador.efeitos.proibir_tipos:
            return False
        if t.tipo in lutador.proibir_luta or (lutador.desarme and t.tipo == "defesa"):
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

    def pode_despertar(self) -> bool:
        c = self.jogador.carma
        return (
            self.ao_despertar is not None
            and c is not None
            and not self.acabou
            and not self.jogador.sem_despertar
            and not self.jogador.efeitos.sem_despertar
            and (c.transbordando or c.guardados > 0)
        )

    # ------------------------------------------------------------- voto de luta

    def pode_jurar_luta(self) -> bool:
        return (
            self.voto_luta is not None
            and not self.voto_jurado
            and not self.acabou
            and self.vez is self.jogador
        )

    def jurar_luta(self) -> None:
        """Jura o voto de luta oferecido: não gasta o turno."""
        if not self.pode_jurar_luta():
            raise RuntimeError("não há voto de luta para jurar agora")
        v = self.voto_luta
        self.voto_jurado = True
        self.aplicar(v.agora)
        if v.condicao:
            cond, valor = next(iter(v.condicao.items()))
            if cond == "dano_em":
                meta, turnos = valor
                self.promessa = Promessa(cond, turnos, meta=meta)
            else:
                self.promessa = Promessa(cond, valor if cond != "sem_defesa" else 0)

    def _fechar_promessa(self, cumpriu: bool) -> None:
        v, self.promessa = self.voto_luta, None
        self.promessa_resultado = "cumprida" if cumpriu else "quebrada"
        self.aplicar(v.premio if cumpriu else v.falha)

    def _depois_da_acao(self, acao: Acao, ator: Lutador, t: Tecnica) -> None:
        """Acompanha a promessa: cumprida ou quebrada, conforme a ação."""
        p = self.promessa
        if p is None or not self.jogador.vivo:
            return
        if not self.rival.vivo:
            self._fechar_promessa(True)  # a luta foi vencida dentro do prazo
            return
        do_jogador = ator is self.jogador
        if p.condicao == "vencer_em" and do_jogador:
            p.restante -= 1
            if p.restante <= 0:
                self._fechar_promessa(False)
        elif p.condicao == "sem_dano" and not do_jogador:
            if acao.dano > 0:
                self._fechar_promessa(False)
            else:
                p.restante -= 1
                if p.restante <= 0:
                    self._fechar_promessa(True)
        elif p.condicao == "so_golpe" and do_jogador:
            if t not in (self.basico, HESITAR):
                self._fechar_promessa(False)
            else:
                p.restante -= 1
                if p.restante <= 0:
                    self._fechar_promessa(True)
        elif p.condicao == "sem_defesa" and do_jogador and t.tipo == "defesa":
            self._fechar_promessa(False)
        elif p.condicao == "dano_em" and do_jogador:
            p.feito += acao.dano
            p.restante -= 1
            if p.feito >= p.meta:
                self._fechar_promessa(True)
            elif p.restante <= 0:
                self._fechar_promessa(False)

    def pode_eclipse(self) -> bool:
        """Ovo do Eclipse: desperta sem Carma, uma vez por run."""
        j = self.jogador
        return (
            self.ao_despertar is not None
            and not self.acabou
            and not (j.sem_despertar or j.efeitos.sem_despertar)
            and j.eclipses < j.efeitos.eclipse
        )

    def despertar(self, eclipse: bool = False):
        """Desperta: paga o Carma (ou um Despertar guardado), gira a Roda e aplica o tipo.
        `eclipse`: o Ovo do Eclipse paga no lugar do Carma (e cobra o Dom)."""
        j, carma = self.jogador, self.jogador.carma
        if eclipse:
            if not self.pode_eclipse():
                raise RuntimeError("o Ovo do Eclipse já foi usado")
            j.eclipses += 1
            if self.ao_eclipse is not None:
                self.ao_eclipse()
        elif not self.pode_despertar():
            raise RuntimeError("não há Despertar disponível")
        elif carma.guardados:
            carma.guardados -= 1
        else:
            carma.valor = 0.0
        fatia = self.ao_despertar()
        self.aplicar(fatia.despertar or {})
        self.ultimo_despertar = fatia
        return fatia

    def aplicar(self, d: dict) -> None:
        """Efeitos de luta de um Despertar ou de um voto de luta, a favor do jogador.

        Chaves de preço (`perde_vida_frac`, `carma`, `sem_*`...) também moram aqui: o
        voto de luta paga e recebe pelo mesmo caminho.
        """
        j, rival, carma = self.jogador, self.rival, self.jogador.carma
        if d.get("retribuicao_golpes") and self.dano_recebido:
            n = d["retribuicao_golpes"]
            j.retrib_golpes, j.retrib_por_golpe = n, -(-self.dano_recebido // n)
        if d.get("roubar"):
            minhas = {t.id for t in j.tecnicas}
            alvo = [t for t in rival.tecnicas if t.id not in minhas]
            if alvo:
                roubada = max(alvo, key=valor_tecnica)
                if len(j.tecnicas) >= self.espacos:
                    j.tecnicas.remove(min(j.tecnicas, key=valor_tecnica))
                j.tecnicas.append(roubada)
        if d.get("travar_rival"):
            for t in rival.tecnicas:
                rival.recargas[t.id] = max(rival.recargas.get(t.id, 0), d["travar_rival"])
            self.intencao_rival = escolher_rival(self)
        if d.get("forma"):
            j.forma = d["forma"]
        if d.get("cura_total"):
            j.vida = j.vida_max
        j.escudos += d.get("escudos", 0)
        if d.get("evoluir"):  # Liberação Final: até o fim da luta
            for i, t in enumerate(j.tecnicas):
                self._antes_da_liberacao.setdefault(t.id, t)
                j.tecnicas[i] = evoluir(t)
        if d.get("instinto"):
            j.instinto = d["instinto"]
        if d.get("cura_frac"):
            j.vida = min(j.vida_max, j.vida + round(j.vida_max * d["cura_frac"]))
        j.percepcao_luta += d.get("percepcao", 0)
        j.bonus_dano += d.get("dano", 0)
        j.dano_mult *= d.get("dano_mult", 1.0)
        j.fera += d.get("fera", 0)
        j.intocavel += d.get("intocavel", 0)
        if d.get("golpe_imediato"):  # Dragão Negro: atravessa tudo, agora
            self._ferir(rival, d["golpe_imediato"])
        if d.get("retorno"):  # Retorno pela Morte: a vida do começo da luta
            j.vida = max(j.vida, min(j.vida_max, self.vida_inicial))
        if d.get("perde_vida_max"):  # Marca do Caçador: o preço fica na run
            j.base_vida_max = max(1, round(j.base_vida_max * (1 - d["perde_vida_max"])))
            j.aplicar_efeitos(j.efeitos)
        # Expansão
        if d.get("atordoar") and rival.vivo:
            rival.pular += d["atordoar"]
            self.intencao_rival = escolher_rival(self)
        if d.get("silenciar") and rival.vivo:
            rival.silencio += d["silenciar"]
            self.intencao_rival = escolher_rival(self)
        if d.get("renovar"):  # todas as suas técnicas prontas
            j.recargas.clear()
        if d.get("sangrar"):
            rival.sangue += d["sangrar"]
            rival.sangue_turnos = 3
        rival.marca += d.get("marca", 0)
        rival.exposto += d.get("expor", 0)
        rival.bonus_dano -= d.get("enfraquecer", 0)
        j.drenar_luta += d.get("drenar", 0.0)
        j.espelho += d.get("espelho", 0)
        j.regen_luta += d.get("regenerar", 0)
        j.absolutos += d.get("absolutos", 0)
        j.extras += d.get("acoes_extras", 0)
        j.santuario = max(j.santuario, d.get("santuario", 0))
        j.dano_mult_luta *= d.get("dano_mult_luta", 1.0)
        j.recebido_mult_luta *= d.get("recebido_mult", 1.0)
        j.recarga_menos_luta += d.get("recarga_menos", 0)
        if d.get("vida_max_run"):  # para sempre (ou o preço, se negativo)
            j.base_vida_max = max(1, j.base_vida_max + d["vida_max_run"])
            j.aplicar_efeitos(j.efeitos)
            if d["vida_max_run"] > 0:
                j.vida = min(j.vida_max, j.vida + d["vida_max_run"])
        if d.get("dano_run"):  # o que a luta ensinou fica: +dano pelo resto da run
            j.dano_run += d["dano_run"]
        if d.get("execucao") and rival.vivo and rival.vida <= rival.vida_max * d["execucao"]:
            self._ferir(rival, rival.vida)  # quem já estava caído não levanta
        if d.get("trocar_vida") and rival.vivo:  # as frações de vida trocam de dono
            fj, fr = j.vida / j.vida_max, rival.vida / rival.vida_max
            j.vida = max(1, round(fr * j.vida_max))
            rival.vida = max(1, round(fj * rival.vida_max))
        if d.get("bomba"):
            rival.bombas.append([d.get("bomba_turnos", 2), d["bomba"]])
        # preços (votos de luta)
        if d.get("perde_vida_frac"):
            j.vida = max(1, j.vida - round(j.vida * d["perde_vida_frac"]))
        if d.get("carma") and carma is not None:
            if d["carma"] > 0:
                carma.ganhar(d["carma"])
            else:
                carma.valor = max(0.0, carma.valor + d["carma"])
        if d.get("zera_carma") and carma is not None:
            carma.valor = 0.0
        if d.get("hesitar"):
            j.pular += d["hesitar"]
        j.sem_despertar = j.sem_despertar or d.get("sem_despertar", False)
        j.sem_basico_luta = j.sem_basico_luta or d.get("sem_basico", False)
        j.proibir_luta = j.proibir_luta | frozenset(d.get("proibir", ()))
        j.imperceptivel_luta = j.imperceptivel_luta or d.get("imperceptivel", False)
        j.sem_percepcao = j.sem_percepcao or d.get("sem_percepcao", False)
        j.percepcao_rival_luta += d.get("percepcao_rival", 0)
        if d.get("revelar"):  # a próxima técnica usada fica revelada
            j.revelar = d["revelar"]
        if d.get("selar_melhor"):  # sela a sua técnica mais forte até o fim da luta
            if j.tecnicas:
                melhor = max(j.tecnicas, key=valor_tecnica)
                j.recargas[melhor.id] = 99

    def encerrar(self) -> None:
        """Desfaz o que só valia nesta luta (a Liberação Final)."""
        if self._antes_da_liberacao:
            j = self.jogador
            j.tecnicas[:] = [self._antes_da_liberacao.get(t.id, t) for t in j.tecnicas]
            self._antes_da_liberacao = {}

    def _curar(self, lutador: Lutador, quanto: int) -> int:
        if lutador.efeitos.sem_cura or not lutador.vivo:
            return 0
        antes = lutador.vida
        cura = round(quanto * lutador.efeitos.cura_mult)
        lutador.vida = min(lutador.vida_max, lutador.vida + cura)
        return lutador.vida - antes

    def _ferir(self, lutador: Lutador, dano: int) -> int:
        feito = lutador.sofrer(dano)
        lutador.dor += feito
        if lutador is self.jogador:
            self.dano_recebido += feito
        return feito

    def _selar(self, alvo: Lutador, turnos: int) -> str:
        t = _selar_alvo(self, alvo)
        if t is None:
            return ""
        alvo.recargas[t.id] = max(alvo.recargas.get(t.id, 0), turnos)
        return t.id

    def percepcao_contra(self, alvo: Lutador) -> int:
        """Percepção do alvo contra quem o ataca (o Voto Exposto dá Percepção ao rival)."""
        if alvo.cego or alvo.cegueira or alvo.sem_percepcao:
            return 0
        extra = 0
        if alvo is self.rival:
            extra = self.jogador.efeitos.percepcao_rival + self.jogador.percepcao_rival_luta
        return max(0, alvo.percepcao + alvo.percepcao_luta + extra)

    def outro(self, lutador: Lutador) -> Lutador:
        return self.rival if lutador is self.jogador else self.jogador

    def ver_intencao(self) -> str | Tecnica | None:
        """O que o jogador enxerga da próxima ação do rival: nada, o tipo, ou a técnica."""
        j = self.jogador
        p, t = j.percepcao + j.percepcao_luta, self.intencao_rival
        if t is None or p <= 0 or j.cego or j.cegueira or j.sem_percepcao:
            return None
        return t.tipo if p == 1 else t

    def turno_rival(self) -> Acao:
        assert self.vez is self.rival
        tecnica = self.intencao_rival
        if tecnica is None or tecnica not in self.prontas(self.rival):
            tecnica = escolher_rival(self)
        return self.resolver(tecnica)

    def _inicio_do_turno(self, ator: Lutador) -> None:
        """O que acontece a quem age antes da ação: curas e preços por turno."""
        if ator.efeitos.regen and ator.vida < ator.vida_max * ator.efeitos.regen_ate:
            self._curar(ator, ator.efeitos.regen)  # Carne que Volta
        if ator.regen_luta:
            self._curar(ator, ator.regen_luta)
        if ator.efeitos.sangria:
            ator.sofrer(ator.efeitos.sangria)  # o preço dos Portões Abertos
        if ator.marca:
            ator.sofrer(ator.marca)  # Marca da Maldição
        if ator.eco:
            ator.sofrer(ator.eco)  # o preço de ter marcado alguém
        if ator.sangue_turnos:
            ator.sofrer(ator.sangue)
            ator.sangue_turnos -= 1
            if not ator.sangue_turnos:
                ator.sangue = 0
        if ator.bombas:
            restantes = []
            for turnos, dano in ator.bombas:
                if turnos <= 1:
                    self._ferir(ator, dano)  # a bomba plantada explode
                else:
                    restantes.append([turnos - 1, dano])
            ator.bombas = restantes
        if ator.efeitos.crescer:
            antes = int(ator.crescido + 1e-9)
            ator.crescido += ator.efeitos.crescer
            ator.bonus_dano += int(ator.crescido + 1e-9) - antes

    def _recarga(self, ator: Lutador, t: Tecnica) -> int:
        if t.recarga in (0, 99):
            return t.recarga
        menos = ator.efeitos.recarga_menos + ator.recarga_menos_luta
        return max(1, t.recarga - menos)

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

        self._inicio_do_turno(ator)
        if efetiva.custo_vida:
            ator.sofrer(efetiva.custo_vida)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        if efetiva.custo_vida_max:  # o preço que fica na run
            ator.base_vida_max = max(1, ator.base_vida_max - efetiva.custo_vida_max)
            ator.aplicar_efeitos(ator.efeitos)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        ator.bonus_dano += efetiva.fortalecer
        ator.bloqueio += round(efetiva.bloqueio * ator.efeitos.bloqueio_mult)
        ator.revide += efetiva.revide
        ator.escudos += efetiva.escudo
        alvo.marca += efetiva.marca
        ator.eco += efetiva.eco
        ator.instinto += efetiva.instinto
        ator.intocavel += efetiva.intocavel
        ator.fera += efetiva.fera
        ator.percepcao_luta += efetiva.foco
        ator.espelho += efetiva.espelho
        ator.regen_luta += efetiva.regenerar
        curou = self._curar(ator, efetiva.cura) if efetiva.cura else 0
        ativou_santuario = efetiva.santuario > 0
        if ativou_santuario:
            ator.santuario = efetiva.santuario
            ator.pular_pendente = efetiva.pular_depois
        if ator.revelar and t not in (self.basico, HESITAR) and not ator.revelada:
            ator.revelada, ator.revelada_bonus, ator.revelar = efetiva.id, ator.revelar, 0.0

        surpresa, reagiu, total = self.abertura or efetiva.sempre_surpresa, False, 0
        esquivas = escudados = sombra = instintos = 0
        despertou, critico = "", False
        basico = t is self.basico
        base = efetiva.dano + int(efetiva.dano_por_carma * ator.carma.valor if ator.carma else 0)
        base += _extra_da_dor(efetiva, ator)  # Esfera dos Mil
        if basico:
            base += ator.efeitos.basico_dano  # Corpo Perfeito
        if efetiva.consome_carma and ator.carma is not None:
            ator.carma.valor = 0.0  # a dor vira golpe: o Despertar que vinha se vai junto
        if base > 0:
            base += ator.acumulos.get(efetiva.id, 0)
            base += efetiva.combo * sum(1 for x in ator.tecnicas if ator.recargas.get(x.id, 0))
            base += min(TETO_GRAVIDADE, int(efetiva.gravidade * max(0, alvo.vida)))
            base += int(efetiva.desespero * max(0, ator.vida_max - ator.vida))
            if efetiva.variacao:
                base += self.rng.randint(0, efetiva.variacao)
            if efetiva.detonar:
                resto = alvo.marca + alvo.sangue * alvo.sangue_turnos
                base += efetiva.detonar * resto
                alvo.marca = alvo.sangue = alvo.sangue_turnos = 0
                ator.eco = 0  # sem Marca, sem o preço dela
        if efetiva.acumula:
            ator.acumulos[efetiva.id] = ator.acumulos.get(efetiva.id, 0) + efetiva.acumula
        if efetiva.dissipar:
            alvo.bloqueio = alvo.revide = alvo.escudos = alvo.espelho = 0
        if base > 0 and ator.vivo:
            perdida = 1 - max(0, ator.vida) / ator.vida_max
            fervor = round(ator.efeitos.furia * perdida)  # Sangue Fervente
            base += ator.bonus_dano + ator.efeitos.bonus_dano + fervor + ator.dano_extra
            base += ator.dano_run
            if ator.vida < ator.vida_max * 0.3:
                base += ator.efeitos.ultimo_suspiro
            if ator.vida >= ator.vida_max:
                base += ator.efeitos.vida_cheia
            if ator.retrib_golpes:  # Retribuição: a dor volta
                base += ator.retrib_por_golpe
                ator.retrib_golpes -= 1
            if ator.forma:  # Forma Desperta
                base *= 2
            base = max(0, base)
            mult = ator.dano_mult * ator.efeitos.dano_mult * ator.dano_mult_luta
            if t.copia_rival:
                mult *= t.copia_bonus
            if not basico:
                mult *= ator.efeitos.dano_tecnicas_mult  # Lâmina Adormecida
            if ator.revelada and efetiva.id == ator.revelada:
                mult *= 1 + ator.revelada_bonus  # Revelação
            if not ator.atacou and ator.efeitos.primeiro_golpe:
                mult *= 1 + ator.efeitos.primeiro_golpe
            fracao_alvo = max(0, alvo.vida) / alvo.vida_max
            if efetiva.executar and fracao_alvo < efetiva.executar:
                mult *= 2
            if ator.efeitos.executar and fracao_alvo < ator.efeitos.executar:
                mult *= 1.5
            if ator.efeitos.dano_marcado and (alvo.marca or alvo.sangue_turnos):
                mult *= 1 + ator.efeitos.dano_marcado
            base = round(base * mult)
            if efetiva.critico and self.rng.random() < efetiva.critico:
                base, critico = round(base * CRITICO), True  # Clarão Negro
            if alvo.chefe:
                base = round(base * ator.efeitos.dano_chefe_mult)  # Carrasco
            santuario = ator.santuario > 0 and not ativou_santuario
            if santuario:
                base = round(base * 1.5)
            absoluto = efetiva.absoluto or ator.absolutos > 0
            perigoso = efetiva.perigosa or surpresa
            oculto = (
                (ator.efeitos.imperceptivel and efetiva.perigosa)
                or santuario
                or ator.imperceptivel_luta
            )
            emboscada = surpresa and ator.efeitos.primeiro_sangue
            sangue_frio = surpresa and alvo.efeitos.sangue_frio
            sutileza = efetiva.sutileza + ator.efeitos.sutileza
            reagiu = (
                perigoso
                and not (oculto or emboscada)
                and (sangue_frio or self.percepcao_contra(alvo) >= sutileza)
            )
            if alvo.cegueira:
                alvo.cegueira -= 1

            def golpear(dano: int) -> int:
                nonlocal esquivas, escudados, despertou, instintos
                if alvo.intocavel:  # Vazio Infinito: o golpe para no ar
                    escudados += 1
                    return 0
                if alvo.exposto:
                    alvo.exposto -= 1
                    dano = round(dano * 1.5)
                dano = round(dano * alvo.efeitos.dano_recebido_mult * alvo.recebido_mult_luta)
                if not absoluto:
                    if alvo.espelho:  # o golpe volta a quem golpeou
                        alvo.espelho -= 1
                        escudados += 1
                        self._ferir(ator, dano)
                        return 0
                    if alvo.instinto and self.rng.random() < 0.6:
                        instintos += 1  # Instinto Puro: esquiva e devolve um Golpe
                        self._ferir(ator, self.basico.dano)
                        return 0
                    if alvo.efeitos.esquiva and self.rng.random() < alvo.efeitos.esquiva:
                        esquivas += 1  # Reflexo Treinado
                        return 0
                    if alvo.escudos:
                        alvo.escudos -= 1  # Pele de Cinzas
                        escudados += 1
                        return 0
                fura = efetiva.perfura or absoluto or (basico and ator.efeitos.basico_perfura)
                absorvido = 0 if fura else min(alvo.bloqueio, dano)
                alvo.bloqueio -= absorvido
                if alvo is self.jogador and dano - absorvido >= alvo.vida:
                    if self.pode_despertar():
                        despertou = self.despertar().id  # à beira da morte: o golpe é anulado
                        return 0
                    if self.pode_eclipse():
                        despertou = self.despertar(eclipse=True).id  # o Ovo do Eclipse
                        return 0
                feito = self._ferir(alvo, dano - absorvido)
                if alvo.revide and dano:
                    self._ferir(ator, alvo.revide)
                    alvo.revide = 0
                return feito

            por_golpe = base // 2 if reagiu else base
            if surpresa and not reagiu and not alvo.efeitos.sem_surpresa:
                por_golpe = round(por_golpe * (1 + self.bonus_surpresa))
            golpes = efetiva.golpes + (ator.efeitos.basico_golpes if basico else 0)
            golpes += 1 if ator.fera else 0  # Fera Interior
            for _ in range(golpes):
                total += golpear(por_golpe)
                if not alvo.vivo:
                    break
            if ator.efeitos.sombra and alvo.vivo and ator.vivo:
                sombra = golpear(round(por_golpe * ator.efeitos.sombra))  # Sombra Leal
                total += sombra
            if reagiu and alvo.vivo:
                self._ferir(ator, self.basico.dano)  # o contra-golpe de quem sentiu o perigo
            if alvo.instinto:
                alvo.instinto -= 1
            ator.atacou = True
            if ator.absolutos and absoluto and not efetiva.absoluto:
                ator.absolutos -= 1
            drenar = efetiva.drenar + ator.efeitos.drenar + ator.drenar_luta
            if drenar and total:
                curou += self._curar(ator, round(total * drenar))
            passivo = ator.efeitos.sangrar if total else 0
            if (efetiva.sangrar or passivo) and alvo.vivo:
                alvo.sangue += efetiva.sangrar
                alvo.sangue = max(alvo.sangue, passivo)  # o passivo renova, não empilha
                alvo.sangue_turnos = 3
        elif efetiva.sangrar and alvo.vivo:
            alvo.sangue += efetiva.sangrar
            alvo.sangue_turnos = 3

        selou, atordoou = "", False
        if efetiva.selar and alvo.vivo:
            selou = self._selar(alvo, efetiva.selar)
        if efetiva.atordoar and alvo.vivo:
            alvo.pular += efetiva.atordoar  # Lua Ilusória
            atordoou = True
        if alvo.vivo:
            alvo.bonus_dano -= efetiva.enfraquecer
            alvo.cegueira += efetiva.cegar
            alvo.exposto += efetiva.expor
            alvo.silencio += efetiva.silenciar
            alvo.desarme += efetiva.desarmar
            if efetiva.bomba:
                alvo.bombas.append([efetiva.bomba_turnos, efetiva.bomba])
        mudou_rival = selou or atordoou or efetiva.silenciar or efetiva.desarmar
        if mudou_rival and alvo is self.rival:
            self.intencao_rival = escolher_rival(self)  # o que ele anunciou não vem mais

        for tid in list(ator.recargas):
            if ator.recargas[tid] > 0:
                ator.recargas[tid] -= 1
        if t not in (self.basico, HESITAR) and t.recarga and not ator.forma:
            ator.recargas[t.id] = self._recarga(ator, t)  # na Forma Desperta, nada em recarga
        if efetiva.acelerar:
            for tid in list(ator.recargas):
                if tid != t.id and 0 < ator.recargas[tid] < 99:
                    ator.recargas[tid] = max(0, ator.recargas[tid] - efetiva.acelerar)
        if ator.forma:
            ator.forma -= 1
        if ator.fera:
            ator.fera -= 1
        if ator.silencio:
            ator.silencio -= 1
        if ator.desarme:
            ator.desarme -= 1
        if alvo.intocavel and t is not HESITAR:
            alvo.intocavel -= 1  # o turno do rival passou
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
        if t.livre:
            ator.extras += 1  # não gasta o turno

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
            despertou,
            critico=critico,
            curou=curou,
            selou=selou,
            atordoou=atordoou,
            instintos=instintos,
        )
        self.log.append(acao)
        self.abertura = False
        self.turnos += 1
        limite = self.jogador.efeitos.limite_turnos
        if limite and self.turnos >= 2 * limite and self.rival.vivo and self.jogador.vivo:
            self.estourou_prazo = True  # voto Prazo
        self._depois_da_acao(acao, ator, t)
        if not extra:  # Instante Suspenso: a vez continua com quem agiu
            self.vez = alvo
        if ator is self.rival and not self.acabou:
            # Anuncia ao fim do próprio turno, para o jogador ver antes de escolher. A técnica
            # anunciada continua pronta até lá: recargas do rival só descem no turno dele.
            self.intencao_rival = escolher_rival(self)
        return acao


def _extra_da_dor(t: Tecnica, ator: Lutador) -> int:
    extra = int(t.dano_por_dor * ator.dor)
    return min(extra, t.teto_dor) if t.teto_dor else extra


def _selar_alvo(luta: Luta, alvo: Lutador) -> Tecnica | None:
    """O que a Corrente prende: a ação anunciada do rival, ou a melhor técnica pronta."""
    if alvo is luta.rival:
        t = luta.intencao_rival
        return t if t is not None and t in alvo.tecnicas else None
    prontas = [t for t in alvo.tecnicas if alvo.pronta(t)]
    return max(prontas, key=valor_tecnica) if prontas else None


def _valor_ofensivo(luta: Luta, ator: Lutador, t: Tecnica) -> float:
    if t.copia_rival:
        roubada = luta.ultima_tecnica(luta.outro(ator))
        return _valor_ofensivo(luta, ator, roubada) if roubada else 0.0
    carma = ator.carma.valor if ator.carma else 0.0
    alvo = luta.outro(ator)
    base = t.dano + t.dano_por_carma * carma + _extra_da_dor(t, ator)
    if base > 0:
        base += ator.acumulos.get(t.id, 0) + t.variacao / 2
        base += t.combo * sum(1 for x in ator.tecnicas if ator.recargas.get(x.id, 0))
        base += min(TETO_GRAVIDADE, t.gravidade * max(0, alvo.vida))
        base += t.desespero * max(0, ator.vida_max - ator.vida)
        base += t.detonar * (alvo.marca + alvo.sangue * alvo.sangue_turnos)
        if t.executar and alvo.vida < alvo.vida_max * t.executar:
            base *= 2
    extra = ator.bonus_dano + ator.efeitos.bonus_dano
    if t is luta.basico:
        extra += ator.efeitos.basico_dano
        golpes = t.golpes + ator.efeitos.basico_golpes
    else:
        golpes = t.golpes
    valor = (base + extra) * golpes if base > 0 else 0.0
    return valor * (1 + t.critico * (CRITICO - 1))


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
        cura=cresce(t.cura),
        sangrar=cresce(t.sangrar),
        bomba=cresce(t.bomba),
        regenerar=cresce(t.regenerar),
        combo=cresce(t.combo),
        acumula=cresce(t.acumula),
        detonar=cresce(t.detonar),
        enfraquecer=cresce(t.enfraquecer),
        recarga=recarga,
    )


def valor_tecnica(t: Tecnica) -> float:
    """Valor bruto de uma técnica, para escolher o que um Contrato sacrifica."""
    valor = t.dano * t.golpes + t.bloqueio + t.revide + 3 * (t.marca + t.fortalecer)
    valor += t.cura + 6 * t.atordoar + 4 * t.selar + 8 * t.escudo
    valor += 3 * t.sangrar + t.bomba + 3 * t.regenerar + 5 * (t.silenciar + t.espelho)
    return valor + 4 * (t.instinto + t.intocavel + t.fera + t.enfraquecer)


def _vale_o_preco(luta: Luta, j: Lutador, t: Tecnica) -> bool:
    """Poderes que custam caro só valem na hora certa.

    Carma e técnica consumidos: para fechar a luta ou num chefe. Marca: só em luta que
    ainda vai durar (rival com vida) e sem empilhar além de duas — o preço também se soma.
    """
    if t.marca:
        return luta.rival.vida >= 12 and luta.rival.marca < 2 * t.marca
    if t.atordoar:
        return luta.rival.vida >= 12 and not luta.rival.pular
    if t.cura and not t.dano:
        return j.vida < j.vida_max * 0.6
    if t.santuario:
        return luta.rival.vida >= 20 and j.santuario == 0
    if t.turno_extra:  # sem preço, sempre; com preço em Carma, só se sobra Carma
        return not t.custo_carma or (j.carma is not None and j.carma.valor >= t.custo_carma + 30)
    if t.custo_vida_max:  # o preço fica na run: contra chefe, ou para se salvar
        mata = _valor_ofensivo(luta, j, t) >= luta.rival.vida
        return luta.rival.chefe or (mata and j.vida < j.vida_max * 0.35)
    if t.fera and j.fera or t.fortalecer and t.recarga == 99 and j.bonus_dano > 0:
        return False  # o efeito ainda está de pé
    if t.custo_vida and not t.dano:  # preparo pago em vida: só em luta que vai durar
        return luta.rival.vida >= 25 and j.vida > 3 * t.custo_vida
    if t.custo_vida >= 6:  # golpe caro: contra chefe, ou se fecha a luta
        mata = _valor_ofensivo(luta, j, t) >= luta.rival.vida
        return j.vida > 2 * t.custo_vida and (luta.rival.chefe or mata and luta.rival.vida >= 20)
    if t.custo_carma:
        return j.carma is not None and j.carma.valor >= t.custo_carma + 30
    if t.detonar and not t.dano:
        return luta.rival.marca + luta.rival.sangue_turnos > 0
    if t.silenciar or t.desarmar or t.bomba:
        return luta.rival.vida >= 12
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


def jurar_luta_auto(luta: Luta) -> bool:
    """O piloto automático diante do voto de luta: jura quando a dica do voto manda."""
    if not luta.pode_jurar_luta():
        return False
    j, rival, v = luta.jogador, luta.rival, luta.voto_luta
    if v.piloto == "inicio":
        return rival.vida >= 15
    if v.piloto == "chefe":
        return rival.chefe
    if v.piloto == "vida_alta":
        return j.vida >= j.vida_max * 0.6 and rival.vida >= 20
    if v.piloto == "seguro":  # promete não ser ferido quando o rival anuncia algo sem dano
        vista = luta.ver_intencao()
        return vista == "defesa" or (isinstance(vista, Tecnica) and vista.dano == 0)
    # "fechar": a promessa de vencer em N turnos, quando dá para cumprir
    turnos = (v.condicao or {}).get("vencer_em", 2)
    melhor = max(_valor_ofensivo(luta, j, t) for t in luta.prontas(j))
    return rival.vida <= melhor * turnos * 0.8


def escolher_jogador_auto(luta: Luta) -> Tecnica:
    """Piloto automático do jogador (simulação): defende o que vê chegando, senão bate forte."""
    j = luta.jogador
    prontas = [t for t in luta.prontas(j) if _vale_o_preco(luta, j, t)] or luta.prontas(j)
    p = luta.promessa
    if p is not None and p.condicao == "so_golpe" and luta.basico in luta.prontas(j):
        return luta.basico  # cumpre a promessa
    if p is not None and p.condicao == "sem_defesa":
        prontas = [t for t in prontas if t.tipo != "defesa"] or prontas
    vista = luta.ver_intencao()
    selos = [t for t in prontas if t.selar]
    if isinstance(vista, Tecnica) and vista is not luta.basico and selos:
        if _valor_ofensivo(luta, luta.rival, vista) >= 8:
            return selos[0]  # prende o golpe que vem
    curas = [t for t in prontas if t.cura and not t.dano]
    if curas and j.vida < j.vida_max * 0.45:
        return max(curas, key=lambda t: t.cura)
    defesas = [t for t in prontas if t.tipo == "defesa" and not t.cura]
    if isinstance(vista, Tecnica) and vista.perigosa and defesas:
        return max(defesas, key=lambda t: t.bloqueio + t.revide)
    if vista == "ataque" and defesas and j.vida < j.vida_max * 0.35:
        return defesas[0]
    melhor = max(prontas, key=lambda t: _valor_ofensivo(luta, j, t))
    preparos = [t for t in prontas if t.tipo == "maldita" and _valor_ofensivo(luta, j, t) == 0]
    # preparar custa um turno: só vale em luta que ainda dura uns golpes
    livres = [t for t in preparos if t.livre]
    if livres:
        return livres[0]
    if preparos and luta.rival.vida > 2 * _valor_ofensivo(luta, j, melhor):
        return preparos[0]
    return melhor


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

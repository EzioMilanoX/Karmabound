"""Combate por recarga: você contra 1 a 3 rivais. Regras puras, sem tela.

- Turnos alternados; quem tem mais Velocidade começa (empate: sorteio). Contra
  um bando, o lado dos rivais age em sequência (o mais rápido primeiro) e você
  escolhe em quem bater (`Luta.rival` é o seu alvo; `mirar` troca).
- Cada rival de um bando tem um papel (`Lutador.papel`): a lâmina bate, o
  guardião protege (`Tecnica.proteger`), o curandeiro cura (`curar_aliado`), o
  xamã amaldiçoa e o comandante inspira (`inspirar`).
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
- Quebra de guarda: todo rival tem um medidor (`Lutador.guarda`) que os seus golpes
  enchem; ao passar de `limiar_guarda`, ele perde o próximo turno e sofre +25%.
- Chefes têm a mecânica da assinatura (`Lutador.mecanica`); elites têm afixos
  (`Lutador.afixos`); o jogador pode ter um aliado, que age no começo do turno dele.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace

from karmabound.carma import Carma
from karmabound.efeitos import NEUTRO, Efeitos
from karmabound.rodas import Fatia
from karmabound.votos_luta import Promessa


@dataclass(frozen=True)
class Modo:
    """Uma transformação (Modo Sábio, Bankai, Gear, Super Saiyajin...): por `turnos` turnos
    seus você fica mais forte, e quando ela acaba vem o preço."""

    turnos: int
    nome: str = ""  # o nome na tela ("Modo Sábio")
    dano_mult: float = 1.0
    dano: int = 0  # +dano em todo golpe
    golpes: int = 0  # golpes a mais em todo ataque
    percepcao: int = 0
    sutileza: int = 0
    regen: int = 0  # cura a cada turno seu
    sangria: int = 0  # vida perdida a cada turno seu (o corpo não aguenta)
    esquiva: float = 0.0
    bloqueio: int = 0  # bloqueio renovado a cada turno seu
    recebido_mult: float = 1.0  # todo dano que você sofre
    drenar: float = 0.0
    inabalavel: bool = False  # não cai abaixo de 1 enquanto dura: o dano fica adiado
    absoluto: bool = False  # todo golpe atravessa bloqueio, escudo e esquiva
    sem_recarga: bool = False  # nada entra em recarga enquanto dura
    # o preço, quando acaba
    exausto: int = 0  # turnos perdidos
    travar: int = 0  # todas as suas técnicas em recarga por N turnos (o cérebro queimado)
    perde_vida_frac: float = 0.0  # fração da vida atual
    vida_max_run: int = 0  # −N de vida máxima pelo resto da run
    adiado: bool = False  # sofre todo o dano adiado (Armadura Berserker)

    @classmethod
    def de_dict(cls, d: dict) -> Modo:
        return cls(**d)


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
    # Leva 3: o que os poderes fazem nos animes
    chama_eterna: int = 0  # Amaterasu: o alvo queima N por turno até o fim da luta, +1 a cada turno
    veneno: int = 0  # doses: o alvo sofre as doses a cada turno dele; elas caem 1 por turno
    congelar: int = 0  # o alvo perde N turnos; o próximo golpe nele causa ×2 e quebra o gelo
    clones: int = 0  # cada clone ataca junto (40% do golpe) e absorve um golpe recebido
    invocar: int = 0  # uma invocação fere o alvo em N a cada turno seu, por `invocar_turnos`
    invocar_turnos: int = 3
    roda_dharma: bool = False  # a Roda do Dharma do jogador: você se adapta até o fim da luta
    vinculo: int = 0  # por N turnos seus, toda dor que você sofre o alvo sofre junto (Hidan)
    purificar: bool = False  # tira de você sangramento, veneno, Marca, cegueira e bloqueios
    custo_percepcao: int = 0  # preço: −N de Percepção pelo resto da run, a cada uso (Mangekyō)
    modo: Modo | None = None  # transformação
    # Bandos: o que um rival faz pelos aliados (e o que atinge todos de uma vez)
    proteger: int = 0  # bloqueio para o aliado mais ferido (o Guardião)
    curar_aliado: int = 0  # cura o aliado mais ferido (o Curandeiro)
    inspirar: int = 0  # +dano em todos os aliados, até o fim da luta (o Comandante)
    area: float = 0.0  # os outros rivais sofrem esta fração do dano que o alvo sofreu
    nivel: int = 1  # duplicatas evoluem a técnica

    def __post_init__(self) -> None:
        if isinstance(self.modo, dict):  # dos dados: o modo chega como dicionário
            object.__setattr__(self, "modo", Modo.de_dict(self.modo))

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
    # Leva 3 (também só da luta)
    chama: int = 0  # a chama que não apaga: queima isto por turno e cresce 1
    veneno: int = 0  # doses de veneno: fere isto por turno e cai 1
    congelado: bool = False  # o próximo golpe recebido causa ×2 e quebra o gelo
    clones: int = 0
    invocacoes: list[list] = field(default_factory=list)  # [turnos, dano, de onde veio]
    vinculo: int = 0  # turnos seus em que a sua dor passa para `elo`
    elo: Lutador | None = field(default=None, repr=False)
    modo: Modo | None = None  # a transformação ativa
    modo_id: str = ""
    modo_turnos: int = 0
    adiado: int = 0  # o dano que a Armadura segurou
    incinerado: bool = False  # a chama negra terminou o serviço
    segunda_forma: bool = False  # o chefe já revelou a segunda forma
    # quem é este rival (a tela desenha por aqui; o combate só olha o papel)
    papel: str = ""  # lamina | guardiao | curandeiro | xama | comandante ("" = sozinho)
    estilo: str = ""  # a figura (espadachim, monge...); vazio: a tela escolhe
    titulo: str = ""  # o nome na tela ("Guardião", "Nêmesis · Ronin do Trovão")
    elite: bool = False
    nemesis: bool = False
    # Quebra de guarda (todo rival; só da luta: o rival nasce a cada luta)
    guarda: int = 0  # o medidor: dano + GUARDA_POR_GOLPE por golpe que fere; ver `limiar_guarda`
    quebrado: bool = False  # guarda quebrada: perde o turno e sofre +25% até agir de novo
    # Chefe com mecânica própria (`data/chefes.json`, `mecanicas`)
    mecanica: str = ""  # adaptar | ilusao | petalas | armadura | repulsao | intangivel | ...
    assinatura: str = ""  # o id da técnica-assinatura do chefe
    turnos_luta: int = 0  # turnos próprios nesta luta (sem contar as ações encadeadas)
    adaptacao: dict[str, int] = field(default_factory=dict)  # Mahoraga: usos de cada técnica sua
    carga: int = 0  # Leigan: cargas do Disparo (+CARGA_BONUS cada; zera ao disparar)
    contrato: bool = False  # Makima: o próximo golpe que a feriria vai para outro lugar
    preco: bool = False  # Mugetsu: a Lua Sem Fim já foi usada (o dano dele caiu à metade)
    # Afixos de elite (`data/caminho.json`, `afixos`): os ids, e o que o combate lê deles
    afixos: tuple[str, ...] = ()
    blindagem: int = 0  # Blindado: bloqueio no início e a cada BLINDADO_CADA turnos dele
    marca_ao_ferir: int = 0  # Amaldiçoado: quem ele fere fica com esta Marca (não soma)
    gelo: float = 0.0  # Gélido: chance de congelar quem ele fere
    veloz: int = 0  # Veloz: a cada N turnos dele, age duas vezes seguidas (0 = não)
    # Leva 5: o vilão por trás do rival (a tela desenha e fala por aqui)
    vilao: str = ""  # o id em data/viloes.json ("" = rival anônimo)
    cor: str = ""  # o tom da figura
    guarda_mult: float = 1.0  # regra do Arco: o limiar da quebra de guarda ×
    zona: int = 0  # Kokusens seguidos (a faixa do próximo é maior); erro ou dano zera
    roda_dharma: bool = False  # o General da Roda do seu lado: os golpes repetidos falham
    # Leva 5: as mecânicas dos chefes finais (só da luta: o rival nasce a cada luta)
    roubos: int = 0  # O Roubo: técnicas suas que ele já tomou nesta luta
    marcha: int = 0  # A Marcha: o dano absoluto que você sofre a cada turno dele
    renasceu: bool = False  # O Rei Renascido: já voltou da morte nesta luta
    dominio: int = 0  # O Domínio: turnos dele que ainda faltam
    contagem: int = 0  # Cinco Minutos: turnos dele até o planeta explodir
    sonho: int = 0  # O Sonho Eterno: turnos até a lua cair
    paradas: int = 0  # O Mundo Para: vezes que ele já parou o tempo nesta luta
    parado: int = 0  # ações dele que ainda acontecem com o tempo parado
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
        self.roda_dharma, self.adaptacao = False, {}  # a roda recomeça a cada luta
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
        self.chama = self.veneno = self.vinculo = self.modo_turnos = self.adiado = 0
        self.congelado, self.elo, self.modo, self.modo_id = False, None, None, ""
        self.incinerado = False
        self.clones = self.efeitos.clones_inicio
        inicio = self.efeitos.invocar_inicio
        self.invocacoes = [[3, inicio, "invocacao_inicio"]] if inicio else []
        self.escudos = self.efeitos.escudo_inicial
        self.bloqueio = self.efeitos.bloqueio_inicio
        if self.efeitos.cura_inicio and not self.efeitos.sem_cura:
            cura = round(self.efeitos.cura_inicio * self.efeitos.cura_mult)
            self.vida = min(self.vida_max, self.vida + cura)  # Bandagem

    def pronta(self, t: Tecnica) -> bool:
        return self.recargas.get(t.id, 0) == 0

    def purificar(self) -> None:
        """Tira sangramento, veneno, Marca, cegueira, selos e bombas. A chama negra fica."""
        self.sangue = self.sangue_turnos = self.veneno = self.marca = 0
        self.cegueira = self.exposto = self.silencio = self.desarme = 0
        self.bombas, self.congelado = [], False
        self.bonus_dano = max(0, self.bonus_dano)  # o que enfraquecia também sai

    def entrar_no_modo(self, t: Tecnica) -> None:
        self.modo, self.modo_id = t.modo, t.id
        self.modo_turnos = t.modo.turnos + self.efeitos.modo_extra

    def sair_do_modo(self) -> None:
        """A transformação acaba: o preço vem agora."""
        m = self.modo
        self.modo, self.modo_id, self.modo_turnos = None, "", 0
        if m is None:
            return
        self.pular += m.exausto
        if m.travar:
            for t in self.tecnicas:
                self.recargas[t.id] = max(self.recargas.get(t.id, 0), m.travar)
        if m.perde_vida_frac:
            self.vida = max(1, self.vida - round(self.vida * m.perde_vida_frac))
        if m.vida_max_run:
            self.base_vida_max = max(1, self.base_vida_max - m.vida_max_run)
            self.aplicar_efeitos(self.efeitos)
        if m.adiado and self.adiado:
            adiado, self.adiado = self.adiado, 0
            self.sofrer(adiado)  # a Armadura se abre: tudo o que ela segurou

    def sofrer(self, dano: int, ecoa: bool = True) -> int:
        dano = max(0, min(dano, self.vida))
        if self.modo is not None and self.modo.inabalavel and dano >= self.vida:
            self.adiado += dano - (self.vida - 1)  # a Armadura segura: o corpo cobra depois
            dano = self.vida - 1
        if ecoa and dano and self.vinculo and self.elo is not None and self.elo.vivo:
            self.elo.sofrer(dano, ecoa=False)  # o ritual: a dor passa para quem está ligado
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
# Cada ferida que dura tem o seu jeito além do dano:
CURA_SANGRANDO = 0.5  # sangramento e queimadura: a ferida aberta não fecha, a cura cai à metade
FRAQUEZA_POR_DOSE = 0.05  # veneno: o corpo amolece, -5% de dano causado por dose...
FRAQUEZA_MAXIMA = 0.5  # ...até -50%
INCINERAR = 2  # chama negra: com a vida em até 2x a chama, o que sobra vira cinza
RECARGA_AMALDICOADA = 1  # Marca: a maldição sela, cada técnica demora +1 turno a voltar
# Chefes não caem de um golpe só, e mudam de forma na metade:
MAX_INVOCACOES = 3  # em campo ao mesmo tempo: a quarta manda embora a mais antiga
MAX_CLONES = 5
POSTURA_CHEFE = 0.3  # uma ação tira no máximo 30% da vida do chefe (feridas que duram, não)
SEGUNDA_FORMA = 0.5  # com a vida na metade, o chefe revela a segunda forma...
FURIA_CHEFE = 1.3  # ...+30% de dano e todas as técnicas prontas de novo
# Quebra de guarda: pressão concentrada derruba a defesa de qualquer rival
GUARDA_LIMIAR = 0.5  # o medidor quebra ao chegar a 50% da vida máxima do rival...
GUARDA_LIMIAR_CHEFE = 0.7  # ...70% num chefe (e a quebra do chefe não fura a postura)
GUARDA_POR_GOLPE = 2  # cada golpe que fere soma o dano e mais isto: golpes múltiplos quebram mais
GUARDA_ESVAI = 0.15  # a cada turno do rival, o medidor esvazia 15% da vida máxima dele
GUARDA_QUEBRADA = 1.25  # guarda quebrada: +25% de dano recebido até ele agir de novo
# Mecânicas dos chefes (uma por técnica-assinatura; nome e texto em data/chefes.json)
ADAPTAR = (1.0, 0.5, 0.0)  # Mahoraga: 1º uso de uma técnica sua inteiro, 2º metade, 3º nada
ADAPTAR_REVIDE = 8  # o chefe que se adaptou a um golpe devolve o próximo com isto
ILUSAO = 0.5  # Aizen: chance de o anúncio ser uma isca (ele age com o que decidiu de verdade)
INTANGIVEL = 0.25  # Kamui: chance de um ataque seu atravessar (absoluto não; feridas, não)
REPULSAO_CADA = 3  # Pain: a cada 3 turnos dele, empurra: clones, invocações e bloqueio seus
ARMADURA_CADA = 2  # Susanoo: bloqueio renovado no 1º turno dele e a cada 2...
ARMADURA_FRAC = 0.12  # ...de 12% da vida máxima dele
PRECO = 0.5  # Mugetsu: depois da Lua Sem Fim, o dano dele cai à metade até o fim
REGENERA = 0.04  # Kokushibo: cura 4% da vida por turno dele, se não sangra nem queima
CONTRATO_CADA = 4  # Makima: o contrato se renova a cada 4 turnos dela
# O Giro do Dono (o Dono da Roda): as fatias e o que cada uma faz enquanto vale
# As mecânicas dos chefes finais (Leva 5; textos em data/chefes.json, `mecanicas`)
ESCURIDAO_RECEBE = 1.2  # a Escuridão: ele sofre +20% de tudo
ESCURIDAO_TRAVA = 2  # o Vórtice que fere: suas técnicas Malditas, Divinas e formas em recarga 2
ROUBOS_MAX = 2  # o Roubo: técnicas suas que ele toma por luta
MARCHA_MAX = 5  # a Marcha: o dano por turno dele para de crescer aqui
DOMINIO_TURNOS, DOMINIO_CORTE, DOMINIO_FIM = 3, 4, 0.15  # o Domínio: duração, corte, o último
CINCO_MINUTOS, CINCO_MINUTOS_DANO, CINCO_MINUTOS_PRECO = 5, 0.4, 0.1  # turnos, você, ele
RENASCER_VIDA, RENASCER_DANO, RENASCER_VENENO = 0.4, 3, 2  # o Rei Renascido
SONHO_TURNOS, SONHO_SONO = 2, 2  # o Sonho Eterno: turnos até a lua cair, turnos que você dorme
AMANHECER_TURNO, AMANHECER_FRAC = 6, 0.05  # o Amanhecer: quando o sol nasce, cura e queimadura
MUNDO_PARADO = (2, 3)  # O Mundo Para: ações dele na 1ª parada e da 2ª em diante
SUTILEZA_TEMPO_PARADO = 99
LUTA_LONGA, LUTA_LONGA_PASSO = 60, 10  # depois de 60 ações: sem cura, e um desgaste que cresce
# O Kokusen (o Clarão Negro de verdade): apertar no instante certo da barra do golpe
KOKUSEN_MULT = 1.75  # o dano do golpe perfeito
ZONA_MAX = 3  # "na zona": cada Kokusen seguido alarga a faixa do próximo, até aqui
ENFRAQUECER_MAX = 3  # o quanto o enfraquecer tira, no total, de cada golpe (o Golpe causa 4)
GIRO_FATIAS = ("sangue", "ferrugem", "divida", "juizo")
GIRO_CADA, GIRO_CADA_FURIA = 3, 2  # gira a cada N turnos dele (2 na segunda forma)
GIRO_CARMA = 10  # cada giro te dá Carma: é o erro dele
GIRO_SANGUE = 3  # Sangue: os dois causam +3
GIRO_DIVIDA = 0.06  # Dívida: ele cura 6% da vida máxima por turno (sangrando ou queimando, não)
GIRO_JUIZO = 1.25  # Juízo: os seus golpes nele causam +25%
CARGA_MAX = 2  # Leigan: cada turno dele sem disparar carrega o Disparo, até 2 cargas...
CARGA_BONUS = 0.35  # ...+35% por carga; atordoar, selar, silenciar ou quebrar a guarda descarrega
# Afixos de elite (os números de cada um estão em data/caminho.json)
BLINDADO_CADA = 3

# Sem nenhuma técnica permitida pronta (ex.: voto Mãos Atadas), o lutador hesita.
HESITAR = Tecnica("hesitar", "Hesitar", "defesa")


def enfraquecer(alvo: Lutador, n: int) -> None:
    """−N em todo golpe de `alvo` pelo resto da luta, até ENFRAQUECER_MAX no total.

    Sem teto, dois lutadores que se enfraquecem de volta chegam a 0 de dano e a luta
    não acaba nunca."""
    if n > 0:
        alvo.bonus_dano = max(alvo.bonus_dano - n, min(alvo.bonus_dano, -ENFRAQUECER_MAX))


def limiar_guarda(r: Lutador) -> int:
    """Quanto o medidor de guarda de `r` aguenta antes de quebrar."""
    limiar = GUARDA_LIMIAR_CHEFE if r.chefe else GUARDA_LIMIAR
    return max(1, round(r.vida_max * limiar * r.guarda_mult))


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
    incinerou: bool = False  # a chama negra reduziu quem agia a cinzas
    segunda_forma: bool = False  # nesta ação o chefe revelou a segunda forma
    # para a tela: quem sofreu e o que aconteceu ao redor
    alvo: str = ""  # o nome de quem a ação mirou
    invocadas: tuple = ()  # (de onde veio, dano) de cada invocação que atacou no começo do turno
    respingo: tuple = ()  # (nome, dano) dos outros rivais que a área pegou
    protegido: str = ""  # quem o Guardião protegeu
    curado: str = ""  # quem o Curandeiro curou (e `curou` diz quanto)
    quebrou: str = ""  # o nome do rival que teve a guarda quebrada nesta ação
    mecanica: str = ""  # a mecânica de chefe que agiu nesta ação (ver data/chefes.json)
    iludiu: bool = False  # Aizen: a ação anunciada era mentira
    aliado: tuple = ()  # (id do aliado, efeito, valor) do que o seu aliado fez neste turno


class Luta:
    def __init__(
        self,
        jogador: Lutador,
        rival: Lutador | list[Lutador],
        basico: Tecnica,
        rng: random.Random,
        bonus_surpresa: float = 0.5,
        ao_despertar=None,
        espacos: int = 4,
        ao_eclipse=None,
        voto_luta=None,
        aliado=None,
        aliado_nivel: int = 1,
    ) -> None:
        """`ao_despertar()`: gira a Roda do Despertar e devolve a fatia (quem monta a luta
        cuida dos contadores e do giro Divino depois). Sem ela, não há Despertar.
        `ao_eclipse()`: cobra o preço do Ovo do Eclipse (o Dom).
        `rival`: um rival, ou o bando (até 3). `self.rival` é o alvo do jogador; no
        turno de um rival do bando, é ele (o combate inteiro fala com `self.rival`).
        `aliado`: o companheiro do jogador (`aliados.Aliado`), no nível `aliado_nivel`; age
        no começo de cada turno seu e nunca é alvo dos rivais."""
        rivais = list(rival) if isinstance(rival, (list, tuple)) else [rival]
        if not 1 <= len(rivais) <= 3:
            raise ValueError("uma luta tem de 1 a 3 rivais")
        self.jogador, self.rivais, self.rival = jogador, rivais, rivais[0]
        # o lado dos rivais age em sequência: o mais rápido primeiro
        self.ordem_rivais = sorted(rivais, key=lambda r: -r.velocidade)
        self.intencoes: dict[int, Tecnica | None] = {}
        self.ao_despertar = ao_despertar
        self.ao_eclipse = ao_eclipse
        self._antes_da_liberacao: dict[str, Tecnica] = {}  # técnicas antes do Bankai
        for lutador in (jogador, *rivais):
            for t in lutador.tecnicas:
                if t.inicia_em_recarga:
                    lutador.recargas[t.id] = max(lutador.recargas.get(t.id, 0), t.inicia_em_recarga)
        self.espacos = espacos  # para o Tomar o Destino saber se precisa trocar uma técnica
        self._invocadas: list[tuple[str, int]] = []
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
        rapido = self.ordem_rivais[0]
        if jogador.efeitos.primeiro_sangue:
            self.vez = jogador
        elif jogador.velocidade != rapido.velocidade:
            self.vez = jogador if jogador.velocidade > rapido.velocidade else rapido
        else:
            self.vez = rng.choice((jogador, rapido))
        self.abertura = True
        self.turnos = 0
        self.rodadas = 0  # voltas completas (o Prazo de um bando conta por aqui)
        self.log: list[Acao] = []
        self.forma_revelada = False  # um chefe revelou a segunda forma (zera a cada ação)
        self.aliado, self.aliado_nivel = aliado, aliado_nivel
        self._aliado_turnos = 0
        self._iludiu = False  # o rival que age agora mentiu no anúncio (Aizen)
        self._verdade: dict[int, Tecnica] = {}  # Aizen: o que ele vai fazer, atrás da isca
        self._mecanica = ""  # a mecânica de chefe que agiu na ação em curso
        self._kokusen = False  # a ação em curso é um Kokusen
        self.roda_dono = ""  # o Giro do Dono: a fatia que vale agora (GIRO_FATIAS)
        for r in rivais:
            r.contrato = r.mecanica == "contrato"  # Makima chega com o contrato firmado
        # Cada rival já chega anunciando: se ele começa, é a emboscada; se não, a resposta.
        for r in self.ordem_rivais:
            with self.foco(r):
                self.intencao_rival = escolher_rival(self)

    # ------------------------------------------------------------- o bando

    @property
    def intencao_rival(self) -> Tecnica | None:
        """A ação anunciada pelo rival em foco (o alvo, ou quem age agora)."""
        return self.intencoes.get(id(self.rival))

    @intencao_rival.setter
    def intencao_rival(self, t: Tecnica | None) -> None:
        r = self.rival
        self._verdade.pop(id(r), None)
        if t is not None and t is not HESITAR and r.mecanica == "ilusao":
            iscas = [x for x in self.prontas(r) if x != t and x is not HESITAR]
            if iscas and self.rng.random() < ILUSAO:  # Kyoka Suigetsu: você vê a isca
                self._verdade[id(r)], t = t, self.rng.choice(iscas)
        self.intencoes[id(r)] = t

    def intencao_de(self, r: Lutador) -> Tecnica | None:
        return self.intencoes.get(id(r))

    @property
    def vivos(self) -> list[Lutador]:
        """Os rivais ainda de pé."""
        return [r for r in self.rivais if r.vivo]

    def foco(self, r: Lutador):
        """`with luta.foco(r)`: o combate passa a falar com `r` e depois volta ao alvo."""
        luta = self

        class _Foco:
            def __enter__(self_):
                self_.antes = luta.rival
                luta.rival = r

            def __exit__(self_, *_):
                luta.rival = self_.antes

        return _Foco()

    def mirar(self, r: Lutador) -> None:
        """O jogador troca de alvo (só entre os rivais de pé)."""
        if r not in self.rivais or not r.vivo:
            raise ValueError("só dá para mirar num rival de pé")
        self.rival = r

    def aliados(self, lutador: Lutador) -> list[Lutador]:
        """Quem luta do lado de `lutador` (ele incluso), de pé."""
        if lutador is self.jogador:
            return [self.jogador]
        return self.vivos

    def _mais_ferido(self, lutador: Lutador) -> Lutador:
        aliados = self.aliados(lutador) or [lutador]
        return min(aliados, key=lambda a: a.vida / a.vida_max)

    def _reajustar_alvo(self) -> None:
        """O alvo caiu: a mira passa para o próximo rival de pé."""
        if not self.rival.vivo and self.vivos:
            self.rival = self.vivos[0]

    def _depois_de(self, ator: Lutador) -> Lutador:
        """Quem age depois de `ator`: você, e então cada rival de pé, do mais rápido."""
        vivos = [r for r in self.ordem_rivais if r.vivo]
        if ator is self.jogador:
            return vivos[0] if vivos else self.jogador
        seguintes = vivos[vivos.index(ator) + 1 :] if ator in vivos else []
        if not seguintes and ator not in vivos:  # caiu no próprio turno: o próximo depois dele
            i = self.ordem_rivais.index(ator)
            seguintes = [r for r in self.ordem_rivais[i + 1 :] if r.vivo]
        return seguintes[0] if seguintes else self.jogador

    @property
    def acabou(self) -> bool:
        return self.estourou_prazo or not (self.jogador.vivo and any(r.vivo for r in self.rivais))

    @property
    def vencedor(self) -> Lutador | None:
        if not self.acabou:
            return None
        if self.estourou_prazo or not self.jogador.vivo:
            return self.rival
        return self.jogador

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
        if not self.vivos:
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
        if d.get("travar_rival") or d.get("atordoar") or d.get("silenciar"):
            rival.carga = 0  # o disparo que carregava se perde
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
        # Leva 3
        if d.get("purificar"):
            j.purificar()
        if rival.vivo:
            rival.chama += d.get("chama", 0)
            rival.veneno += d.get("veneno", 0)
        j.clones = min(MAX_CLONES, j.clones + d.get("clones", 0))
        if d.get("invocar"):
            invocar(j, [d.get("invocar_turnos", 3), d["invocar"], "despertar"])
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
        if lutador.efeitos.sem_cura or not lutador.vivo or self.turnos >= LUTA_LONGA:
            return 0  # numa luta longa demais, ninguém fecha as feridas
        antes = lutador.vida
        cura = quanto * lutador.efeitos.cura_mult
        if lutador.sangue_turnos:
            cura *= CURA_SANGRANDO  # a ferida aberta não fecha
        cura = round(cura)
        lutador.vida = min(lutador.vida_max, lutador.vida + cura)
        return lutador.vida - antes

    def _ferir(self, lutador: Lutador, dano: int) -> int:
        feito = lutador.sofrer(dano)
        lutador.dor += feito
        if lutador is self.jogador:
            self.dano_recebido += feito
        if (
            lutador.chefe
            and not lutador.segunda_forma
            and lutador.vivo
            and lutador.vida <= lutador.vida_max * SEGUNDA_FORMA
        ):
            lutador.segunda_forma = self.forma_revelada = True
            lutador.dano_mult *= FURIA_CHEFE
            lutador.recargas.clear()
            lutador.adaptacao.clear()  # a roda do Mahoraga recomeça na segunda forma
            if lutador.preco and lutador.assinatura:
                lutador.recargas[lutador.assinatura] = 99  # a Lua Sem Fim não volta
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
        extra = alvo.modo.percepcao if alvo.modo is not None else 0
        if alvo is not self.jogador:
            extra += self.jogador.efeitos.percepcao_rival + self.jogador.percepcao_rival_luta
        return max(0, alvo.percepcao + alvo.percepcao_luta + extra)

    def outro(self, lutador: Lutador) -> Lutador:
        return self.rival if lutador is self.jogador else self.jogador

    def ver_intencao(self, de: Lutador | None = None) -> str | Tecnica | None:
        """O que o jogador enxerga da próxima ação de um rival (padrão: o alvo): nada, o
        tipo, ou a técnica."""
        j = self.jogador
        p, t = j.percepcao + j.percepcao_luta, self.intencao_de(de or self.rival)
        if j.modo is not None:
            p += j.modo.percepcao
        if t is None or p <= 0 or j.cego or j.cegueira or j.sem_percepcao:
            return None
        return t.tipo if p == 1 else t

    def turno_rival(self) -> Acao:
        """O rival da vez age (num bando, o combate fala com ele durante a ação)."""
        ator = self.vez
        assert ator is not self.jogador
        alvo = self.rival
        self.rival = ator
        try:
            tecnica = self.intencao_rival
            verdade = self._verdade.pop(id(ator), None)
            prontas = self.prontas(ator)
            if verdade is not None and verdade in prontas:
                tecnica, self._iludiu = verdade, True  # o anúncio era a ilusão
            elif tecnica is None or tecnica not in prontas:
                tecnica = escolher_rival(self)
            acao = self.resolver(tecnica)
        finally:
            self.rival = alvo
            self._iludiu, self._mecanica = False, ""
        self._reajustar_alvo()
        return acao

    def _inicio_do_turno(self, ator: Lutador) -> None:
        """O que acontece a quem age antes da ação: curas e preços por turno."""
        if self.turnos >= LUTA_LONGA:  # a luta que não acaba: os dois se gastam, cada vez mais
            ator.sofrer(1 + (self.turnos - LUTA_LONGA) // LUTA_LONGA_PASSO)
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
            ator.sofrer(round(ator.sangue * self.outro(ator).efeitos.dot_mult))
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
        # Leva 3: o que queima, o que envenena, o que luta ao seu lado
        dot = self.outro(ator).efeitos.dot_mult  # quem aplicou decide o quanto fere
        if ator.chama:
            self._ferir(ator, round(ator.chama * dot))  # a chama negra não apaga
            ator.chama += 1  # e cresce, até incinerar
            if ator.vivo and ator.vida <= INCINERAR * ator.chama:
                self._ferir(ator, ator.vida)  # o que sobra vira cinza
                ator.incinerado = not ator.vivo
        if ator.veneno:
            self._ferir(ator, round(ator.veneno * dot))
            ator.veneno -= 1
        m = ator.modo
        if m is not None:
            if m.regen:
                self._curar(ator, m.regen)
            if m.sangria:
                ator.sofrer(m.sangria)  # o corpo paga a forma
            if m.bloqueio:
                ator.bloqueio = max(ator.bloqueio, m.bloqueio)
        if ator.invocacoes:
            alvo = self.outro(ator)
            restantes = []
            for turnos, dano, origem in ator.invocacoes:
                if alvo.vivo:
                    absorvido = min(alvo.bloqueio, dano)
                    alvo.bloqueio -= absorvido
                    feito = self._ferir(alvo, dano - absorvido)  # a invocação ataca sozinha
                    self._invocadas.append((origem, feito))
                if turnos > 1:
                    restantes.append([turnos - 1, dano, origem])
            ator.invocacoes = restantes
        if ator.efeitos.crescer:
            antes = int(ator.crescido + 1e-9)
            ator.crescido += ator.efeitos.crescer
            ator.bonus_dano += int(ator.crescido + 1e-9) - antes

    def _turno_do_rival(self, r: Lutador) -> None:
        """O começo do turno de um rival: a guarda se recompõe um pouco, e o que a
        mecânica do chefe e os afixos da elite fazem a cada turno dele."""
        if r.guarda:
            r.guarda = max(0, r.guarda - round(r.vida_max * GUARDA_ESVAI))
        n, j = r.turnos_luta, self.jogador
        if r.blindagem and n % BLINDADO_CADA == 1:
            r.bloqueio = max(r.bloqueio, r.blindagem)  # Blindado
        if not r.vivo or not r.mecanica:
            return
        if r.mecanica == "armadura" and n % ARMADURA_CADA == 1:
            r.bloqueio = max(r.bloqueio, round(r.vida_max * ARMADURA_FRAC))
            self._mecanica = "armadura"
        elif r.mecanica == "repulsao" and n % REPULSAO_CADA == 0:
            j.clones, j.invocacoes, j.bloqueio = 0, [], 0  # tudo é empurrado para longe
            self._mecanica = "repulsao"
        elif r.mecanica == "regenera" and not (r.sangue_turnos or r.chama):
            if self._curar(r, round(r.vida_max * REGENERA)):  # a ferida aberta não fecha
                self._mecanica = "regenera"
        elif r.mecanica == "contrato" and n % CONTRATO_CADA == 0:
            r.contrato = True
        elif r.mecanica == "giro_da_roda":
            self._giro_do_dono(r, n)
        elif r.mecanica == "dominio_sem_barreira" and r.dominio:
            r.dominio -= 1
            if not r.dominio:  # o domínio fecha com o último corte
                j.sofrer(round(j.vida_max * DOMINIO_FIM))
                self._mecanica = "dominio_sem_barreira"
        elif r.mecanica == "cinco_minutos" and r.contagem:
            r.contagem -= 1
            if not r.contagem:  # o planeta explode: você e ele pagam
                j.sofrer(round(j.vida_max * CINCO_MINUTOS_DANO))
                j.clones, j.invocacoes = 0, []
                r.sofrer(round(r.vida_max * CINCO_MINUTOS_PRECO))
                self._mecanica = "cinco_minutos"
        elif r.mecanica == "amanhecer":
            if n < AMANHECER_TURNO:  # a noite: ele se refaz, a não ser que sangre ou envenene
                if not (r.sangue_turnos or r.veneno):
                    self._curar(r, math.ceil(r.vida_max * AMANHECER_FRAC))
            else:  # o sol nasce, e queima
                r.sofrer(math.ceil(r.vida_max * AMANHECER_FRAC))
                self._mecanica = "amanhecer"
        elif r.mecanica == "sonho_eterno" and r.sonho:
            r.sonho -= 1
            if not r.sonho:  # a lua cai: só uma proteção a reflete
                if j.bloqueio:
                    j.bloqueio = 0
                elif j.escudos:
                    j.escudos -= 1
                elif j.espelho:
                    j.espelho -= 1
                elif j.clones:
                    j.clones = 0
                else:
                    j.pular += SONHO_SONO
                self._mecanica = "sonho_eterno"

    def _assinaturas(self, r: Lutador) -> set[str]:
        """As técnicas de chefe de `r` (as que trazem uma mecânica)."""
        return {t.id for t in r.tecnicas if t.id == r.assinatura} | {r.assinatura}

    def _dominio_corta(self, jogador: Lutador) -> None:
        """O Domínio: no começo de cada turno seu, o corte que nada segura."""
        for r in self.rivais:
            if r.vivo and r.mecanica == "dominio_sem_barreira" and r.dominio:
                jogador.sofrer(DOMINIO_CORTE)
                self._mecanica = "dominio_sem_barreira"

    def _mecanicas_finais(
        self, ator: Lutador, alvo: Lutador, t: Tecnica, feriu: int, encadeada: bool
    ) -> None:
        """O que as mecânicas dos chefes finais fazem depois de uma ação."""
        j = self.jogador
        assinatura = t.id == ator.assinatura
        if ator.mecanica == "escuridao" and assinatura and feriu > 0 and alvo is j:
            j.modo, j.modo_id, j.modo_turnos = None, "", 0  # a forma se desfaz, sem preço
            for x in j.tecnicas:
                if x.raridade in ("maldito", "divino") or x.tipo == "modo":
                    j.recargas[x.id] = max(j.recargas.get(x.id, 0), ESCURIDAO_TRAVA)
            self._mecanica = "escuridao"
        elif ator.mecanica == "roubar" and assinatura and feriu > 0 and alvo is j:
            if ator.roubos < ROUBOS_MAX:
                livres = [x for x in j.tecnicas if j.recargas.get(x.id, 0) < 99]
                if livres:
                    tomada = max(
                        livres, key=lambda x: (x.dano * max(1, x.golpes), -j.recargas.get(x.id, 0))
                    )
                    j.recargas[tomada.id] = 99  # volta para você quando a luta acabar
                    ator.tecnicas.append(tomada)
                    ator.recargas[tomada.id] = 0
                    ator.roubos += 1
                    self._mecanica = "roubar"
        elif ator.mecanica == "marcha" and not encadeada and t is not HESITAR:
            if assinatura:
                ator.marcha = max(ator.marcha, 1)
            elif ator.marcha:
                ator.marcha = min(MARCHA_MAX, ator.marcha + 1)
                j.sofrer(ator.marcha)  # os colossos não param: nada segura o passo deles
                self._mecanica = "marcha"
        elif ator.mecanica == "dominio_sem_barreira" and assinatura:
            ator.dominio = DOMINIO_TURNOS
            j.clones, j.invocacoes = 0, []
            self._mecanica = "dominio_sem_barreira"
        elif ator.mecanica == "mundo_parado" and assinatura:
            ator.paradas += 1
            ator.parado = MUNDO_PARADO[min(ator.paradas, len(MUNDO_PARADO)) - 1]
            ator.extras += ator.parado - 2  # a técnica já dá duas ações seguidas
            self._mecanica = "mundo_parado"
        elif ator.mecanica == "mundo_parado" and ator.parado:
            ator.parado -= 1
        elif ator.mecanica == "cinco_minutos" and assinatura and not ator.contagem:
            ator.contagem = CINCO_MINUTOS
            self._mecanica = "cinco_minutos"
        for r in self.rivais:  # o Rei Renascido: a primeira morte não conta
            if r.mecanica == "rei_renascido" and not r.vivo and not r.renasceu:
                r.renasceu = r.segunda_forma = True
                r.vida = math.ceil(r.vida_max * RENASCER_VIDA)
                r.bonus_dano += RENASCER_DANO
                r.chama = max(r.chama, RENASCER_VENENO)  # o veneno da rosa vem junto
                self._mecanica = "rei_renascido"

    def _giro_do_dono(self, r: Lutador, n: int) -> None:
        """O Dono gira a Roda no 1º turno dele e a cada 3 (a cada 2 na segunda forma), sem
        gastar o turno: a fatia vale até o próximo giro. Todo giro te dá Carma (o erro dele).
        Na Dívida, ele se cura a cada turno, a não ser que sangre ou queime."""
        cada = GIRO_CADA_FURIA if r.segunda_forma else GIRO_CADA
        if n == 1 or (n - 1) % cada == 0:
            opcoes = [f for f in GIRO_FATIAS if f != self.roda_dono]
            self.roda_dono = self.rng.choice(opcoes)
            if self.jogador.carma is not None:
                self.jogador.carma.ganhar(GIRO_CARMA)
            self._mecanica = "giro_da_roda"
        if self.roda_dono == "divida" and not (r.sangue_turnos or r.chama):
            self._curar(r, round(r.vida_max * GIRO_DIVIDA))

    def _aliado_age(self) -> tuple:
        """O seu companheiro age (no começo do seu turno). Devolve (id, efeito, valor)."""
        a, j, alvo = self.aliado, self.jogador, self.rival
        if a is None or not j.vivo:
            return ()
        self._aliado_turnos += 1
        if self._aliado_turnos % a.cada:
            return ()
        v = a.valor_no_nivel(self.aliado_nivel)
        if a.acao == "curar":
            curou = self._curar(j, v) if j.vida < j.vida_max else 0
            return (a.id, "curar", curou) if curou else ()
        if a.acao == "bloquear":
            j.bloqueio = max(j.bloqueio, v)
            return (a.id, "bloquear", v)
        if not alvo.vivo:
            return ()
        if a.acao == "ferir":
            absorvido = min(alvo.bloqueio, v)
            alvo.bloqueio -= absorvido
            return (a.id, "ferir", self._ferir(alvo, v - absorvido))
        if a.acao == "expor":
            alvo.exposto = max(alvo.exposto, v)
        elif a.acao == "envenenar":
            alvo.veneno = max(alvo.veneno, v)  # mantém o veneno vivo (não empilha)
        else:
            raise ValueError(f"ação de aliado desconhecida: {a.acao}")
        return (a.id, a.acao, v)

    def _recarga(self, ator: Lutador, t: Tecnica) -> int:
        if t.recarga in (0, 99):
            return t.recarga
        menos = ator.efeitos.recarga_menos + ator.recarga_menos_luta
        selo = RECARGA_AMALDICOADA if ator.marca else 0  # a maldição sela
        ferrugem = 1 if self.roda_dono == "ferrugem" and ator is self.jogador else 0
        return max(1, t.recarga - menos) + selo + ferrugem

    def resolver(
        self, t: Tecnica, sacrificio: Tecnica | None = None, kokusen: bool = False
    ) -> Acao:
        """Usa `t`. `sacrificio`: a técnica que um Contrato destrói (padrão: a mais fraca).
        `kokusen`: o jogador acertou o tempo da barra (a tela decide): dano ×KOKUSEN_MULT
        e a zona sobe; um ataque fora do tempo, uma defesa ou tomar dano zeram a zona."""
        self._kokusen = kokusen and self.vez is self.jogador and t.dano > 0
        if self.acabou:
            raise RuntimeError("a luta já acabou")
        self.forma_revelada = False
        self._invocadas: list[tuple[str, int]] = []
        respingos: list[tuple[str, int]] = []
        protegido = curado = ""
        ator, alvo = self.vez, self.outro(self.vez)
        vida_antes = alvo.vida
        if t not in self.prontas(ator):
            raise ValueError(f"{ator.nome} não pode usar {t.nome} agora")
        ator.cego = False  # a cegueira dura até o próximo turno de quem a sofreu
        if t is HESITAR and ator.pular:
            ator.pular -= 1
        elif ator.quebrado:
            ator.quebrado = False  # ele agiu de novo: a guarda se recompõe
        # uma ação encadeada (Instante Suspenso, Veloz) não é um turno novo
        encadeada = bool(self.log) and self.log[-1].turno_extra and self.log[-1].ator == ator.nome
        if not encadeada:
            ator.turnos_luta += 1

        efetiva = t
        if t.copia_rival:
            efetiva = self.ultima_tecnica(alvo)  # Olho Roubado
        if t.custo_carma and ator.carma is not None:
            ator.carma.valor = max(0.0, ator.carma.valor - t.custo_carma)

        self._inicio_do_turno(ator)
        aliado = ()
        if ator is self.jogador and not encadeada:
            self._dominio_corta(ator)
            aliado = self._aliado_age()  # o companheiro age no começo do seu turno
            if not alvo.vivo and self.vivos:  # ele derrubou o alvo: a mira passa adiante
                self._reajustar_alvo()
                alvo = self.rival
        elif ator is not self.jogador and not encadeada:
            self._turno_do_rival(ator)
        if ator.mecanica == "balanca" and efetiva.id == ator.assinatura and alvo.vivo:
            # a Balança pesa os dois: quem tem menos (em fração da vida) obedece
            if alvo.vida / alvo.vida_max < ator.vida / ator.vida_max:
                self._mecanica = "balanca"
            else:  # a balança vira contra quem a ergueu
                self._mecanica = "balanca_virou"
                ator.pular += efetiva.atordoar
                enfraquecer(ator, efetiva.enfraquecer)
                efetiva = replace(efetiva, atordoar=0, enfraquecer=0)
        if ator.mecanica == "sonho_eterno" and efetiva.id in self._assinaturas(ator):
            ator.sonho, ator.pular = SONHO_TURNOS, ator.pular + 1  # canaliza: a lua vem
            efetiva = replace(efetiva, atordoar=0)
            self._mecanica = "sonho_eterno"
        if efetiva.vinculo and alvo.vivo:  # o ritual vem antes do preço: a dor já é dividida
            ator.vinculo, ator.elo = max(ator.vinculo, efetiva.vinculo), alvo
        if efetiva.custo_vida:
            ator.sofrer(efetiva.custo_vida)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        if efetiva.custo_vida_max:  # o preço que fica na run
            ator.base_vida_max = max(1, ator.base_vida_max - efetiva.custo_vida_max)
            ator.aplicar_efeitos(ator.efeitos)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        if efetiva.custo_percepcao:  # o Mangekyō cobra a visão, para sempre
            ator.base_percepcao = max(0, ator.base_percepcao - efetiva.custo_percepcao)
            ator.aplicar_efeitos(ator.efeitos)
            if ator.carma is not None:
                ator.carma.registrar_custo(ator.efeitos.carma_mult)
        if efetiva.purificar:
            ator.purificar()
        ativou_modo = efetiva.modo is not None
        if ativou_modo:
            if ator.modo is not None:
                ator.sair_do_modo()  # trocar de forma cobra a anterior
            ator.entrar_no_modo(efetiva)
        ator.bonus_dano += efetiva.fortalecer
        ator.bloqueio += round(efetiva.bloqueio * ator.efeitos.bloqueio_mult)
        ator.revide += efetiva.revide
        ator.escudos += efetiva.escudo
        alvo.marca += efetiva.marca
        ator.eco += efetiva.eco
        ator.instinto += efetiva.instinto
        if efetiva.roda_dharma:  # o General da Roda: daqui até o fim da luta você se adapta
            ator.roda_dharma = True
        ator.intocavel += efetiva.intocavel
        ator.fera += efetiva.fera
        ator.percepcao_luta += efetiva.foco
        ator.espelho += efetiva.espelho
        ator.regen_luta += efetiva.regenerar
        curou = self._curar(ator, efetiva.cura) if efetiva.cura else 0
        if efetiva.proteger and ator.vivo:  # o Guardião ergue a defesa de quem mais precisa
            protegido_lut = self._mais_ferido(ator)
            protegido_lut.bloqueio += efetiva.proteger
            protegido = protegido_lut.nome
        if efetiva.curar_aliado and ator.vivo:  # o Curandeiro fecha a ferida de quem sangra
            curado_lut = self._mais_ferido(ator)
            curou += self._curar(curado_lut, efetiva.curar_aliado)
            curado = curado_lut.nome
        if efetiva.inspirar:  # o Comandante: todo o bando bate mais forte
            for aliado in self.aliados(ator):
                aliado.bonus_dano += efetiva.inspirar
        ativou_santuario = efetiva.santuario > 0
        if ativou_santuario:
            ator.santuario = efetiva.santuario
            ator.pular_pendente = efetiva.pular_depois
        if ator.revelar and t not in (self.basico, HESITAR) and not ator.revelada:
            ator.revelada, ator.revelada_bonus, ator.revelar = efetiva.id, ator.revelar, 0.0

        surpresa, reagiu, total = self.abertura or efetiva.sempre_surpresa, False, 0
        esquivas = escudados = sombra = instintos = 0
        despertou, critico, quebrou = "", False, ""
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
                resto = alvo.marca + alvo.sangue * alvo.sangue_turnos + alvo.veneno
                base += efetiva.detonar * resto
                alvo.marca = alvo.sangue = alvo.sangue_turnos = alvo.veneno = 0
                ator.eco = 0  # sem Marca, sem o preço dela
        if efetiva.acumula:
            ator.acumulos[efetiva.id] = ator.acumulos.get(efetiva.id, 0) + efetiva.acumula
        if efetiva.dissipar:
            alvo.bloqueio = alvo.revide = alvo.escudos = alvo.espelho = 0
        if base > 0 and ator.vivo:
            perdida = 1 - max(0, ator.vida) / ator.vida_max
            fervor = round(ator.efeitos.furia * perdida)  # Sangue Fervente
            base += ator.bonus_dano + ator.efeitos.bonus_dano + fervor + ator.dano_extra
            base += GIRO_SANGUE if self.roda_dono == "sangue" else 0  # o Giro do Dono
            base += ator.dano_run
            modo = ator.modo
            if modo is not None:
                base += modo.dano
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
            if modo is not None:
                mult *= modo.dano_mult
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
            marcado = alvo.marca or alvo.sangue_turnos or alvo.veneno or alvo.chama
            if ator.efeitos.dano_marcado and marcado:
                mult *= 1 + ator.efeitos.dano_marcado
            if ator.veneno:  # o veneno amolece o corpo de quem golpeia
                mult *= 1 - min(FRAQUEZA_MAXIMA, FRAQUEZA_POR_DOSE * ator.veneno)
            adapta_chefe = alvo.mecanica == "adaptar" and ator is self.jogador
            adapta_voce = alvo is self.jogador and alvo.roda_dharma and ator is not alvo
            if adapta_chefe or adapta_voce:  # a Roda do Dharma gira
                usos = alvo.adaptacao.get(t.id, 0)
                alvo.adaptacao[t.id] = usos + 1
                mult *= ADAPTAR[min(usos, len(ADAPTAR) - 1)]
                if usos:
                    self._mecanica = "adaptar"
                    if adapta_chefe and usos == 1:  # adaptado: ele devolve o golpe
                        alvo.revide = max(alvo.revide, ADAPTAR_REVIDE)
            if ator.carga and t.id == ator.assinatura:  # Leigan: o Disparo sai carregado
                mult *= 1 + CARGA_BONUS * ator.carga
                self._mecanica = "carregar"
            base = round(base * mult)
            if efetiva.critico and self.rng.random() < efetiva.critico:
                base, critico = round(base * CRITICO), True  # Clarão Negro
            if self._kokusen and ator is self.jogador:  # o golpe no instante exato
                base, critico = round(base * KOKUSEN_MULT), True
            if alvo.chefe:
                base = round(base * ator.efeitos.dano_chefe_mult)  # Carrasco
            santuario = ator.santuario > 0 and not ativou_santuario
            if santuario:
                base = round(base * 1.5)
            absoluto = (
                efetiva.absoluto or ator.absolutos > 0 or (modo is not None and modo.absoluto)
            )
            perigoso = efetiva.perigosa or surpresa
            oculto = (
                (ator.efeitos.imperceptivel and efetiva.perigosa)
                or santuario
                or ator.imperceptivel_luta
            )
            emboscada = surpresa and ator.efeitos.primeiro_sangue
            sangue_frio = surpresa and alvo.efeitos.sangue_frio
            sutileza = efetiva.sutileza + ator.efeitos.sutileza
            if ator.parado:  # O Mundo Para: ninguém sente o que vem no tempo parado
                sutileza = SUTILEZA_TEMPO_PARADO
            if modo is not None:
                sutileza += modo.sutileza
            reagiu = (
                perigoso
                and not (oculto or emboscada)
                and (sangue_frio or self.percepcao_contra(alvo) >= sutileza)
            )
            if alvo.cegueira:
                alvo.cegueira -= 1

            # a postura do chefe: o quanto esta ação ainda pode tirar dele
            postura = [round(alvo.vida_max * POSTURA_CHEFE)] if alvo.chefe else None
            # Kamui: o ataque inteiro atravessa o corpo dele
            atravessa = (
                alvo.mecanica == "intangivel"
                and ator is self.jogador
                and not absoluto
                and self.rng.random() < INTANGIVEL
            )
            if atravessa:
                self._mecanica = "intangivel"
            petalas = ator.mecanica == "petalas"  # Senbonzakura: as pétalas passam pelos clones
            guarda = ator is self.jogador and alvo is not self.jogador  # só rivais têm guarda

            def golpear(dano: int) -> int:
                nonlocal esquivas, escudados, despertou, instintos, quebrou
                if alvo.intocavel or atravessa:  # Vazio Infinito: o golpe para no ar
                    escudados += 1
                    return 0
                if alvo.congelado:  # o gelo se estilhaça com o golpe
                    alvo.congelado, alvo.pular = False, 0
                    dano *= 2
                if alvo.exposto:
                    alvo.exposto -= 1
                    dano = round(dano * 1.5)
                recebido = alvo.efeitos.dano_recebido_mult * alvo.recebido_mult_luta
                if alvo.modo is not None:
                    recebido *= alvo.modo.recebido_mult
                if alvo.quebrado:
                    recebido *= GUARDA_QUEBRADA  # a guarda quebrada (a postura ainda segura)
                if self.roda_dono == "juizo" and alvo.mecanica == "giro_da_roda":
                    recebido *= GIRO_JUIZO
                if alvo.mecanica == "escuridao":  # a escuridão puxa tudo, até o golpe
                    recebido *= ESCURIDAO_RECEBE
                dano = round(dano * recebido)
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
                    esquiva = alvo.efeitos.esquiva + (alvo.modo.esquiva if alvo.modo else 0.0)
                    if esquiva and self.rng.random() < esquiva:
                        esquivas += 1  # Reflexo Treinado
                        return 0
                    # com N clones, o golpe acha um clone em N de N+1 vezes: quem sabe qual
                    # é o verdadeiro?
                    clones = alvo.clones and not petalas
                    if clones and self.rng.random() < alvo.clones / (alvo.clones + 1):
                        alvo.clones -= 1  # era um clone: some numa nuvem
                        escudados += 1
                        return 0
                    if alvo.escudos and not petalas:
                        alvo.escudos -= 1  # Pele de Cinzas
                        escudados += 1
                        return 0
                fura = efetiva.perfura or absoluto or (basico and ator.efeitos.basico_perfura)
                absorvido = 0 if fura else min(alvo.bloqueio, dano)
                if alvo.contrato and not absoluto and dano > absorvido:
                    alvo.contrato = False  # Makima: o golpe vai para outro lugar
                    self._mecanica = "contrato"
                    escudados += 1
                    return 0
                alvo.bloqueio -= absorvido
                inabalavel = alvo.modo is not None and alvo.modo.inabalavel
                if alvo is self.jogador and dano - absorvido >= alvo.vida and not inabalavel:
                    if self.pode_despertar():
                        despertou = self.despertar().id  # à beira da morte: o golpe é anulado
                        return 0
                    if self.pode_eclipse():
                        despertou = self.despertar(eclipse=True).id  # o Ovo do Eclipse
                        return 0
                real = dano - absorvido
                if postura is not None:
                    real = min(real, postura[0])
                    postura[0] -= real
                feito = self._ferir(alvo, real)
                if feito and guarda and not alvo.quebrado and alvo.vivo:
                    alvo.guarda += feito + GUARDA_POR_GOLPE  # a pressão se acumula
                    if alvo.guarda >= limiar_guarda(alvo):  # a guarda quebra
                        alvo.guarda, alvo.quebrado = 0, True
                        alvo.pular = max(alvo.pular, 1)
                        quebrou = alvo.nome
                if alvo.revide and dano:
                    self._ferir(ator, alvo.revide)
                    alvo.revide = 0
                if feito and alvo.efeitos.veneno_espinhos:
                    ator.veneno += alvo.efeitos.veneno_espinhos  # o corpo é veneno
                return feito

            por_golpe = base // 2 if reagiu else base
            if surpresa and not reagiu and not alvo.efeitos.sem_surpresa:
                por_golpe = round(por_golpe * (1 + self.bonus_surpresa))
            golpes = efetiva.golpes + (ator.efeitos.basico_golpes if basico else 0)
            golpes += 1 if ator.fera else 0  # Fera Interior
            golpes += modo.golpes if modo is not None else 0
            for _ in range(golpes):
                total += golpear(por_golpe)
                if not alvo.vivo:
                    break
            for _ in range(min(ator.clones, 3)):  # os clones atacam junto
                if not alvo.vivo:
                    break
                total += golpear(max(1, round(por_golpe * 0.4)))
            if ator.efeitos.sombra and alvo.vivo and ator.vivo:
                sombra = golpear(round(por_golpe * ator.efeitos.sombra))  # Sombra Leal
                total += sombra
            if reagiu and alvo.vivo:
                self._ferir(ator, self.basico.dano)  # o contra-golpe de quem sentiu o perigo
            if efetiva.area and total and ator is self.jogador:
                for outro in self.vivos:  # a explosão pega o bando inteiro
                    if outro is not alvo:
                        respingo = round(total * efetiva.area)
                        absorvido = min(outro.bloqueio, respingo)
                        outro.bloqueio -= absorvido
                        respingos.append((outro.nome, self._ferir(outro, respingo - absorvido)))
            if alvo.instinto:
                alvo.instinto -= 1
            ator.atacou = True
            if ator.absolutos and absoluto and not efetiva.absoluto:
                ator.absolutos -= 1
            drenar = efetiva.drenar + ator.efeitos.drenar + ator.drenar_luta
            if modo is not None:
                drenar += modo.drenar
            if drenar and total:
                curou += self._curar(ator, round(total * drenar))
            passivo = ator.efeitos.sangrar if total else 0
            if (efetiva.sangrar or passivo) and alvo.vivo:
                alvo.sangue += efetiva.sangrar
                alvo.sangue = max(alvo.sangue, passivo)  # o passivo renova, não empilha
                alvo.sangue_turnos = 3
            if total and alvo.vivo:  # o veneno precisa entrar na carne
                alvo.veneno += efetiva.veneno + ator.efeitos.veneno_ao_ferir
        else:
            if efetiva.sangrar and alvo.vivo:
                alvo.sangue += efetiva.sangrar
                alvo.sangue_turnos = 3
            if efetiva.veneno and alvo.vivo:  # névoa, gás, esporos: sem golpe
                alvo.veneno += efetiva.veneno

        selou, atordoou = "", False
        if total and alvo.vivo and ator.marca_ao_ferir:  # Amaldiçoado: a Marca fica
            alvo.marca = max(alvo.marca, ator.marca_ao_ferir)
        if total and alvo.vivo and ator.gelo and not alvo.pular and self.rng.random() < ator.gelo:
            alvo.pular += 1  # Gélido: o golpe congela
            alvo.congelado = atordoou = True
        if efetiva.selar and alvo.vivo:
            selou = self._selar(alvo, efetiva.selar)
        if efetiva.atordoar and alvo.vivo:
            alvo.pular += efetiva.atordoar  # Lua Ilusória
            atordoou = True
        if alvo.vivo:
            enfraquecer(alvo, efetiva.enfraquecer)
            alvo.cegueira += efetiva.cegar
            alvo.exposto += efetiva.expor
            alvo.silencio += efetiva.silenciar
            alvo.desarme += efetiva.desarmar
            if efetiva.bomba:
                alvo.bombas.append([efetiva.bomba_turnos, efetiva.bomba])
            alvo.chama += efetiva.chama_eterna  # basta o olhar: não há esquiva
            if efetiva.congelar:
                alvo.pular += efetiva.congelar
                alvo.congelado = atordoou = True
        ator.clones = min(MAX_CLONES, ator.clones + efetiva.clones)
        if efetiva.invocar and alvo.vivo:  # a invocação ataca assim que chega
            absorvido = min(alvo.bloqueio, efetiva.invocar)
            alvo.bloqueio -= absorvido
            total += self._ferir(alvo, efetiva.invocar - absorvido)
            if efetiva.invocar_turnos > 1:
                invocar(ator, [efetiva.invocar_turnos - 1, efetiva.invocar, efetiva.id])
        mudou_rival = selou or atordoou or efetiva.silenciar or efetiva.desarmar or quebrou
        if mudou_rival and alvo is not self.jogador:
            if selou or atordoou or efetiva.silenciar or quebrou:
                alvo.carga = 0  # o disparo que carregava se perde
            self.intencao_rival = escolher_rival(self)  # o que ele anunciou não vem mais

        for tid in list(ator.recargas):
            if ator.recargas[tid] > 0:
                ator.recargas[tid] -= 1
        sem_recarga = ator.modo is not None and ator.modo.sem_recarga and not ativou_modo
        if t not in (self.basico, HESITAR) and t.recarga and not ator.forma and not sem_recarga:
            ator.recargas[t.id] = self._recarga(ator, t)  # na Forma Desperta, nada em recarga
        if efetiva.acelerar:
            for tid in list(ator.recargas):
                if tid != t.id and 0 < ator.recargas[tid] < 99:
                    ator.recargas[tid] = max(0, ator.recargas[tid] - efetiva.acelerar)
        if ator.forma:
            ator.forma -= 1
        if ator.fera:
            ator.fera -= 1
        if ator.modo is not None and not ativou_modo and ator.vivo:
            ator.modo_turnos -= 1
            if ator.modo_turnos <= 0:
                ator.sair_do_modo()  # a forma se desfaz: o preço vem agora
        if ator.vinculo and not efetiva.vinculo:
            ator.vinculo -= 1
            if not ator.vinculo:
                ator.elo = None
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
        if ator.veloz and not encadeada and t is not HESITAR and ator.turnos_luta % ator.veloz == 0:
            ator.extras += 1  # Veloz: desta vez, age duas vezes seguidas
        if ator.mecanica == "carregar" and not encadeada and t is not HESITAR:
            disparou = t.id == ator.assinatura  # disparar descarrega; esperar carrega
            ator.carga = 0 if disparou else min(CARGA_MAX, ator.carga + 1)
        self._mecanicas_finais(ator, alvo, t, vida_antes - alvo.vida, encadeada)
        if ator is self.jogador and t is not HESITAR:  # a zona do Kokusen
            ator.zona = min(ZONA_MAX, ator.zona + 1) if self._kokusen else 0
        elif ator is not self.jogador and vida_antes > alvo.vida and alvo is self.jogador:
            alvo.zona = 0  # tomou dano: sai da zona
        if ator.mecanica == "preco" and t.id == ator.assinatura and not ator.preco:
            ator.preco = True  # Mugetsu: o poder inteiro num golpe, e o que sobra é metade
            ator.dano_mult *= PRECO
            self._mecanica = "preco"

        do_outro_lado = bool(self.vivos) if ator is self.jogador else alvo.vivo
        extra = ator.extras > 0 and ator.vivo and do_outro_lado
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
            incinerou=ator.incinerado,
            segunda_forma=self.forma_revelada,
            alvo=alvo.nome,
            invocadas=tuple(self._invocadas),
            respingo=tuple(respingos),
            protegido=protegido,
            curado=curado,
            quebrou=quebrou,
            mecanica=self._mecanica,
            iludiu=self._iludiu,
            aliado=aliado,
        )
        self._mecanica, self._iludiu = "", False
        self.log.append(acao)
        self.abertura = False
        self.turnos += 1
        if not extra:  # Instante Suspenso: a vez continua com quem agiu
            self.vez = self._depois_de(ator)
            if self.vez is self.jogador:
                self.rodadas += 1
        limite = self.jogador.efeitos.limite_turnos or 0
        if len(self.rivais) == 1:
            estourou = self.turnos >= 2 * limite
        else:  # num bando, o prazo conta voltas inteiras
            estourou = self.rodadas >= limite
        if limite and estourou and self.vivos and self.jogador.vivo:
            self.estourou_prazo = True  # voto Prazo
        self._depois_da_acao(acao, ator, t)
        if ator is not self.jogador and not self.acabou:
            # Anuncia ao fim do próprio turno, para o jogador ver antes de escolher. A técnica
            # anunciada continua pronta até lá: recargas do rival só descem no turno dele.
            self.intencao_rival = escolher_rival(self)
        if ator is self.jogador:
            self._reajustar_alvo()
        return acao


def invocar(lutador: Lutador, entrada: list) -> None:
    """Uma invocação entra em campo ([turnos, dano, de onde veio]). No limite, a mais
    antiga vai embora: o campo não comporta um exército inteiro."""
    lutador.invocacoes.append(entrada)
    del lutador.invocacoes[:-MAX_INVOCACOES]


def _extra_da_dor(t: Tecnica, ator: Lutador) -> int:
    extra = int(t.dano_por_dor * ator.dor)
    return min(extra, t.teto_dor) if t.teto_dor else extra


def _selar_alvo(luta: Luta, alvo: Lutador) -> Tecnica | None:
    """O que a Corrente prende: a ação anunciada do rival, ou a melhor técnica pronta."""
    if alvo is not luta.jogador:
        t = luta.intencao_de(alvo)
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
        base += t.detonar * (alvo.marca + alvo.sangue * alvo.sangue_turnos + alvo.veneno)
        if t.executar and alvo.vida < alvo.vida_max * t.executar:
            base *= 2
    extra = ator.bonus_dano + ator.efeitos.bonus_dano
    if ator.modo is not None:
        extra += ator.modo.dano
    if t is luta.basico:
        extra += ator.efeitos.basico_dano
        golpes = t.golpes + ator.efeitos.basico_golpes
    else:
        golpes = t.golpes
    valor = (base + extra) * golpes if base > 0 else 0.0
    if alvo.congelado and valor:
        valor *= 2
    # o que fere com o tempo (Leva 3): o que ainda vai doer, em poucos turnos
    valor += 3 * t.chama_eterna + t.veneno * (t.veneno + 1) / 2 + t.invocar * t.invocar_turnos
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
        chama_eterna=cresce(t.chama_eterna),
        veneno=cresce(t.veneno),
        invocar=cresce(t.invocar),
        clones=cresce(t.clones),
        modo=replace(t.modo, turnos=t.modo.turnos + 1) if t.modo is not None else None,
        recarga=recarga,
    )


def valor_tecnica(t: Tecnica) -> float:
    """Valor bruto de uma técnica, para escolher o que um Contrato sacrifica."""
    valor = t.dano * t.golpes + t.bloqueio + t.revide + 3 * (t.marca + t.fortalecer)
    valor += t.cura + 6 * t.atordoar + 4 * t.selar + 8 * t.escudo
    valor += 3 * t.sangrar + t.bomba + 3 * t.regenerar + 5 * (t.silenciar + t.espelho)
    valor += 6 * t.chama_eterna + 2 * t.veneno + t.invocar * t.invocar_turnos
    valor += 6 * (t.congelar + t.clones) + 4 * t.vinculo + (12 if t.modo is not None else 0)
    valor += t.proteger + t.curar_aliado + 4 * t.inspirar
    return valor + 4 * (t.instinto + t.intocavel + t.fera + t.enfraquecer)


def _vale_o_preco(luta: Luta, j: Lutador, t: Tecnica) -> bool:
    """Poderes que custam caro só valem na hora certa.

    Carma e técnica consumidos: para fechar a luta ou num chefe. Marca: só em luta que
    ainda vai durar (rival com vida) e sem empilhar além de duas — o preço também se soma.
    """
    rival = luta.rival
    if t.modo is not None:  # transformar custa; só em luta que ainda dura, e uma forma por vez
        m = t.modo
        caro = m.exausto or m.travar or m.vida_max_run or m.adiado or m.sangria or t.custo_vida
        return j.modo is None and (rival.chefe or rival.vida >= (30 if caro else 10))
    if t.custo_percepcao:  # o preço fica na run: só contra chefe ou rival que vai durar
        return rival.chefe or rival.vida >= 30
    if t.purificar and not t.dano:
        sujo = j.sangue * j.sangue_turnos + j.veneno + j.marca
        return sujo >= 6 or j.silencio or j.desarme or j.bonus_dano < 0
    if t.chama_eterna and not t.dano:
        return rival.vida >= 15 and rival.chama == 0
    if t.congelar:
        return rival.vida >= 12 and not rival.pular
    if (t.invocar or t.vinculo or t.clones) and not t.dano:
        return rival.vida >= 15 and not (t.clones and j.clones >= 2)
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


MALDICOES = ("veneno", "marca", "enfraquecer", "cegar", "sangrar", "chama_eterna", "expor")


def _maldicao(t: Tecnica) -> bool:
    return any(getattr(t, a) for a in MALDICOES)


def _pelo_papel(luta: Luta, rival: Lutador, prontas: list[Tecnica]) -> Tecnica | None:
    """O que o papel manda fazer num bando (None: age como um rival qualquer)."""
    ferido = luta._mais_ferido(rival)
    fracao = ferido.vida / ferido.vida_max
    if rival.papel == "curandeiro":
        curas = [t for t in prontas if t.curar_aliado]
        if curas and fracao < 0.7:
            return curas[0]
    elif rival.papel == "guardiao":
        guardas = [t for t in prontas if t.proteger]
        if guardas and ferido.bloqueio == 0:
            return guardas[0]
    elif rival.papel == "comandante":
        gritos = [t for t in prontas if t.inspirar]
        if gritos:
            return gritos[0]
    elif rival.papel == "xama":
        pragas = [t for t in prontas if _maldicao(t)]
        if pragas and luta.rng.random() < 0.75:
            return luta.rng.choice(pragas)
    return None


def _assinatura_vale(luta: Luta, rival: Lutador, t: Tecnica) -> bool:
    """O chefe sabe o preço da própria técnica: a Balança só quando você obedeceria; a Lua
    Sem Fim (que cobra metade do poder) para fechar a luta ou na segunda forma."""
    j = luta.jogador
    if rival.mecanica == "balanca":
        return j.vida / j.vida_max < rival.vida / rival.vida_max
    if rival.mecanica == "preco":
        golpe = _valor_ofensivo(luta, rival, t) * rival.dano_mult
        return rival.segunda_forma or j.vida <= golpe * 1.2
    return True


def _valor_contra(luta: Luta, j: Lutador, t: Tecnica) -> float:
    """O valor ofensivo de `t` contra o alvo, lendo a mecânica do chefe (o piloto)."""
    valor, r = _valor_ofensivo(luta, j, t), luta.rival
    m = r.mecanica
    if m == "adaptar":  # o que a roda já aprendeu rende menos
        valor *= ADAPTAR[min(r.adaptacao.get(t.id, 0), len(ADAPTAR) - 1)]
    elif m == "contrato" and r.contrato and not t.absoluto:  # o 1º golpe vai embora
        valor *= (t.golpes - 1) / t.golpes
    elif m == "intangivel" and t.absoluto:
        valor *= 1.5
    elif m == "regenera" and (t.sangrar or t.chama_eterna):
        valor += 6  # a ferida aberta corta a regeneração
    elif m == "armadura" and (t.perfura or t.absoluto):
        valor += r.bloqueio
    return valor


def escolher_rival(luta: Luta) -> Tecnica:
    """IA simples do rival: defende quando está mal, prepara malditas cedo, senão bate forte.
    Num bando, o papel vem antes (o curandeiro cura, o guardião protege...)."""
    rival, rng = luta.rival, luta.rng
    prontas = luta.prontas(rival)
    if rival.mecanica and rival.assinatura:  # a assinatura que custa caro espera a hora
        prontas = [
            t for t in prontas if t.id != rival.assinatura or _assinatura_vale(luta, rival, t)
        ] or prontas
    if rival.papel:
        pelo_papel = _pelo_papel(luta, rival, prontas)
        if pelo_papel is not None:
            return pelo_papel
    defesas = [t for t in prontas if t.tipo == "defesa"]
    if defesas and rival.vida < rival.vida_max * 0.4 and rng.random() < 0.5:
        return rng.choice(defesas)
    preparos = [t for t in prontas if t.tipo == "maldita" and _valor_ofensivo(luta, rival, t) == 0]
    if rival.modo is None:  # o rival também se transforma, cedo
        preparos += [t for t in prontas if t.modo is not None]
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


PRIORIDADE_ALVO = {"curandeiro": 0, "xama": 1, "comandante": 1, "lamina": 2, "": 2, "guardiao": 3}


def escolher_alvo_auto(luta: Luta) -> Lutador:
    """Piloto automático da mira: quem cai com um Golpe primeiro; senão quem cura, quem
    amaldiçoa e por último o guardião (o mais fraco de cada papel antes)."""
    vivos = luta.vivos
    if len(vivos) == 1:
        return vivos[0]
    golpe = luta.basico.dano + luta.jogador.bonus_dano + luta.jogador.dano_run
    caidos = [r for r in vivos if r.vida <= golpe]
    if caidos:
        return min(caidos, key=lambda r: r.vida)
    return min(vivos, key=lambda r: (PRIORIDADE_ALVO.get(r.papel, 2), r.vida))


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
    if len(luta.vivos) > 1:  # num bando, o que importa é o golpe perigoso que vem
        for r in luta.vivos:
            v = luta.ver_intencao(r)
            if isinstance(v, Tecnica) and v.perigosa:
                vista = v
                break
    selos = [t for t in prontas if t.selar]
    if isinstance(vista, Tecnica) and vista is not luta.basico and selos:
        if _valor_ofensivo(luta, luta.rival, vista) >= 8:
            return selos[0]  # prende o golpe que vem
    r = luta.rival
    if r.carga and isinstance(vista, Tecnica) and vista.id == r.assinatura:
        corta = [t for t in prontas if t.atordoar or t.selar or t.silenciar or t.congelar]
        if corta:  # o Disparo carregado vem aí: atordoar ou selar descarrega
            return corta[0]
    curas = [t for t in prontas if t.cura and not t.dano]
    if curas and j.vida < j.vida_max * 0.45:
        return max(curas, key=lambda t: t.cura)
    defesas = [t for t in prontas if t.tipo == "defesa" and not t.cura]
    if isinstance(vista, Tecnica) and vista.perigosa and defesas:
        return max(defesas, key=lambda t: t.bloqueio + t.revide)
    if vista == "ataque" and defesas and j.vida < j.vida_max * 0.35:
        return defesas[0]
    poupa = luta.rival.mecanica in ("adaptar", "contrato")  # no empate, gasta o Golpe
    melhor = max(prontas, key=lambda t: (_valor_contra(luta, j, t), poupa and t is luta.basico))
    preparos = [t for t in prontas if t.tipo == "maldita" and _valor_ofensivo(luta, j, t) == 0]
    preparos += [t for t in prontas if t.modo is not None and t not in preparos]
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

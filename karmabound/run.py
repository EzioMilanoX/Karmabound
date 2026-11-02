"""Uma run: os passos e um piloto automático que os percorre.

Os passos (`aplicar_dom`, `aplicar_arco`, `comecar_luta`, `encerrar_luta`,
`receber_tecnica`, `receber_reliquia`, `girar`...) são as regras da run. Dois
pilotos os usam: `jogar_run` (o piloto automático, para o simulador e para o
Altar) e a `Jornada` (uma pessoa, fase a fase). Assim o que a simulação mede é
exatamente o jogo que se joga.

`medir` é como o Altar dos Votos pesa uma restrição: continua a run do jogador
muitas vezes, com e sem ela, usando as mesmas seeds dos dois lados (números
aleatórios comuns), e devolve a diferença em lutas vencidas.

Despertar: acontece na luta (`Luta.despertar`), quando o jogador quer ou à beira
da morte; o tipo sai da Roda do Despertar, e o próximo giro depois da luta vem
Divino garantido. O Carma cheio fica esperando a luta: não desperta no giro.
Com o Coração Selado, o Carma que enche vira um Despertar guardado e recomeça.
"""

from __future__ import annotations

import copy
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from karmabound.carma import ConfigCarma
from karmabound.combate import (
    Luta,
    Lutador,
    Tecnica,
    config_combate,
    escolher_jogador_auto,
    evoluir,
)
from karmabound.efeitos import Efeitos, somar
from karmabound.mesa import Giro, Mesa
from karmabound.rodas import (
    Fatia,
    Raridade,
    Roda,
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
)
from karmabound.votos import Catalogo, Voto, Votos, carregar_catalogo, lutas_da_duracao


@dataclass(frozen=True)
class Contexto:
    """O que não muda durante uma run: dados, regras e forma."""

    rodas: dict[str, Roda]
    raridades: list[Raridade]
    config_carma: ConfigCarma
    combate: dict  # já com a dificuldade aplicada
    catalogo: Catalogo
    basico: Tecnica
    capitulos: int = 3
    lutas_por_capitulo: int = 4
    chance_reliquia: float = 1 / 3
    max_turnos: int = 80

    @property
    def lutas(self) -> int:
        """Lutas de uma run sem Invasão."""
        return self.capitulos * self.lutas_por_capitulo

    @property
    def ordem(self) -> list[str]:
        return [r.id for r in self.raridades]

    @property
    def tecnicas(self) -> dict[str, Fatia]:
        return {f.id: f for f in self.rodas["tecnicas"].fatias}

    @classmethod
    def padrao(cls, dificuldade: str | None = None, balanceamento: dict | None = None) -> Contexto:
        bal = balanceamento or carregar_balanceamento()
        raridades = carregar_raridades(bal)
        cfg = config_combate(bal, dificuldade)
        return cls(
            rodas=carregar_rodas(raridades),
            raridades=raridades,
            config_carma=ConfigCarma.de_dict(bal["carma"]),
            combate=cfg,
            catalogo=carregar_catalogo(),
            basico=Tecnica.de_dict(cfg["golpe_basico"]),
        )


@dataclass
class EstadoRun:
    jogador: Lutador
    mesa: Mesa
    votos: Votos
    proxima_luta: int = 1  # número da próxima luta na run inteira (dá a força do rival)
    capitulo: int = 1
    luta_no_capitulo: int = 1
    tamanho_capitulo: int = 4  # cresce com a Invasão
    lutas_vencidas: int = 0
    derrotado: bool = False
    venceu: bool = False
    transbordos: int = 0  # vezes que o Carma transbordou (Despertar ou guardado)
    despertares: int = 0
    divino_pendente: int = 0  # giros Divinos garantidos por Despertares feitos na luta
    altares: int = 0
    pontos_guardados: float = 0.0  # pontos de voto não gastos: ficam para o próximo voto
    dom: Fatia | None = None
    arco: Fatia | None = None  # None no começo de cada capítulo: falta girar o Arco
    reliquias: list[Fatia] = field(default_factory=list)
    fragmentos: Counter = field(default_factory=Counter)

    @property
    def acabou(self) -> bool:
        return self.derrotado or self.venceu

    @property
    def chefe(self) -> bool:
        return self.luta_no_capitulo >= self.tamanho_capitulo

    @property
    def regra(self) -> dict:
        return (self.arco.regra or {}) if self.arco else {}

    def clonar(self, rng: random.Random) -> EstadoRun:
        """Cópia independente para simular um futuro (rodas e catálogo são compartilhados)."""
        mesa = Mesa(self.mesa.rodas, self.mesa.raridades, self.mesa.carma.config, rng)
        mesa.carma = copy.copy(self.mesa.carma)
        jogador = copy.copy(self.jogador)
        jogador.tecnicas = list(self.jogador.tecnicas)
        jogador.recargas = dict(self.jogador.recargas)
        jogador.carma = mesa.carma
        votos = Votos(self.votos.catalogo, [copy.copy(v) for v in self.votos.ativos])
        clone = copy.copy(self)
        clone.jogador, clone.mesa, clone.votos = jogador, mesa, votos
        clone.reliquias = list(self.reliquias)
        clone.fragmentos = Counter(self.fragmentos)
        return clone


# ----------------------------------------------------------------------- efeitos


def efeitos_do_estado(estado: EstadoRun) -> Efeitos:
    """Votos + Dom + Relíquias + a parte do Arco que é do jogador."""
    partes = [estado.votos.efeitos()]
    if estado.dom is not None and estado.dom.efeito:
        partes.append(Efeitos.de_dict(estado.dom.efeito))
    partes += [Efeitos.de_dict(r.efeito) for r in estado.reliquias if r.efeito]
    if estado.regra.get("carma_mult"):
        partes.append(Efeitos(carma_mult=estado.regra["carma_mult"]))
    return somar(partes)


def atualizar_efeitos(estado: EstadoRun) -> None:
    efeitos = efeitos_do_estado(estado)
    estado.jogador.aplicar_efeitos(efeitos)
    estado.mesa.carma.guardar = efeitos.guarda_despertar


# ----------------------------------------------------------------------- roleta


def girar(estado: EstadoRun, ctx: Contexto, roda: str) -> Giro:
    """Gira uma roda da run. Depois de um Despertar na luta, o giro vem Divino garantido."""
    if estado.divino_pendente:
        estado.divino_pendente -= 1
        return estado.mesa.girar(roda, forcar_despertar=True)
    return estado.mesa.girar(roda, permitir_despertar=False)


# ----------------------------------------------------------------------- passos


def espacos(estado: EstadoRun, ctx: Contexto) -> int:
    """Espaços de técnica do jogador (a Fruta Proibida dá mais um)."""
    return ctx.combate["espacos"] + estado.jogador.efeitos.espacos_extra


def aplicar_dom(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> None:
    estado.dom = fatia
    j = estado.jogador
    j.tecnica_dom = None
    if fatia.tecnica:
        j.tecnica_dom = Tecnica(
            id=fatia.id, nome=fatia.nome, raridade=fatia.raridade, **fatia.tecnica
        )
    atualizar_efeitos(estado)


def aplicar_arco(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> None:
    estado.arco = fatia
    estado.tamanho_capitulo = ctx.lutas_por_capitulo + estado.regra.get("luta_extra", 0)
    atualizar_efeitos(estado)


def gerar_rival(
    ctx: Contexto,
    n_luta: int,
    rng: random.Random,
    capitulo: int | None = None,
    chefe: bool | None = None,
) -> Lutador:
    cfg = ctx.combate["rivais"]
    por_capitulo = cfg["raridades_por_capitulo"]
    if capitulo is None:
        capitulo = (n_luta - 1) // ctx.lutas_por_capitulo + 1
    if chefe is None:
        chefe = n_luta % ctx.lutas_por_capitulo == 0
    indice = min(capitulo - 1, len(por_capitulo) - 1)
    raridades = set(por_capitulo[indice])
    pool = [f for f in ctx.tecnicas.values() if f.raridade in raridades and f.combate]
    n_tec = min(len(pool), cfg["tecnicas_base"] + indice * cfg["tecnicas_por_capitulo"])
    vida = cfg["vida_base"] + cfg["vida_por_luta"] * n_luta
    return Lutador(
        nome=f"Rival {n_luta}" + (" (chefe)" if chefe else ""),
        vida_max=round(vida * (cfg["chefe_multiplicador"] if chefe else 1)),
        velocidade=rng.randint(*cfg["velocidade"]),
        percepcao=rng.randint(*cfg["percepcao"]) + (cfg["chefe_percepcao_extra"] if chefe else 0),
        tecnicas=[Tecnica.de_fatia(f) for f in rng.sample(pool, n_tec)],
        chefe=chefe,
    )


def comecar_luta(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> Luta:
    rival = gerar_rival(ctx, estado.proxima_luta, rng, estado.capitulo, estado.chefe)
    regra = estado.regra
    mult = regra.get("vida_rival_mult", 1.0) * (
        regra.get("chefe_mult", 1.0) if rival.chefe else 1.0
    )
    if mult != 1.0:
        rival.vida_max = rival.base_vida_max = rival.vida = round(rival.vida_max * mult)
    jogador = estado.jogador
    jogador.nova_luta()
    if regra.get("dano_todos"):  # Lua de Sangue: vale para os dois
        jogador.dano_extra = rival.dano_extra = regra["dano_todos"]
    if rival.chefe and regra.get("chefe_mult"):  # Arco do Juízo
        rival.dano_mult = regra["chefe_mult"]

    def ao_despertar():
        estado.despertares += 1
        estado.transbordos += 1
        estado.divino_pendente += 1
        return estado.mesa.girar("despertar").fatias[0]

    def ao_eclipse():  # o preço do Ovo do Eclipse: o Dom
        estado.dom = None
        jogador.tecnica_dom = None
        atualizar_efeitos(estado)

    return Luta(
        jogador,
        rival,
        ctx.basico,
        rng,
        ctx.combate["bonus_surpresa"],
        ao_despertar=ao_despertar,
        espacos=espacos(estado, ctx),
        ao_eclipse=ao_eclipse,
    )


def encerrar_luta(estado: EstadoRun, ctx: Contexto, luta: Luta) -> bool:
    """Fecha a luta: contadores, recompensas, cura, votos e o avanço de capítulo."""
    jogador, carma = estado.jogador, estado.mesa.carma
    luta.encerrar()
    if luta.vencedor is not jogador:
        estado.derrotado = True
        return False
    estado.lutas_vencidas += 1
    estado.proxima_luta += 1
    if jogador.efeitos.vida_por_vitoria:  # Manto de Peso: o treino acumula
        v, n = jogador.efeitos.vida_por_vitoria, estado.lutas_vencidas
        ganho = int(n * v) - int((n - 1) * v)
        jogador.base_vida_max += ganho
        jogador.vida += ganho
    if jogador.efeitos.carma_por_vitoria:
        carma.ganhar(jogador.efeitos.carma_por_vitoria)  # Rosário de Ossos
    if luta.rival.chefe and estado.regra.get("carma_cheio_chefe"):
        carma.ganhar(carma.config.maximo)  # Arco do Juízo
    if not jogador.efeitos.sem_cura:
        fracao = estado.regra.get("cura_entre_lutas", ctx.combate["cura_entre_lutas"])
        fracao *= jogador.efeitos.cura_mult
        jogador.vida = min(jogador.vida_max, jogador.vida + round(jogador.vida_max * fracao))
    estado.votos.fim_de_luta()
    if estado.luta_no_capitulo >= estado.tamanho_capitulo:
        estado.capitulo += 1
        estado.luta_no_capitulo = 1
        estado.arco = None
        estado.tamanho_capitulo = ctx.lutas_por_capitulo
        estado.venceu = estado.capitulo > ctx.capitulos
    else:
        estado.luta_no_capitulo += 1
    atualizar_efeitos(estado)
    return True


def receber_tecnica(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> str:
    """'altar' | 'equipada' | 'fragmento' | 'evoluiu' | 'cheio' (falta escolher o que sai)."""
    if fatia.evento == "altar":
        return "altar"
    if not fatia.combate:
        return "nada"
    tecnicas = estado.jogador.tecnicas
    for i, t in enumerate(tecnicas):
        if t.id == fatia.id:  # duplicata
            estado.fragmentos[t.id] += 1
            if estado.jogador.efeitos.evolucao_imediata or estado.fragmentos[t.id] >= 2:
                tecnicas[i] = evoluir(t, estado.jogador.efeitos.fator_evolucao)
                estado.fragmentos[t.id] = 0
                return "evoluiu"
            return "fragmento"
    if len(tecnicas) < espacos(estado, ctx):
        tecnicas.append(Tecnica.de_fatia(fatia))
        return "equipada"
    return "cheio"


def substituir_tecnica(estado: EstadoRun, sai: Tecnica | None, entra: Fatia) -> None:
    if sai is not None:
        estado.jogador.tecnicas.remove(sai)
        estado.jogador.tecnicas.append(Tecnica.de_fatia(entra))


def receber_reliquia(estado: EstadoRun, fatia: Fatia) -> None:
    estado.reliquias.append(fatia)
    atualizar_efeitos(estado)


def vai_ter_reliquia(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> bool:
    sorte = rng.random()
    return estado.regra.get("reliquia_garantida", False) or sorte < ctx.chance_reliquia


# ----------------------------------------------------------------------- piloto automático


def nova_run(ctx: Contexto, rng: random.Random) -> EstadoRun:
    mesa = Mesa(ctx.rodas, ctx.raridades, ctx.config_carma, rng)
    j = ctx.combate["jogador"]
    jogador = Lutador(
        "Você",
        j["vida"],
        j["velocidade"],
        j["percepcao"],
        [Tecnica.de_fatia(ctx.tecnicas[t]) for t in j["tecnicas"]],
        carma=mesa.carma,
    )
    estado = EstadoRun(jogador, mesa, Votos(ctx.catalogo))
    aplicar_dom(estado, ctx, girar(estado, ctx, "destino").fatias[0])
    return estado


@dataclass
class Registro:
    """Medições opcionais de `jogar_run`, para o simulador."""

    dano_por_luta: list[float] = field(default_factory=list)
    turnos_por_luta: list[int] = field(default_factory=list)
    reacoes: int = 0
    golpes_perigosos_recebidos: int = 0


Altar = Callable[[EstadoRun, "Contexto", random.Random], None]


def jogar_luta(estado: EstadoRun, ctx: Contexto, rng: random.Random, reg: Registro | None) -> bool:
    jogador = estado.jogador
    luta = comecar_luta(estado, ctx, rng)
    vida_antes = jogador.vida
    while not luta.acabou and luta.turnos < ctx.max_turnos:
        if luta.vez is jogador:
            if luta.pode_despertar() and _desperta_agora(luta):
                luta.despertar()
            luta.resolver(escolher_jogador_auto(luta))
        else:
            t = luta.intencao_rival
            acao = luta.turno_rival()
            if reg is not None and t is not None and (t.perigosa or acao.surpresa) and t.dano > 0:
                reg.golpes_perigosos_recebidos += 1
                reg.reacoes += acao.reagiu
    if reg is not None:
        reg.dano_por_luta.append(max(0, vida_antes - jogador.vida) / jogador.vida_max)
        reg.turnos_por_luta.append(luta.turnos)
    if not luta.acabou:  # passou do limite de turnos: conta como derrota
        jogador.vida = 0
    return encerrar_luta(estado, ctx, luta)


def _desperta_agora(luta: Luta) -> bool:
    """O piloto desperta contra um chefe logo de cara, ou quando está mal; senão espera,
    e a beira da morte dispara sozinha."""
    j = luta.jogador
    return (luta.rival.chefe and luta.turnos <= 1) or j.vida < j.vida_max * 0.4


def _substituir_auto(estado: EstadoRun, ctx: Contexto, nova: Fatia) -> None:
    """Troca a pior técnica pela nova, se a nova for de raridade igual ou maior."""
    ordem = ctx.ordem
    pior = min(estado.jogador.tecnicas, key=lambda t: (ordem.index(t.raridade), t.dano))
    if ordem.index(nova.raridade) >= ordem.index(pior.raridade):
        substituir_tecnica(estado, pior, nova)


def jogar_run(
    estado: EstadoRun,
    ctx: Contexto,
    rng: random.Random,
    altar: Altar | None = None,
    reg: Registro | None = None,
    ate: int | None = None,
) -> EstadoRun:
    """Joga da próxima luta até o fim da run (ou até a luta `ate`, inclusive) ou até cair."""
    while not estado.acabou and (ate is None or estado.proxima_luta <= ate):
        if estado.arco is None:
            aplicar_arco(estado, ctx, girar(estado, ctx, "arco").fatias[0])
        if not jogar_luta(estado, ctx, rng, reg) or estado.venceu:
            break
        giro = girar(estado, ctx, "tecnicas")
        nova = max(giro.fatias, key=lambda f: ctx.ordem.index(f.raridade))
        resultado = receber_tecnica(estado, ctx, nova)
        if resultado == "altar" and altar is not None:
            estado.altares += 1
            altar(estado, ctx, rng)
        elif resultado == "cheio":
            _substituir_auto(estado, ctx, nova)
        if vai_ter_reliquia(estado, ctx, rng):
            receber_reliquia(estado, girar(estado, ctx, "reliquias").fatias[0])
    return estado


def medir(
    estado: EstadoRun,
    ctx: Contexto,
    modificar: Callable[[EstadoRun], None],
    amostras: int = 200,
    seed: int = 0,
) -> float:
    """Lutas vencidas a mais (positivo) ou a menos (negativo) no resto da run com `modificar`.

    Mesmas seeds com e sem: a diferença vem da modificação, não do acaso.
    """
    diferenca = 0
    for i in range(amostras):
        base = estado.clonar(random.Random(seed + i))
        jogar_run(base, ctx, random.Random(seed + i))
        variante = estado.clonar(random.Random(seed + i))
        modificar(variante)
        jogar_run(variante, ctx, random.Random(seed + i))
        diferenca += variante.lutas_vencidas - base.lutas_vencidas
    return diferenca / amostras


def aplicar_voto(estado: EstadoRun, ctx: Contexto, voto: Voto) -> None:
    if voto.duracao == "capitulo":  # o capítulo pode ter crescido com a Invasão
        voto.lutas_restantes = estado.tamanho_capitulo - estado.luta_no_capitulo + 1
    else:
        voto.lutas_restantes = lutas_da_duracao(voto.duracao, estado.proxima_luta, 1)
    estado.votos.jurar(voto)
    estado.jogador.aplicar_efeitos(estado.votos.efeitos())


def _com(ctx: Contexto, restricoes, ganhos, duracao: str) -> Callable[[EstadoRun], None]:
    def modificar(e: EstadoRun) -> None:
        aplicar_voto(e, ctx, Voto(list(restricoes), list(ganhos), duracao))

    return modificar


def medir_restricoes(
    estado: EstadoRun, ctx: Contexto, duracao: str = "run", amostras: int = 120, seed: int = 0
) -> dict[str, float]:
    """Sacrifício de cada restrição sozinha contra o build atual, em lutas (≥ 0 = custa)."""
    return {
        r.id: -medir(estado, ctx, _com(ctx, [r], [], duracao), amostras, seed)
        for r in ctx.catalogo.restricoes.values()
    }


def avaliar_restricoes(
    estado: EstadoRun,
    ctx: Contexto,
    restricoes: list,
    individuais: dict[str, float],
    duracao: str = "run",
    amostras: int = 120,
    seed: int = 0,
) -> tuple[float, float]:
    """(pontos, sacrifício medido junto) de um conjunto de restrições."""
    cat = ctx.catalogo
    junto = -medir(estado, ctx, _com(ctx, restricoes, [], duracao), amostras, seed)
    creditado = cat.creditado(junto, [individuais[r.id] for r in restricoes])
    return cat.pontos(creditado, duracao, restricoes), junto


def beneficios_dos_ganhos(
    estado: EstadoRun,
    ctx: Contexto,
    restricoes: list,
    sacrificio: float,
    duracao: str = "run",
    amostras: int = 120,
    seed: int = 0,
) -> dict[str, float]:
    """Quanto cada ganho rende junto destas restrições, em lutas: é o que dá o preço."""
    return {
        g.id: medir(estado, ctx, _com(ctx, restricoes, [g], duracao), amostras, seed) + sacrificio
        for g in ctx.catalogo.ganhos.values()
    }


def custo_dos_ganhos(ctx: Contexto, ganhos: list, beneficio: dict[str, float]) -> float:
    """Pontos que uma compra custa: cada nível de um ganho custa mais que o anterior."""
    cat, total = ctx.catalogo, 0.0
    for gid, n in Counter(g.id for g in ganhos).items():
        g = cat.ganhos[gid]
        total += sum(cat.preco(g, beneficio[gid], k) for k in range(1, n + 1))
    return total


def comprar_ganhos(
    estado: EstadoRun,
    ctx: Contexto,
    restricoes: list,
    pontos: float,
    sacrificio: float,
    duracao: str = "run",
    amostras: int = 120,
    seed: int = 0,
    beneficio: dict[str, float] | None = None,
) -> list:
    """Gasta `pontos` nível a nível, sempre no ganho de maior benefício por nível acessível."""
    cat = ctx.catalogo
    if beneficio is None:
        beneficio = beneficios_dos_ganhos(
            estado, ctx, restricoes, sacrificio, duracao, amostras, seed
        )
    restante, niveis, ganhos = pontos, Counter(), []
    while True:
        opcoes = []
        for g in cat.ganhos.values():
            proximo = niveis[g.id] + 1
            if beneficio[g.id] <= 0 or proximo > g.niveis:
                continue
            preco = cat.preco(g, beneficio[g.id], proximo)
            if preco <= restante:
                opcoes.append((beneficio[g.id] / proximo, preco, g))
        if not opcoes:
            return ganhos
        _, preco, g = max(opcoes, key=lambda o: o[0])
        restante -= preco
        niveis[g.id] += 1
        ganhos.append(g)


def saldo_do_voto(
    estado: EstadoRun, ctx: Contexto, voto: Voto, amostras: int = 120, seed: int = 0
) -> float:
    """Lutas vencidas a mais (ou a menos) com o voto inteiro: a estimativa que o Altar mostra."""
    return medir(estado, ctx, _com(ctx, voto.restricoes, voto.ganhos, voto.duracao), amostras, seed)


def montar_voto_auto(
    estado: EstadoRun,
    ctx: Contexto,
    duracao: str = "run",
    amostras: int = 120,
    seed: int = 0,
    max_restricoes: int = 3,
) -> Voto | None:
    """O piloto automático no Altar.

    Junta restrições (as de maior crédito primeiro) enquanto o voto render mais pontos;
    cada uma credita no máximo o teto, então a combinação é o caminho para mais poder.
    Depois compra ganhos e só jura se o voto inteiro compensa, como um jogador que lê
    a estimativa do Altar.
    """
    cat = ctx.catalogo
    individuais = medir_restricoes(estado, ctx, duracao, amostras, seed)
    candidatas = sorted(
        (r for r in cat.restricoes.values() if individuais[r.id] > 0),
        key=lambda r: min(individuais[r.id], cat.teto_por_restricao),
        reverse=True,
    )
    escolha: list = []
    pontos = sacrificio = 0.0
    for r in candidatas[:max_restricoes]:
        teste = escolha + [r]
        p, junto = avaliar_restricoes(estado, ctx, teste, individuais, duracao, amostras, seed)
        if p <= pontos:
            break
        escolha, pontos, sacrificio = teste, p, junto
    if not escolha:
        return None
    pontos += estado.pontos_guardados  # a força que sobrou de votos anteriores
    beneficio = beneficios_dos_ganhos(estado, ctx, escolha, sacrificio, duracao, amostras, seed)
    ganhos = comprar_ganhos(
        estado, ctx, escolha, pontos, sacrificio, duracao, amostras, seed, beneficio
    )
    voto = Voto(escolha, ganhos, duracao, pontos=pontos, sacrificio=sacrificio)
    voto.sobra = pontos - custo_dos_ganhos(ctx, ganhos, beneficio)
    return voto if saldo_do_voto(estado, ctx, voto, amostras, seed) > 0 else None


def altar_auto(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> None:
    if not estado.votos.pode_jurar():
        return
    voto = montar_voto_auto(estado, ctx, seed=rng.randrange(1 << 30))
    if voto is not None:
        aplicar_voto(estado, ctx, voto)
        estado.pontos_guardados = max(0.0, voto.sobra)

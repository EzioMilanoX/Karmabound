"""Uma run inteira com combate real, que pode continuar de qualquer ponto.

`jogar_run` é usado pelo simulador (runs do zero) e por `medir`, que é como o
Altar dos Votos pesa uma restrição: continua a run do jogador muitas vezes,
com e sem ela, usando as mesmas seeds dos dois lados (números aleatórios
comuns), e devolve a diferença em lutas vencidas.
"""

from __future__ import annotations

import copy
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from karmabound.carma import Carma, ConfigCarma
from karmabound.combate import Luta, Lutador, Tecnica, config_combate, escolher_jogador_auto
from karmabound.mesa import Mesa
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
    proxima_luta: int = 1
    lutas_vencidas: int = 0
    derrotado: bool = False
    transbordos: int = 0
    altares: int = 0

    @property
    def acabou(self) -> bool:
        return self.derrotado

    def clonar(self, rng: random.Random) -> EstadoRun:
        """Cópia independente para simular um futuro (rodas e catálogo são compartilhados)."""
        mesa = Mesa(self.mesa.rodas, self.mesa.raridades, self.mesa.carma.config, rng)
        mesa.carma = Carma(self.mesa.carma.config, self.mesa.carma.valor)
        jogador = copy.copy(self.jogador)
        jogador.tecnicas = list(self.jogador.tecnicas)
        jogador.recargas = dict(self.jogador.recargas)
        jogador.carma = mesa.carma
        votos = Votos(self.votos.catalogo, [copy.copy(v) for v in self.votos.ativos])
        return EstadoRun(
            jogador,
            mesa,
            votos,
            self.proxima_luta,
            self.lutas_vencidas,
            self.derrotado,
            self.transbordos,
            self.altares,
        )


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
    mesa.girar("destino", permitir_despertar=False)
    return estado


def gerar_rival(ctx: Contexto, n_luta: int, rng: random.Random) -> Lutador:
    cfg = ctx.combate["rivais"]
    por_capitulo = cfg["raridades_por_capitulo"]
    capitulo = min((n_luta - 1) // ctx.lutas_por_capitulo, len(por_capitulo) - 1)
    chefe = n_luta % ctx.lutas_por_capitulo == 0
    raridades = set(por_capitulo[capitulo])
    pool = [f for f in ctx.tecnicas.values() if f.raridade in raridades and f.combate]
    n_tec = min(len(pool), cfg["tecnicas_base"] + capitulo * cfg["tecnicas_por_capitulo"])
    vida = cfg["vida_base"] + cfg["vida_por_luta"] * n_luta
    return Lutador(
        nome=f"Rival {n_luta}" + (" (chefe)" if chefe else ""),
        vida_max=round(vida * (cfg["chefe_multiplicador"] if chefe else 1)),
        velocidade=rng.randint(*cfg["velocidade"]),
        percepcao=rng.randint(*cfg["percepcao"]) + (cfg["chefe_percepcao_extra"] if chefe else 0),
        tecnicas=[Tecnica.de_fatia(f) for f in rng.sample(pool, n_tec)],
        chefe=chefe,
    )


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
    rival = gerar_rival(ctx, estado.proxima_luta, rng)
    jogador.nova_luta()
    vida_antes = jogador.vida
    luta = Luta(jogador, rival, ctx.basico, rng, ctx.combate["bonus_surpresa"])
    while not luta.acabou and luta.turnos < ctx.max_turnos:
        if luta.vez is jogador:
            luta.resolver(escolher_jogador_auto(luta))
        else:
            t = luta.intencao_rival
            acao = luta.turno_rival()
            if reg is not None and t is not None and (t.perigosa or acao.surpresa) and t.dano > 0:
                reg.golpes_perigosos_recebidos += 1
                reg.reacoes += acao.reagiu
        if estado.mesa.carma.transbordando:  # Despertar ainda sem efeito: só conta e zera
            estado.transbordos += 1
            estado.mesa.carma.despertar()
    if reg is not None:
        reg.dano_por_luta.append(max(0, vida_antes - jogador.vida) / jogador.vida_max)
        reg.turnos_por_luta.append(luta.turnos)
    return luta.vencedor is jogador


def _equipar(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> None:
    tecnicas = estado.jogador.tecnicas
    if any(t.id == fatia.id for t in tecnicas):
        return
    if len(tecnicas) >= ctx.combate["espacos"]:
        ordem = ctx.ordem
        tecnicas.remove(min(tecnicas, key=lambda t: (ordem.index(t.raridade), t.dano)))
    tecnicas.append(Tecnica.de_fatia(fatia))


def jogar_run(
    estado: EstadoRun,
    ctx: Contexto,
    rng: random.Random,
    altar: Altar | None = None,
    reg: Registro | None = None,
    ate: int | None = None,
) -> EstadoRun:
    """Joga da `proxima_luta` até o fim (ou até `ate`, inclusive) ou até a derrota."""
    ultima = ate or ctx.lutas
    mesa, jogador = estado.mesa, estado.jogador
    while not estado.acabou and estado.proxima_luta <= ultima:
        n = estado.proxima_luta
        if (n - 1) % ctx.lutas_por_capitulo == 0:
            mesa.girar("arco", permitir_despertar=False)
        if not jogar_luta(estado, ctx, rng, reg):
            estado.derrotado = True
            break
        estado.lutas_vencidas += 1
        estado.proxima_luta += 1
        if not jogador.efeitos.sem_cura:
            cura = round(jogador.vida_max * ctx.combate["cura_entre_lutas"])
            jogador.vida = min(jogador.vida_max, jogador.vida + cura)
        if estado.votos.fim_de_luta():
            jogador.aplicar_efeitos(estado.votos.efeitos())
        giro = mesa.girar("tecnicas", permitir_despertar=False)
        nova = max(giro.fatias, key=lambda f: ctx.ordem.index(f.raridade))
        if nova.evento == "altar":
            if altar is not None:
                estado.altares += 1
                altar(estado, ctx, rng)
        elif nova.combate:
            _equipar(estado, ctx, nova)
        if rng.random() < ctx.chance_reliquia:
            mesa.girar("reliquias", permitir_despertar=False)
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
    voto.lutas_restantes = lutas_da_duracao(
        voto.duracao, estado.proxima_luta, ctx.lutas_por_capitulo
    )
    estado.votos.jurar(voto)
    estado.jogador.aplicar_efeitos(estado.votos.efeitos())


def _com(ctx: Contexto, restricoes, ganhos, duracao: str) -> Callable[[EstadoRun], None]:
    def modificar(e: EstadoRun) -> None:
        aplicar_voto(e, ctx, Voto(list(restricoes), list(ganhos), duracao))

    return modificar


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
    Depois compra ganhos nível a nível, sempre o de maior benefício por nível ainda
    acessível com os pontos que sobram.
    """
    cat = ctx.catalogo
    individuais = {
        r.id: -medir(estado, ctx, _com(ctx, [r], [], duracao), amostras, seed)
        for r in cat.restricoes.values()
    }
    candidatas = sorted(
        (r for r in cat.restricoes.values() if individuais[r.id] > 0),
        key=lambda r: min(individuais[r.id], cat.teto_por_restricao),
        reverse=True,
    )
    escolha: list = []
    pontos = sacrificio = 0.0
    for r in candidatas[:max_restricoes]:
        teste = escolha + [r]
        junto = -medir(estado, ctx, _com(ctx, teste, [], duracao), amostras, seed)
        creditado = cat.creditado(junto, [individuais[x.id] for x in teste])
        p = cat.pontos(creditado, duracao, teste)
        if p <= pontos:
            break
        escolha, pontos, sacrificio = teste, p, junto
    if not escolha:
        return None

    beneficio = {
        g.id: medir(estado, ctx, _com(ctx, escolha, [g], duracao), amostras, seed) + sacrificio
        for g in cat.ganhos.values()
    }
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
            break
        _, preco, g = max(opcoes, key=lambda o: o[0])
        restante -= preco
        niveis[g.id] += 1
        ganhos.append(g)
    voto = Voto(escolha, ganhos, duracao, pontos=pontos, sacrificio=sacrificio)
    # Como um jogador que lê a estimativa do Altar: só jura se o voto inteiro compensa.
    saldo = medir(estado, ctx, _com(ctx, escolha, ganhos, duracao), amostras, seed)
    return voto if saldo > 0 else None


def altar_auto(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> None:
    if not estado.votos.pode_jurar():
        return
    voto = montar_voto_auto(estado, ctx, seed=rng.randrange(1 << 30))
    if voto is not None:
        aplicar_voto(estado, ctx, voto)

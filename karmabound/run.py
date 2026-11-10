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
from dataclasses import dataclass, field, replace

from karmabound.aliados import aliado as aliado_de
from karmabound.aliados import nivel_maximo as nivel_maximo_aliado
from karmabound.aliados import sortear_aliado
from karmabound.ascensao import aplicar_ascensao
from karmabound.caminho import (
    Caminho,
    Porta,
    aplicar_opcao,
    carregar_caminho,
    escolher_opcao_auto,
    escolher_porta_auto,
    estilo_do_rival,
    fortalecer_elite,
    fortalecer_nemesis,
    montar_bando,
    oferecer_portas,
)
from karmabound.carma import ConfigCarma
from karmabound.combate import (
    Luta,
    Lutador,
    Tecnica,
    config_combate,
    escolher_alvo_auto,
    escolher_jogador_auto,
    evoluir,
    jurar_luta_auto,
)
from karmabound.efeitos import Efeitos, somar
from karmabound.fusoes import Fusao, carregar_fusoes, fundir
from karmabound.historias import (
    ARCO_ALEM,
    Historia,
    carregar_arcos_da_historia,
    carregar_historias,
)
from karmabound.memes import MEME_CHANCE, memes_disponiveis
from karmabound.mesa import Giro, Mesa
from karmabound.ressonancia import efeitos_de_ressonancia
from karmabound.rodas import (
    Fatia,
    Raridade,
    Roda,
    anime_de,
    carregar_balanceamento,
    carregar_chefes,
    carregar_raridades,
    carregar_rodas,
)
from karmabound.treino import Treino, carregar_treinos, oferecer
from karmabound.treino import aplicar as aplicar_treino
from karmabound.treino import escolher_auto as escolher_treino_auto
from karmabound.viloes import (
    DONO,
    MECANICA_REFLEXO,
    REFLEXO,
    Elenco,
    Vilao,
    carregar_viloes,
    escolher_chefe,
    escolher_tenente,
)
from karmabound.votos import Catalogo, Voto, Votos, carregar_catalogo, lutas_da_duracao
from karmabound.votos_luta import VotoDeLuta, carregar_votos_luta


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
    chefes: tuple[Fatia, ...] = ()  # técnicas-assinatura: cada chefe recebe uma
    votos_luta: tuple[VotoDeLuta, ...] = ()  # a roleta oferece um por luta
    jogo: str = "classico"  # o modo de jogo (JOGOS)
    anime: str = ""  # no Mundo de um anime: de qual
    todos_chefes: bool = False  # Desfile de chefes: toda luta é contra um chefe
    treinos: tuple[Treino, ...] = ()  # depois de cada vitória, escolhe 1 de `oferta_treino`
    oferta_treino: int = 3
    caminho: Caminho | None = None  # as portas entre as lutas (None: luta atrás de luta)
    # o Legado de quem joga (o piloto e o simulador jogam sem): ver legado.py
    maestria: dict[str, int] = field(default_factory=dict)  # técnica -> evoluções de saída
    nemesis: dict | None = None  # quem te matou numa run passada, à espera
    fusoes: tuple[Fusao, ...] = ()  # técnicas que nascem de requisitos (fusoes.py)
    ascensao: int = 0  # o degrau da Ascensão (ascensao.py): já aplicado nos dados
    # Leva 5: os vilões, o modo História e o capítulo secreto
    elenco: Elenco | None = None  # rivais e chefes com nome (viloes.py); None: anônimos
    animes: frozenset[str] | None = None  # as obras abertas pelo Legado (None: todas)
    historia: Historia | None = None  # a campanha do modo História
    arcos_fixos: dict[str, Fatia] = field(default_factory=dict)  # Arcos fora da roda
    alem: bool = False  # o capítulo secreto já está aberto (Legado): o Dono convida
    assinaturas: dict[str, Fatia] = field(default_factory=dict)  # todas as de chefe, por id
    memes: tuple[Vilao, ...] = ()  # os chefes secretos ligados e com imagem (memes.py)

    @property
    def lutas(self) -> int:
        """Lutas de uma run sem Invasão."""
        return self.capitulos * self.lutas_por_capitulo

    def restantes(self, proxima_luta: int) -> int:
        """Lutas que ainda faltam (na Torre sem fim, um horizonte de 12)."""
        if self.jogo == "torre":
            return HORIZONTE_TORRE
        return max(1, self.lutas - proxima_luta + 1)

    @property
    def ordem(self) -> list[str]:
        return [r.id for r in self.raridades]

    @property
    def tecnicas(self) -> dict[str, Fatia]:
        return {f.id: f for f in self.rodas["tecnicas"].fatias}

    @classmethod
    def padrao(
        cls,
        dificuldade: str | None = None,
        balanceamento: dict | None = None,
        jogo: str = "classico",
        anime: str = "",
        caminho: bool = True,
        abertos: frozenset[str] | None = None,
        maestria: dict[str, int] | None = None,
        nemesis: dict | None = None,
        ascensao: int = 0,
        historia: str = "",
        alem: bool = False,
        viloes: bool = True,
        desbloqueios: frozenset[str] = frozenset(),
        memes: bool = False,
    ) -> Contexto:
        """`abertos`: os animes que o Legado já abriu (None: todos). `maestria` e
        `nemesis`: do Legado de quem joga. `caminho=False`: luta atrás de luta.
        `ascensao`: o degrau da Ascensão (0: nenhum). `historia`: a campanha do modo
        História. `alem`: o capítulo secreto está aberto. `viloes=False`: rivais e
        chefes anônimos, como antes da Leva 5 (para medir). `desbloqueios`: as
        recompensas de voto já liberadas (pacto.py); as outras ficam fora das rodas."""
        if jogo not in JOGOS:
            raise ValueError(f"modo de jogo '{jogo}' não existe (use: {', '.join(JOGOS)})")
        bal = balanceamento or carregar_balanceamento()
        raridades = carregar_raridades(bal)
        cfg = config_combate(bal, dificuldade)
        rodas, chefes = carregar_rodas(raridades), carregar_chefes()

        def liberada(f: Fatia) -> bool:  # as recompensas de voto só entram depois de liberadas
            return "voto" not in f.tags or f.id in desbloqueios

        rodas = {
            rid: replace(roda, fatias=tuple(f for f in roda.fatias if liberada(f)))
            for rid, roda in rodas.items()
        }
        if abertos is not None:  # a roda se abre aos poucos: só os animes já abertos
            fixas = set(cfg["jogador"]["tecnicas"])
            fixas |= {f.inicial for f in rodas["linhagem"].fatias if f.inicial}
            rodas = filtrar_animes(rodas, abertos, frozenset(fixas))
        forma: dict = {}
        if jogo == "torre":
            forma = {"capitulos": CAPITULOS_TORRE}
        elif jogo == "chefes":
            forma = {"capitulos": 3, "lutas_por_capitulo": 2, "todos_chefes": True}
        campanha = None
        if jogo == "historia":
            campanha = carregar_historias().get(historia or ORIGINAL)
            if campanha is None:
                raise ValueError(f"a campanha '{historia}' não existe")
            anime = campanha.anime
        elif historia:
            raise ValueError("`historia` só vale no modo História")
        assinaturas = {c.id: c for c in chefes}  # todas: um vilão leva as dele em qualquer modo
        if jogo == "historia" and anime:  # a campanha de um anime: só aquele mundo
            if not anime:
                raise ValueError("o Mundo de um anime precisa do anime")
            fixas = set(cfg["jogador"]["tecnicas"])
            fixas |= {f.inicial for f in rodas["linhagem"].fatias if f.inicial}
            rodas = filtrar_anime(rodas, anime, frozenset(fixas), convidados=False)
            chefes = tuple(c for c in chefes if anime_de(c.origem) == anime) or chefes
        treinos, oferta = carregar_treinos()
        elenco = carregar_viloes() if viloes else None
        ctx = cls(
            rodas=rodas,
            raridades=raridades,
            config_carma=ConfigCarma.de_dict(bal["carma"]),
            combate=cfg,
            catalogo=carregar_catalogo(),
            basico=Tecnica.de_dict(cfg["golpe_basico"]),
            chefes=chefes,
            votos_luta=carregar_votos_luta(),
            jogo=jogo,
            anime=anime if jogo in ("anime", "historia") else "",
            treinos=treinos,
            oferta_treino=oferta,
            caminho=carregar_caminho() if caminho and jogo != "chefes" else None,
            maestria=dict(maestria or {}),
            nemesis=nemesis,
            fusoes=carregar_fusoes(),
            elenco=elenco,
            assinaturas=assinaturas,
            memes=memes_disponiveis(elenco) if memes and elenco and jogo != "historia" else (),
            animes=abertos,
            historia=campanha,
            arcos_fixos=carregar_arcos_da_historia(),
            alem=alem and jogo in ("classico", "historia") and not (campanha and campanha.anime),
            **forma,
        )
        return aplicar_ascensao(ctx, ascensao)


# ----------------------------------------------------------------------- modos de jogo

JOGOS = {
    "classico": "Clássico",
    "historia": "História",
    "torre": "Torre sem fim",
    "chefes": "Desfile de chefes",
}
DESCRICAO_JOGO = {
    "classico": "3 capítulos, 12 lutas",
    "historia": "capítulos, cenas e chefes fixos",
    "torre": "até onde você sobe?",
    "chefes": "6 lutas, só chefes",
}
MECANICAS_ANTIGAS = frozenset(  # as mecânicas de chefe de antes dos vilões finais
    "petalas armadura repulsao intangivel preco carregar contrato balanca regenera adaptar "
    "ilusao".split()
)
ORIGINAL = "torneio_da_roda"  # a campanha principal do modo História
TORRE_DONO_CADA = 5  # na Torre sem fim, o Dono da Roda guarda cada 5º capítulo
CAPITULOS_TORRE = 10_000
HORIZONTE_TORRE = 12  # o Altar e o piloto projetam a Torre como uma run de 12 lutas
MINIMO_ANIME = 10  # técnicas de um anime para ele ter o próprio Mundo


def filtrar_anime(
    rodas: dict[str, Roda], anime: str, manter=frozenset(), convidados: bool = True
) -> dict[str, Roda]:
    """As rodas só com o anime. `convidados`: uma raridade que ele não tem numa roda
    volta inteira (sem eles, a História: todo anime tem todas as raridades)."""
    return filtrar_animes(rodas, frozenset({anime}), manter, convidados)


def filtrar_animes(
    rodas: dict[str, Roda], animes: frozenset[str], manter=frozenset(), convidados: bool = True
) -> dict[str, Roda]:
    """As rodas só com estes animes (e as fatias de `manter`). Uma raridade que eles não
    têm numa roda volta inteira, para nenhuma roda ficar sem o que sortear."""
    novas = {}
    for rid, roda in rodas.items():
        do_anime = [f for f in roda.fatias if anime_de(f.origem) in animes or f.id in manter]
        tem = {f.raridade for f in do_anime}
        de_fora = [f for f in roda.fatias if f.raridade not in tem] if convidados else []
        if not do_anime:  # sem nada daquele mundo (o Arco, que a História fixa): fica
            de_fora = list(roda.fatias)
        novas[rid] = replace(roda, fatias=tuple(do_anime + de_fora))
    return novas


def animes_jogaveis(rodas: dict[str, Roda]) -> list[str]:
    """Os animes com técnicas suficientes para um Mundo próprio (o mais rico primeiro)."""
    conta = Counter(anime_de(f.origem) for f in rodas["tecnicas"].fatias)
    conta.pop("", None)
    return sorted((a for a, n in conta.items() if n >= MINIMO_ANIME), key=lambda a: -conta[a])


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
    linhagem: Fatia | None = None
    altar_pendente: bool = False  # o capítulo acabou: o Altar dos Votos abre antes do próximo
    votos_de_luta: int = 0  # votos de luta jurados na run
    promessas_cumpridas: int = 0
    arco: Fatia | None = None  # None no começo de cada capítulo: falta girar o Arco
    reliquias: list[Fatia] = field(default_factory=list)
    fragmentos: Counter = field(default_factory=Counter)
    # o caminho
    porta: Porta | None = None  # a porta escolhida para a próxima luta
    reliquia_garantida: bool = False  # venceu uma elite ou a Nêmesis
    nemesis_vista: bool = False  # a Nêmesis já apareceu nesta run
    vingou: bool = False  # venceu a Nêmesis
    bandos: int = 0  # bandos vencidos
    elites: int = 0  # elites vencidas
    encruzilhadas: int = 0
    proximas_portas: tuple[Porta, ...] = ()  # as portas do passo seguinte (vazio: o chefe)
    # fusões (fusoes.py)
    despertares_ids: list[str] = field(default_factory=list)  # os Despertares desta run
    fusoes_nascidas: list[str] = field(default_factory=list)  # cada fusão nasce uma vez
    # o aliado (aliados.py): um por run; o novo substitui o antigo
    aliado: str = ""  # o id ("" = sem aliado)
    aliado_nivel: int = 0  # começa no 1 e sobe a cada luta vencida
    # Leva 5
    viloes_vistos: list[str] = field(default_factory=list)  # quem já apareceu nesta run
    alem: bool = False  # aceitou o convite: o capítulo secreto, além da Roda
    final: str = ""  # o final escolhido no modo História (quebrar | tomar)
    dono_vencido: bool = False  # venceu o Dono da Roda nesta run
    vilao_forcado: str = ""  # o Laboratório (livre.py): o rival escolhido a dedo

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
        clone.despertares_ids = list(self.despertares_ids)
        clone.fusoes_nascidas = list(self.fusoes_nascidas)
        clone.viloes_vistos = list(self.viloes_vistos)
        return clone


# ----------------------------------------------------------------------- efeitos


def efeitos_do_estado(estado: EstadoRun) -> Efeitos:
    """Votos + Dom + Relíquias + Ressonância + a parte do Arco que é do jogador."""
    partes = [estado.votos.efeitos(), *efeitos_de_ressonancia(estado)]
    if estado.linhagem is not None and estado.linhagem.efeito:
        partes.append(Efeitos.de_dict(estado.linhagem.efeito))
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
    mais = estado.regra.get("opcoes_tecnica", 0) if roda == "tecnicas" else 0
    rodas = estado.mesa.rodas
    if mais:  # o Arco oferece uma técnica a mais na escolha (só neste giro)
        estado.mesa.rodas = {**rodas, roda: replace(rodas[roda], opcoes=rodas[roda].opcoes + mais)}
    try:
        if estado.divino_pendente:
            estado.divino_pendente -= 1
            return estado.mesa.girar(roda, forcar_despertar=True)
        return estado.mesa.girar(roda, permitir_despertar=False)
    finally:
        estado.mesa.rodas = rodas


# ----------------------------------------------------------------------- passos


def criar_tecnica(ctx: Contexto, fatia: Fatia) -> Tecnica:
    """A técnica que chega à mão: já evoluída pela Maestria de quem joga."""
    t = Tecnica.de_fatia(fatia)
    for _ in range(ctx.maestria.get(fatia.id, 0)):
        t = evoluir(t)
    return t


def tecnicas_iniciais(ctx: Contexto) -> list[Tecnica]:
    return [criar_tecnica(ctx, ctx.tecnicas[t]) for t in ctx.combate["jogador"]["tecnicas"]]


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


def aplicar_linhagem(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> None:
    """A Linhagem: o sangue de onde você vem. Efeitos, às vezes uma técnica própria
    (que não ocupa espaço) e às vezes uma técnica que já começa num espaço."""
    estado.linhagem = fatia
    j = estado.jogador
    j.tecnica_linhagem = None
    if fatia.tecnica:
        j.tecnica_linhagem = Tecnica(
            id=fatia.id, nome=fatia.nome, raridade=fatia.raridade, **fatia.tecnica
        )
    if fatia.inicial and fatia.inicial in ctx.tecnicas:
        if all(t.id != fatia.inicial for t in j.tecnicas):
            j.tecnicas.append(criar_tecnica(ctx, ctx.tecnicas[fatia.inicial]))
    atualizar_efeitos(estado)
    j.vida = j.vida_max  # a run começa com a vida cheia da Linhagem


def arco_fixo(estado: EstadoRun, ctx: Contexto) -> Fatia | None:
    """O Arco que este capítulo não sorteia: o do capítulo secreto e os da História."""
    if estado.alem and estado.capitulo > ctx.capitulos:
        return ctx.arcos_fixos.get(ARCO_ALEM)
    if ctx.historia is not None:
        cap = ctx.historia.capitulo(estado.capitulo)
        if cap is not None:
            na_roda = {f.id: f for f in ctx.rodas["arco"].fatias}
            return ctx.arcos_fixos.get(cap.arco) or na_roda.get(cap.arco)
    return None


def girar_arco(estado: EstadoRun, ctx: Contexto) -> Giro:
    """O giro do Arco: o fixo cai sem sorteio (e sem mexer no Carma)."""
    fixo = arco_fixo(estado, ctx)
    if fixo is not None:
        return Giro(ctx.rodas["arco"], [fixo])
    return girar(estado, ctx, "arco")


def aplicar_arco(estado: EstadoRun, ctx: Contexto, fatia: Fatia) -> None:
    estado.arco = fatia
    estado.tamanho_capitulo = ctx.lutas_por_capitulo + estado.regra.get("luta_extra", 0)
    atualizar_efeitos(estado)


def vida_do_rival(ctx: Contexto, n_luta: int) -> float:
    cfg = ctx.combate["rivais"]
    return cfg["vida_base"] + cfg["vida_por_luta"] * n_luta


def _pool_do_rival(ctx: Contexto, capitulo: int) -> tuple[list[Fatia], int]:
    """As técnicas que um rival deste capítulo pode ter, e quantas ele leva."""
    cfg = ctx.combate["rivais"]
    por_capitulo = cfg["raridades_por_capitulo"]
    indice = min(capitulo - 1, len(por_capitulo) - 1)
    raridades = set(por_capitulo[indice])
    pool = [f for f in ctx.tecnicas.values() if f.raridade in raridades and f.combate]
    n_tec = min(len(pool), cfg["tecnicas_base"] + indice * cfg["tecnicas_por_capitulo"])
    return pool, n_tec


def _ultimo_capitulo(estado: EstadoRun, ctx: Contexto) -> bool:
    """O capítulo do chefe fixo (o Dono, ou o final do anime)."""
    if ctx.jogo == "torre":
        return estado.capitulo % TORRE_DONO_CADA == 0
    if ctx.todos_chefes:  # Desfile: só a última luta de todas
        return estado.capitulo >= ctx.capitulos and estado.chefe
    return estado.capitulo >= ctx.capitulos


def vilao_chefe(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> Vilao | None:
    """O chefe com nome deste capítulo (None: sem elenco, o chefe é anônimo)."""
    el = ctx.elenco
    if el is None:
        return None
    if estado.alem and estado.capitulo > ctx.capitulos:
        return el.get(REFLEXO)
    if ctx.historia is not None:
        cap = ctx.historia.capitulo(estado.capitulo)
        if cap is not None and el.get(cap.chefe) is not None:
            return el[cap.chefe]
    if ctx.memes and not _ultimo_capitulo(estado, ctx) and rng.random() < MEME_CHANCE:
        return rng.choice(ctx.memes)  # um chefe secreto toma o lugar
    return escolher_chefe(
        el,
        estado.capitulo,
        _ultimo_capitulo(estado, ctx),
        rng,
        animes=ctx.animes,
        anime=ctx.anime,
        vistos=estado.viloes_vistos,
    )


def vilao_rival(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> Vilao | None:
    """O rival com nome de uma luta comum (na História, os da cena do capítulo)."""
    el = ctx.elenco
    if el is None:
        return None
    lista: tuple[str, ...] = ()
    if ctx.historia is not None:
        cap = ctx.historia.capitulo(estado.capitulo)
        lista = cap.rivais if cap is not None else ()
    return escolher_tenente(
        el,
        min(estado.capitulo, 3),
        rng,
        animes=ctx.animes,
        anime=ctx.anime,
        vistos=estado.viloes_vistos,
        lista=lista,
    )


def _vestir(rival: Lutador, vilao: Vilao | None, estado: EstadoRun, padrao: str) -> None:
    """O rival ganha o nome, a figura e a cor do vilão (e entra nos vistos da run)."""
    if vilao is None:
        rival.estilo = padrao
        return
    rival.nome = rival.titulo = vilao.nome
    rival.estilo = vilao.estilo or padrao
    rival.vilao, rival.cor = vilao.id, vilao.cor
    estado.viloes_vistos.append(vilao.id)


def gerar_oponentes(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> list[Lutador]:
    """Quem espera atrás da porta escolhida: um rival, um bando, a elite ou a Nêmesis.
    Luta de chefe (ou sem caminho): um rival, como sempre."""
    chefe = estado.chefe or ctx.todos_chefes
    porta, cam = estado.porta, ctx.caminho
    n, cap = estado.proxima_luta, estado.capitulo
    forcado = ctx.elenco.get(estado.vilao_forcado) if estado.vilao_forcado and ctx.elenco else None
    if forcado is not None:  # o Laboratório: quem você escolheu (tenente não é chefe)
        rival = gerar_rival(ctx, n, rng, cap, forcado.papel != "tenente", vilao=forcado)
        _vestir(rival, forcado, estado, estilo_do_rival(n, cap, rival.chefe))
        return [rival]
    if chefe or porta is None or cam is None or porta.tipo == "rival":
        vilao = vilao_chefe(estado, ctx, rng) if chefe else vilao_rival(estado, ctx, rng)
        rival = gerar_rival(ctx, n, rng, cap, chefe, vilao=vilao)
        _vestir(rival, vilao, estado, estilo_do_rival(n, cap, rival.chefe))
        return [rival]
    if porta.papeis:  # um bando (a elite às vezes vem com Comandante)
        cfg = ctx.combate["rivais"]
        pool, n_tec = _pool_do_rival(ctx, cap)
        n_tec = max(1, n_tec - cam.bando["tecnicas_menos"])
        tecnicas = [[Tecnica.de_fatia(f) for f in rng.sample(pool, n_tec)] for _ in porta.papeis]
        bando = montar_bando(
            cam,
            porta.papeis,
            vida_do_rival(ctx, n),
            tecnicas,
            rng,
            cap,
            tuple(cfg["velocidade"]),
            tuple(cfg["percepcao"]),
        )
        if porta.tipo == "elite":
            for r in bando:  # os afixos: só o Comandante (o bando já é a ameaça)
                sorte = rng if r.papel == "comandante" else None
                fortalecer_elite(cam, r, bando=True, rng=sorte, capitulo=cap)
        return bando
    if porta.tipo == "elite":
        vilao = vilao_rival(estado, ctx, rng)
        mais = cam.elite["tecnicas_mais"]
        rival = gerar_rival(ctx, n, rng, cap, False, mais_tecnicas=mais, vilao=vilao)
        fortalecer_elite(cam, rival, rng=rng, capitulo=cap)
        rival.nome = rival.titulo = f"Elite {n}"
        _vestir(rival, vilao, estado, estilo_do_rival(n, cap, False))
        return [rival]
    if porta.tipo == "nemesis" and ctx.nemesis is not None:
        rival = gerar_rival(ctx, n, rng, cap, False)
        rival.estilo = estilo_do_rival(n, cap, False)
        tid = ctx.nemesis.get("tecnica", "")
        fatia = ctx.tecnicas.get(tid) or next((c for c in ctx.chefes if c.id == tid), None)
        golpe = Tecnica.de_fatia(fatia) if fatia is not None and fatia.combate else None
        fortalecer_nemesis(cam, rival, ctx.nemesis, golpe)
        return [rival]
    vilao = vilao_rival(estado, ctx, rng)
    rival = gerar_rival(ctx, n, rng, cap, False, vilao=vilao)
    _vestir(rival, vilao, estado, estilo_do_rival(n, cap, False))
    return [rival]


def gerar_rival(
    ctx: Contexto,
    n_luta: int,
    rng: random.Random,
    capitulo: int | None = None,
    chefe: bool | None = None,
    mais_tecnicas: int = 0,
    vilao: Vilao | None = None,
) -> Lutador:
    """Um rival da luta `n_luta`. Com `vilao`, ele leva primeiro as técnicas do vilão que
    cabem nas raridades do capítulo, e as assinaturas dele (se for chefe)."""
    cfg = ctx.combate["rivais"]
    if capitulo is None:
        capitulo = (n_luta - 1) // ctx.lutas_por_capitulo + 1
    if chefe is None:
        chefe = n_luta % ctx.lutas_por_capitulo == 0
    pool, n_tec = _pool_do_rival(ctx, capitulo)
    mais_tecnicas += cfg.get("chefe_tecnicas_extra", 0) if chefe else 0  # Ascensão
    n_tec = min(len(pool), n_tec + mais_tecnicas)
    vida = vida_do_rival(ctx, n_luta)
    if vilao is None:
        fatias = rng.sample(pool, n_tec)
    else:
        no_pool = {f.id for f in pool}
        dele = [ctx.tecnicas[t] for t in vilao.tecnicas if t in no_pool][:n_tec]
        resto = [f for f in pool if f not in dele]
        fatias = dele + rng.sample(resto, min(len(resto), n_tec - len(dele)))
    tecnicas = [Tecnica.de_fatia(f) for f in fatias]
    # as técnicas-assinatura do chefe (e a mecânica que vem com a primeira que tiver uma)
    assinaturas = _assinaturas(ctx, vilao, chefe, rng)
    tecnicas += [Tecnica.de_fatia(a) for a in assinaturas]
    # a mecânica: a do vilão final (a que só ele tem) vem antes das que já existiam
    novas = [a for a in assinaturas if a.mecanica and a.mecanica not in MECANICAS_ANTIGAS]
    assinatura = next(iter(novas), None) or next((a for a in assinaturas if a.mecanica), None)
    assinatura = assinatura or (assinaturas[0] if assinaturas else None)
    mecanica = assinatura.mecanica if assinatura is not None else ""
    if vilao is not None and vilao.papel == "secreto":
        mecanica = MECANICA_REFLEXO  # ele copia as suas técnicas quando a luta começa
    return Lutador(
        nome=f"Rival {n_luta}" + (" (chefe)" if chefe else ""),
        vida_max=round(vida * (cfg["chefe_multiplicador"] if chefe else 1)),
        velocidade=rng.randint(*cfg["velocidade"]),
        percepcao=rng.randint(*cfg["percepcao"]) + (cfg["chefe_percepcao_extra"] if chefe else 0),
        tecnicas=tecnicas,
        chefe=chefe,
        mecanica=mecanica,
        assinatura=assinatura.id if assinatura is not None else "",
    )


def _assinaturas(
    ctx: Contexto, vilao: Vilao | None, chefe: bool, rng: random.Random
) -> list[Fatia]:
    """As técnicas-assinatura de um chefe: as do vilão; sem vilão, uma sorteada."""
    if not chefe:
        return []
    if vilao is not None and (vilao.assinaturas or vilao.papel == "secreto"):
        return [ctx.assinaturas[a] for a in vilao.assinaturas if a in ctx.assinaturas]
    return [rng.choice(ctx.chefes)] if ctx.chefes else []


def comecar_luta(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> Luta:
    rivais = gerar_oponentes(estado, ctx, rng)
    regra = estado.regra
    jogador = estado.jogador
    jogador.nova_luta()
    for rival in rivais:
        mult = regra.get("vida_rival_mult", 1.0) * (
            regra.get("chefe_mult", 1.0) if rival.chefe else 1.0
        )
        if mult != 1.0:
            rival.vida_max = rival.base_vida_max = rival.vida = round(rival.vida_max * mult)
        if regra.get("dano_todos"):  # Lua de Sangue: vale para os dois lados
            rival.dano_extra = regra["dano_todos"]
        rival.percepcao += regra.get("percepcao_rivais", 0)  # Hueco Mundo
        if rival.chefe and regra.get("chefe_mult"):  # Arco do Juízo
            rival.dano_mult = regra["chefe_mult"]
        if regra.get("dano_rivais_mult"):
            rival.dano_mult *= regra["dano_rivais_mult"]
        if regra.get("velocidade_rivais") or regra.get("sutileza_rivais"):
            rival.aplicar_efeitos(
                somar(
                    [
                        rival.efeitos,
                        Efeitos(
                            velocidade=regra.get("velocidade_rivais", 0),
                            sutileza=regra.get("sutileza_rivais", 0),
                        ),
                    ]
                )
            )
        rival.guarda_mult = regra.get("guarda_mult", 1.0)
        if rival.mecanica == MECANICA_REFLEXO:  # o Reflexo: as suas técnicas, na mão dele
            rival.tecnicas = [*jogador.tecnicas, *rival.tecnicas]
    if regra.get("sangria_todos"):  # todos sangram, o capítulo inteiro
        for lutador in (jogador, *rivais):
            lutador.sangue, lutador.sangue_turnos = regra["sangria_todos"], ctx.max_turnos
    if regra.get("dano_todos"):
        jogador.dano_extra = regra["dano_todos"]
    if regra.get("dano_por_vitoria"):  # Torre Celestial: sobe um andar a cada vitória
        jogador.dano_extra += regra["dano_por_vitoria"] * (estado.luta_no_capitulo - 1)

    def ao_despertar():
        estado.despertares += 1
        estado.transbordos += 1
        estado.divino_pendente += 1
        fatia = estado.mesa.girar("despertar").fatias[0]
        estado.despertares_ids.append(fatia.id)  # as fusões pedem um Despertar
        return fatia

    def ao_eclipse():  # o preço do Ovo do Eclipse: o Dom
        estado.dom = None
        jogador.tecnica_dom = None
        atualizar_efeitos(estado)

    voto = rng.choice(ctx.votos_luta) if ctx.votos_luta else None
    return Luta(
        jogador,
        rivais if len(rivais) > 1 else rivais[0],
        ctx.basico,
        rng,
        ctx.combate["bonus_surpresa"],
        ao_despertar=ao_despertar,
        espacos=espacos(estado, ctx),
        ao_eclipse=ao_eclipse,
        voto_luta=voto,
        aliado=aliado_de(estado.aliado),  # o companheiro luta do seu lado
        aliado_nivel=estado.aliado_nivel,
    )


def encerrar_luta(estado: EstadoRun, ctx: Contexto, luta: Luta) -> bool:
    """Fecha a luta: contadores, recompensas, cura, votos e o avanço de capítulo."""
    jogador, carma = estado.jogador, estado.mesa.carma
    luta.encerrar()
    estado.votos_de_luta += luta.voto_jurado
    estado.promessas_cumpridas += luta.promessa_resultado == "cumprida"
    porta, estado.porta = estado.porta, None
    if luta.vencedor is not jogador:
        estado.derrotado = True
        return False
    estado.lutas_vencidas += 1
    estado.proxima_luta += 1
    if porta is not None and not luta.rival.chefe:
        estado.bandos += len(luta.rivais) > 1
        if porta.tipo in ("elite", "nemesis"):
            estado.elites += porta.tipo == "elite"
            estado.reliquia_garantida = True
        if porta.tipo == "nemesis" and ctx.caminho is not None:
            estado.vingou = True  # a Nêmesis caiu: Carma e um Despertar guardado
            carma.ganhar(ctx.caminho.nemesis["carma"])
            carma.guardados += 1
    if estado.aliado:  # o aliado cresce a cada luta vencida
        estado.aliado_nivel = min(nivel_maximo_aliado(), estado.aliado_nivel + 1)
    elif porta is not None and porta.tipo == "elite" and ctx.caminho is not None:
        if luta.rng.random() < ctx.caminho.elite.get("aliado", 0):
            ganhar_aliado(estado, luta.rng)  # às vezes, quem a elite prendia te segue
    if jogador.efeitos.vida_por_vitoria:  # Manto de Peso: o treino acumula
        v, n = jogador.efeitos.vida_por_vitoria, estado.lutas_vencidas
        ganho = int(n * v) - int((n - 1) * v)
        jogador.base_vida_max += ganho
        jogador.vida += ganho
    if jogador.efeitos.carma_por_vitoria:
        carma.ganhar(jogador.efeitos.carma_por_vitoria)  # Rosário de Ossos
    if estado.regra.get("carma_por_vitoria"):
        carma.ganhar(estado.regra["carma_por_vitoria"])
    if luta.rival.vilao == DONO:
        estado.dono_vencido = True
    if luta.rival.chefe and estado.regra.get("carma_cheio_chefe"):
        carma.ganhar(carma.config.maximo)  # Arco do Juízo
    if luta.rival.chefe and estado.regra.get("despertar_chefe"):
        carma.guardados += 1  # Torneio do Poder: um Despertar guardado
    if not jogador.efeitos.sem_cura:
        fracao = estado.regra.get("cura_entre_lutas", ctx.combate["cura_entre_lutas"])
        fracao += estado.regra.get("cura_por_vitoria", 0)
        fracao *= jogador.efeitos.cura_mult
        jogador.vida = min(jogador.vida_max, jogador.vida + round(jogador.vida_max * fracao))
    estado.votos.fim_de_luta()
    if estado.luta_no_capitulo >= estado.tamanho_capitulo:
        estado.capitulo += 1
        estado.luta_no_capitulo = 1
        estado.arco = None
        estado.tamanho_capitulo = ctx.lutas_por_capitulo
        estado.venceu = estado.capitulo > ctx.capitulos + estado.alem
        # os votos agora são jurados no menu, antes da run (pacto.py): sem Altar no meio
    else:
        estado.luta_no_capitulo += 1
    atualizar_efeitos(estado)
    return True


def oferecer_treinos(
    ctx: Contexto, rng: random.Random, estado: EstadoRun | None = None
) -> tuple[Treino, ...]:
    """Os treinos depois de uma vitória (o Arco pode oferecer um a mais)."""
    extra = estado.regra.get("treino_extra", 0) if estado is not None else 0
    return oferecer(ctx.treinos, ctx.oferta_treino + extra, rng)


def aceitar_convite(estado: EstadoRun, ctx: Contexto) -> None:
    """Depois do Dono: em vez de terminar, a run segue para além da Roda (capítulo 4)."""
    if not ctx.alem or estado.alem or not estado.venceu:
        raise RuntimeError("o convite para além da Roda não está aberto")
    estado.alem, estado.venceu = True, False


def convite_aberto(estado: EstadoRun, ctx: Contexto) -> bool:
    """Venceu o Dono com o capítulo secreto aberto: a Roda range."""
    return ctx.alem and estado.venceu and estado.dono_vencido and not estado.alem


def tem_caminho(estado: EstadoRun, ctx: Contexto) -> bool:
    """A próxima luta pede a escolha de uma porta? (chefe não: ele espera no fim)."""
    return ctx.caminho is not None and not (estado.chefe or ctx.todos_chefes)


def oferecer_caminho(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> tuple[Porta, ...]:
    """As portas de agora (as que o mapa já mostrava, se havia) e, se o passo seguinte do
    capítulo não é o chefe, já as dele em `estado.proximas_portas` (vazio: vem o chefe)."""
    portas = estado.proximas_portas or _sortear_portas(estado, ctx, rng, estado.proxima_luta)
    estado.proximas_portas = ()
    if estado.luta_no_capitulo + 1 < estado.tamanho_capitulo:  # o seguinte não é o chefe
        estado.proximas_portas = _sortear_portas(estado, ctx, rng, estado.proxima_luta + 1)
    return portas


def _sortear_portas(
    estado: EstadoRun, ctx: Contexto, rng: random.Random, n_luta: int
) -> tuple[Porta, ...]:
    nemesis = ctx.nemesis is not None and not estado.nemesis_vista
    mult = estado.regra.get("portas")
    portas = oferecer_portas(ctx.caminho, rng, n_luta, estado.capitulo, nemesis, mult)
    if any(p.tipo == "nemesis" for p in portas):
        estado.nemesis_vista = True  # ela aparece uma vez por run: recusar também conta
    return portas


def escolher_porta(estado: EstadoRun, porta: Porta) -> None:
    estado.porta = porta


def atravessar_encruzilhada(estado: EstadoRun, op) -> str:
    """Aplica a escolha da encruzilhada e avança o caminho (sem luta). Devolve o giro que
    a escolha pede ("tecnicas", "reliquias" ou "")."""
    aplicar_opcao(op, estado.jogador)
    if getattr(op, "aliado", False):
        ganhar_aliado(estado, estado.mesa.rng)  # o Lutador Ferido te segue
    estado.porta = None
    estado.encruzilhadas += 1
    estado.luta_no_capitulo += 1  # o tempo passa: o próximo rival é o da luta seguinte
    estado.proxima_luta += 1
    return op.giro


def ganhar_aliado(estado: EstadoRun, rng: random.Random) -> str:
    """Um aliado sorteado passa a lutar do seu lado, no nível 1 (substitui o antigo)."""
    estado.aliado, estado.aliado_nivel = sortear_aliado(rng, estado.aliado).id, 1
    return estado.aliado


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
        tecnicas.append(criar_tecnica(ctx, fatia))
        atualizar_efeitos(estado)  # a Ressonância conta as técnicas equipadas
        return "equipada"
    return "cheio"


def substituir_tecnica(
    estado: EstadoRun, sai: Tecnica | None, entra: Fatia, ctx: Contexto | None = None
) -> None:
    if sai is not None:
        estado.jogador.tecnicas.remove(sai)
        nova = criar_tecnica(ctx, entra) if ctx is not None else Tecnica.de_fatia(entra)
        estado.jogador.tecnicas.append(nova)
        atualizar_efeitos(estado)  # a Ressonância conta as técnicas equipadas


def receber_reliquia(estado: EstadoRun, fatia: Fatia) -> None:
    estado.reliquias.append(fatia)
    atualizar_efeitos(estado)


def vai_ter_reliquia(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> bool:
    if estado.reliquia_garantida:  # a elite e a Nêmesis pagam com Relíquia
        estado.reliquia_garantida = False
        return True
    sorte = rng.random()
    chance = ctx.chance_reliquia + estado.jogador.efeitos.chance_reliquia
    return estado.regra.get("reliquia_garantida", False) or sorte < chance


# ----------------------------------------------------------------------- piloto automático


def nova_run(ctx: Contexto, rng: random.Random) -> EstadoRun:
    mesa = Mesa(ctx.rodas, ctx.raridades, ctx.config_carma, rng)
    j = ctx.combate["jogador"]
    jogador = Lutador(
        "Você",
        j["vida"],
        j["velocidade"],
        j["percepcao"],
        tecnicas_iniciais(ctx),
        carma=mesa.carma,
    )
    estado = EstadoRun(jogador, mesa, Votos(ctx.catalogo))
    aplicar_linhagem(estado, ctx, girar(estado, ctx, "linhagem").fatias[0])
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
                if luta.acabou:  # o Dragão Negro pode encerrar a luta no próprio Despertar
                    break
            if jurar_luta_auto(luta):
                luta.jurar_luta()
                if luta.acabou:
                    break
            if len(luta.rivais) > 1:
                luta.mirar(escolher_alvo_auto(luta))
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
        substituir_tecnica(estado, pior, nova, ctx)


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
        _fundir_auto(estado, ctx)  # o que o último passo trouxe (técnica, Relíquia, Dom)
        if estado.altar_pendente:
            estado.altar_pendente = False
            if altar is not None and estado.votos.pode_jurar():
                estado.altares += 1
                altar(estado, ctx, rng)
        if estado.arco is None:
            aplicar_arco(estado, ctx, girar_arco(estado, ctx).fatias[0])
        if tem_caminho(estado, ctx):
            portas = oferecer_caminho(estado, ctx, rng)
            porta = portas[escolher_porta_auto(portas, estado.jogador)]
            if porta.tipo == "evento":
                ev = porta.evento
                giro = atravessar_encruzilhada(
                    estado, ev.opcoes[escolher_opcao_auto(ev, estado.jogador, bool(estado.aliado))]
                )
                if giro == "reliquias":
                    receber_reliquia(estado, girar(estado, ctx, "reliquias").fatias[0])
                elif giro == "tecnicas":
                    _tecnica_auto(estado, ctx, rng, altar)
                continue
            escolher_porta(estado, porta)
        if not jogar_luta(estado, ctx, rng, reg) or estado.venceu:
            break
        _fundir_auto(estado, ctx)  # o Despertar da luta pode completar uma fusão
        if ctx.treinos:
            oferta = oferecer_treinos(ctx, rng, estado)
            aplicar_treino(estado.jogador, escolher_treino_auto(estado.jogador, oferta))
        _tecnica_auto(estado, ctx, rng, altar)
        if vai_ter_reliquia(estado, ctx, rng):
            receber_reliquia(estado, girar(estado, ctx, "reliquias").fatias[0])
    return estado


def _fundir_auto(estado: EstadoRun, ctx: Contexto) -> None:
    """O piloto nas fusões: a que nasce sem espaço troca a pior (como uma técnica nova)."""
    for n in fundir(estado, ctx):
        if n.resultado == "cheio":
            _substituir_auto(estado, ctx, n.fatia)


def _combo(estado: EstadoRun, fatia: Fatia) -> int:
    """O quanto `fatia` ajuda a montar algo: 2 se é peça que falta numa fusão, 1 se o anime
    dela já tem 2 técnicas equipadas (vira Ressonância)."""
    from karmabound.fusoes import carregar_fusoes, faltam
    from karmabound.ressonancia import contar_animes

    for fusao in carregar_fusoes():
        if fusao.id not in estado.fusoes_nascidas:
            if any(fatia.id in r.ids for r in faltam(fusao, estado)):
                return 2
    return 1 if contar_animes(estado).get(anime_de(fatia.origem), 0) >= 2 else 0


def _tecnica_auto(
    estado: EstadoRun, ctx: Contexto, rng: random.Random, altar: Altar | None
) -> None:
    """O piloto num giro de Técnicas: pega a mais rara (no empate, a peça de uma fusão ou
    de uma Ressonância); se não cabe, troca a pior."""
    giro = girar(estado, ctx, "tecnicas")
    nova = max(giro.fatias, key=lambda f: (ctx.ordem.index(f.raridade), _combo(estado, f)))
    resultado = receber_tecnica(estado, ctx, nova)
    if resultado == "altar" and altar is not None:
        estado.altares += 1
        altar(estado, ctx, rng)
    elif resultado == "cheio":
        _substituir_auto(estado, ctx, nova)


def medir(
    estado: EstadoRun,
    ctx: Contexto,
    modificar: Callable[[EstadoRun], None],
    amostras: int = 200,
    seed: int = 0,
    horizonte: int | None = None,
) -> float:
    """Lutas vencidas a mais (positivo) ou a menos (negativo) no resto da run com `modificar`.

    Mesmas seeds com e sem: a diferença vem da modificação, não do acaso. `horizonte`:
    joga só as próximas N lutas e projeta a diferença para o resto da run (o Altar da
    tela usa, para não fazer o jogador esperar).
    """
    restantes = ctx.restantes(estado.proxima_luta)
    ate = None
    escala = 1.0
    if horizonte is not None and horizonte < restantes:
        ate = estado.proxima_luta + horizonte - 1
        escala = restantes / horizonte
    diferenca = 0
    for i in range(amostras):
        base = estado.clonar(random.Random(seed + i))
        jogar_run(base, ctx, random.Random(seed + i), ate=ate)
        variante = estado.clonar(random.Random(seed + i))
        modificar(variante)
        jogar_run(variante, ctx, random.Random(seed + i), ate=ate)
        diferenca += variante.lutas_vencidas - base.lutas_vencidas
    return diferenca / amostras * escala


def aplicar_voto(estado: EstadoRun, ctx: Contexto, voto: Voto) -> None:
    if voto.duracao == "capitulo":  # o capítulo pode ter crescido com a Invasão
        voto.lutas_restantes = estado.tamanho_capitulo - estado.luta_no_capitulo + 1
    else:
        voto.lutas_restantes = lutas_da_duracao(voto.duracao, estado.proxima_luta, 1)
    estado.votos.jurar(voto)
    atualizar_efeitos(estado)  # votos + Dom + Relíquias: só os votos apagaria o resto


def _com(ctx: Contexto, restricoes, ganhos, duracao: str) -> Callable[[EstadoRun], None]:
    def modificar(e: EstadoRun) -> None:
        aplicar_voto(e, ctx, Voto(list(restricoes), list(ganhos), duracao))

    return modificar


def medir_restricoes(
    estado: EstadoRun,
    ctx: Contexto,
    duracao: str = "run",
    amostras: int = 120,
    seed: int = 0,
    horizonte: int | None = None,
) -> dict[str, float]:
    """Sacrifício de cada restrição sozinha contra o build atual, em lutas (≥ 0 = custa)."""
    return {
        r.id: -medir(estado, ctx, _com(ctx, [r], [], duracao), amostras, seed, horizonte)
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
    horizonte: int | None = None,
) -> tuple[float, float]:
    """(pontos, sacrifício medido junto) de um conjunto de restrições."""
    cat = ctx.catalogo
    junto = -medir(estado, ctx, _com(ctx, restricoes, [], duracao), amostras, seed, horizonte)
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
    horizonte: int | None = None,
) -> dict[str, float]:
    """Quanto cada ganho rende junto destas restrições, em lutas: é o que dá o preço."""
    return {
        g.id: medir(estado, ctx, _com(ctx, restricoes, [g], duracao), amostras, seed, horizonte)
        + sacrificio
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
    estado: EstadoRun,
    ctx: Contexto,
    voto: Voto,
    amostras: int = 120,
    seed: int = 0,
    horizonte: int | None = None,
) -> float:
    """Lutas vencidas a mais (ou a menos) com o voto inteiro: a estimativa que o Altar mostra."""
    modificar = _com(ctx, voto.restricoes, voto.ganhos, voto.duracao)
    return medir(estado, ctx, modificar, amostras, seed, horizonte)


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


def altar_rapido(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> None:
    """O Altar do simulador: sem medir nada, com os valores típicos do catálogo.

    `altar_auto` mede cada restrição contra o build (centenas de continuações da run):
    certo, mas lento demais para rodar dentro de milhares de runs. Este usa o sacrifício
    e o benefício típicos (lutas por luta restante, medidos por `tools/medir_tipicos.py`)
    e só jura se o voto compensa, como o jogador que lê o Altar.
    """
    if not estado.votos.pode_jurar():
        return
    cat = ctx.catalogo
    restantes = ctx.restantes(estado.proxima_luta)
    tipico = {r.id: r.tipico * restantes for r in cat.restricoes.values()}
    candidatas = sorted(
        (r for r in cat.restricoes.values() if tipico[r.id] > 0),
        key=lambda r: min(tipico[r.id], cat.teto_por_restricao),
        reverse=True,
    )[:3]
    if not candidatas:
        return
    individuais = [tipico[r.id] for r in candidatas]
    sacrificio = sum(individuais)
    pontos = cat.pontos(cat.creditado(sacrificio, individuais), "run", candidatas)
    pontos += estado.pontos_guardados
    beneficio = {g.id: g.tipico * restantes for g in cat.ganhos.values()}
    ganhos = comprar_ganhos(estado, ctx, candidatas, pontos, sacrificio, "run", beneficio=beneficio)
    if sum(beneficio[g.id] for g in ganhos) <= sacrificio:
        return
    voto = Voto(candidatas, ganhos, "run", pontos=pontos, sacrificio=sacrificio)
    voto.sobra = pontos - custo_dos_ganhos(ctx, ganhos, beneficio)
    aplicar_voto(estado, ctx, voto)
    estado.pontos_guardados = max(0.0, voto.sobra)


def altar_auto(estado: EstadoRun, ctx: Contexto, rng: random.Random) -> None:
    if not estado.votos.pode_jurar():
        return
    voto = montar_voto_auto(estado, ctx, seed=rng.randrange(1 << 30))
    if voto is not None:
        aplicar_voto(estado, ctx, voto)
        estado.pontos_guardados = max(0.0, voto.sobra)

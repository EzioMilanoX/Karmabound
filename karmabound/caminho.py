"""O caminho entre as lutas: portas, bandos, elites, encruzilhadas e a Nêmesis.

Regras puras, sem tela. Antes de cada luta que não é de chefe, o jogador escolhe 1
de 3 portas:

- **Rival**: um lutador, como sempre.
- **Bando**: 2 ou 3 rivais, cada um com um papel (lâmina, guardião, curandeiro,
  xamã). A vida do bando é a de um rival comum vezes `fator_vida`, repartida pelo
  peso de cada papel; cada um bate menos (`dano_mult`), mas são vários.
- **Elite**: mais forte; vencer garante uma Relíquia. Às vezes é um bando com
  Comandante. Toda elite ganha afixos sorteados (`afixos`: Vampírico, Espinhos...).
- **Encruzilhada**: sem luta. Um encontro com escolha e preço (`eventos`).
- **Nêmesis**: o rival que te matou numa run passada (vem do `Legado`). Só a
  partir do capítulo 2, uma vez por run.

Os números estão em `data/caminho.json`.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

from karmabound.combate import Lutador, Tecnica, evoluir, invocar, valor_tecnica
from karmabound.efeitos import Efeitos, somar
from karmabound.rodas import DADOS

TIPOS = ("rival", "bando", "elite", "evento", "nemesis")
# As figuras dos rivais (as mesmas de figuras.ESTILOS; aqui sem depender da tela)
ESTILOS = ("espadachim", "monge", "ninja", "oni", "hollow", "tita")
NOME_ESTILO = {
    "espadachim": "Ronin",
    "monge": "Monge Errante",
    "ninja": "Shinobi",
    "oni": "Oni",
    "hollow": "Hollow",
    "tita": "Titã",
    "colosso": "Colosso",
}


def estilo_do_rival(n_luta: int, capitulo: int, chefe: bool) -> str:
    """A figura de um rival sozinho: o chefe é o colosso; os outros variam pela luta."""
    return "colosso" if chefe else ESTILOS[(n_luta * 5 + capitulo) % len(ESTILOS)]


def nome_de_nemesis(estilo: str, golpe: str) -> str:
    """'Ronin · Chidori': quem te matou, pelo golpe que te matou."""
    base = NOME_ESTILO.get(estilo, "Rival")
    return f"{base} · {golpe}" if golpe else base


@dataclass(frozen=True)
class Papel:
    id: str
    nome: str
    kanji: str
    vida: float  # peso na vida do bando
    dano: float  # multiplicador do dano
    estilo: str
    texto: str
    tecnica: dict | None = None


@dataclass(frozen=True)
class Opcao:
    texto: str
    cura: float = 0.0
    vida_max: int = 0
    perde_vida_frac: float = 0.0
    dano: int = 0
    carma: float = 0.0
    zera_carma: bool = False
    custa_carma: int = 0
    velocidade: int = 0
    percepcao: int = 0
    evoluir: bool = False
    giro: str = ""  # "tecnicas" | "reliquias": a escolha leva a um giro
    aliado: bool = False  # a escolha traz um aliado (sorteado; substitui o que você tem)


@dataclass(frozen=True)
class Evento:
    id: str
    nome: str
    kanji: str
    texto: str
    opcoes: tuple[Opcao, ...]


@dataclass(frozen=True)
class Afixo:
    """Um afixo de elite (`caminho.json`, `afixos`). `efeitos`: o que entra pelos Efeitos
    do rival; `lutador`: campos do Lutador que o combate lê; `por_capitulo`: o que
    cresce por capítulo depois do 1º; `bloqueio_frac` e `invocacao`: os casos à parte."""

    id: str
    nome: str
    kanji: str
    texto: str
    efeitos: dict = field(default_factory=dict)
    lutador: dict = field(default_factory=dict)
    por_capitulo: dict = field(default_factory=dict)
    bloqueio_frac: float = 0.0
    invocacao: dict = field(default_factory=dict)  # {"turnos", "dano"}


@dataclass(frozen=True)
class Porta:
    tipo: str  # rival | bando | elite | evento | nemesis
    nome: str
    kanji: str
    texto: str
    papeis: tuple[str, ...] = ()  # o bando que espera atrás dela
    evento: Evento | None = None


@dataclass(frozen=True)
class Caminho:
    portas: int
    pesos: dict[str, float]
    elite_a_partir_da_luta: int
    bando_a_partir_da_luta: int
    bando: dict
    elite: dict
    nemesis: dict
    papeis: dict[str, Papel]
    grupos: tuple[tuple[str, ...], ...]
    grupos_elite: tuple[tuple[str, ...], ...]
    tipos: dict[str, dict]
    eventos: tuple[Evento, ...] = field(default=())
    afixos: dict[str, Afixo] = field(default_factory=dict)  # os afixos de elite

    def porta(self, tipo: str, **extra) -> Porta:
        t = self.tipos[tipo]
        return Porta(tipo, t["nome"], t["kanji"], t["texto"], **extra)


def carregar_caminho(caminho: Path | None = None) -> Caminho:
    d = json.loads((caminho or DADOS / "caminho.json").read_text(encoding="utf-8"))
    papeis = {pid: Papel(id=pid, **p) for pid, p in d["papeis"].items()}
    eventos = tuple(
        Evento(e["id"], e["nome"], e["kanji"], e["texto"], tuple(Opcao(**o) for o in e["opcoes"]))
        for e in d["eventos"]
    )
    return Caminho(
        portas=d["portas"],
        pesos=d["pesos"],
        elite_a_partir_da_luta=d["elite_a_partir_da_luta"],
        bando_a_partir_da_luta=d.get("bando_a_partir_da_luta", 1),
        bando=d["bando"],
        elite=d["elite"],
        nemesis=d["nemesis"],
        papeis=papeis,
        grupos=tuple(tuple(g) for g in d["grupos"]),
        grupos_elite=tuple(tuple(g) for g in d["grupos_elite"]),
        tipos=d["portas_tipos"],
        eventos=eventos,
        afixos={aid: Afixo(id=aid, **a) for aid, a in d.get("afixos", {}).items()},
    )


# ----------------------------------------------------------------------- portas


def oferecer_portas(
    cam: Caminho, rng: random.Random, n_luta: int, capitulo: int, nemesis: bool = False
) -> tuple[Porta, ...]:
    """As portas desta encruzilhada: sempre um Rival; as outras sorteadas pelos pesos,
    sem repetir. `nemesis`: a Nêmesis está à espera e toma o lugar de uma delas."""
    pesos = dict(cam.pesos)
    if n_luta < cam.elite_a_partir_da_luta:
        pesos.pop("elite", None)
    if n_luta < cam.bando_a_partir_da_luta:  # a primeira luta é um duelo: você ainda bate fraco
        pesos.pop("bando", None)
    portas = [cam.porta("rival")]
    while len(portas) < cam.portas and pesos:
        tipos = list(pesos)
        tipo = rng.choices(tipos, weights=[pesos[t] for t in tipos])[0]
        del pesos[tipo]
        portas.append(_montar(cam, tipo, rng))
    if nemesis and capitulo >= cam.nemesis["a_partir_do_capitulo"]:
        portas[-1] = cam.porta("nemesis")
    return tuple(portas)


def _montar(cam: Caminho, tipo: str, rng: random.Random) -> Porta:
    if tipo == "bando":
        return cam.porta("bando", papeis=rng.choice(cam.grupos))
    if tipo == "elite":
        papeis = rng.choice(cam.grupos_elite) if rng.random() < cam.elite["bando"] else ()
        return cam.porta("elite", papeis=papeis)
    if tipo == "evento":
        return cam.porta("evento", evento=rng.choice(cam.eventos))
    return cam.porta(tipo)


def escolher_porta_auto(portas: tuple[Porta, ...], jogador: Lutador) -> int:
    """O piloto: mal de vida, procura a encruzilhada (quase sempre cura) ou o rival;
    inteiro, vai atrás da Relíquia (elite, Nêmesis); no meio, o que vier."""
    fracao = jogador.vida / jogador.vida_max

    def nota(p: Porta) -> float:
        if fracao < 0.4:
            return {"evento": 3, "rival": 2, "bando": 1}.get(p.tipo, 0)
        if fracao > 0.75:
            return {"nemesis": 4, "elite": 3, "bando": 2, "rival": 1.5}.get(p.tipo, 1)
        return {"rival": 3, "bando": 2.5, "evento": 2, "elite": 1, "nemesis": 1}[p.tipo]

    return max(range(len(portas)), key=lambda i: nota(portas[i]))


# ----------------------------------------------------------------------- bandos


def montar_bando(
    cam: Caminho,
    papeis: tuple[str, ...],
    vida_rival: float,
    tecnicas: list[list[Tecnica]],
    rng: random.Random,
    capitulo: int,
    velocidade: tuple[int, int],
    percepcao: tuple[int, int],
) -> list[Lutador]:
    """Os rivais de um bando. `vida_rival`: a vida que um rival comum teria nesta luta;
    `tecnicas[i]`: as técnicas sorteadas para o membro i (o papel acrescenta a dele)."""
    n = len(papeis)
    total = vida_rival * cam.bando["fator_vida"][str(n)]
    pesos = [cam.papeis[p].vida for p in papeis]
    dano_bando = cam.bando["dano_mult"][str(n)]
    vistos: dict[str, int] = {}
    membros = []
    for i, pid in enumerate(papeis):
        papel = cam.papeis[pid]
        vistos[pid] = vistos.get(pid, 0) + 1
        titulo = papel.nome + (" II" if vistos[pid] == 2 else " III" if vistos[pid] == 3 else "")
        lista = list(tecnicas[i])
        if papel.tecnica:
            lista.append(tecnica_do_papel(papel, vida_rival, capitulo))
        membros.append(
            Lutador(
                nome=titulo,
                vida_max=max(1, round(total * pesos[i] / sum(pesos))),
                velocidade=rng.randint(*velocidade),
                percepcao=rng.randint(*percepcao),
                tecnicas=lista,
                papel=pid,
                estilo=papel.estilo,
                titulo=titulo,
            )
        )
        membros[-1].dano_mult = dano_bando * papel.dano
    return membros


def tecnica_do_papel(papel: Papel, vida_rival: float, capitulo: int) -> Tecnica:
    """A técnica que o papel traz, na escala desta luta."""
    d = dict(papel.tecnica or {})
    proteger = round(vida_rival * d.pop("proteger_frac", 0))
    curar = round(vida_rival * d.pop("curar_frac", 0))
    d["veneno"] = d.get("veneno", 0) + d.pop("veneno_por_capitulo", 0) * (capitulo - 1)
    d["inspirar"] = d.get("inspirar", 0) + d.pop("inspirar_por_capitulo", 0) * (capitulo - 1)
    return Tecnica(proteger=proteger, curar_aliado=curar, **d)


def fortalecer_elite(
    cam: Caminho,
    rival: Lutador,
    bando: bool = False,
    rng: random.Random | None = None,
    capitulo: int = 1,
) -> None:
    """A elite: mais vida, mais dano e mais atenção. Num bando (que já tem o Comandante),
    o reforço é menor. Com `rng`, ganha os afixos (1; 2 a partir do capítulo de
    `elite.afixos_dois_a_partir_do_capitulo`)."""
    e = cam.elite
    vida = e["bando_vida_mult"] if bando else e["vida_mult"]
    rival.vida_max = rival.base_vida_max = rival.vida = round(rival.vida_max * vida)
    rival.dano_mult *= e["bando_dano_mult"] if bando else e["dano_mult"]
    rival.percepcao += e["percepcao"]
    rival.base_percepcao = rival.percepcao
    rival.elite = True
    if rng is not None and cam.afixos:
        aplicar_afixos(cam, rival, sortear_afixos(cam, rng, capitulo), capitulo)


def sortear_afixos(cam: Caminho, rng: random.Random, capitulo: int) -> tuple[str, ...]:
    e = cam.elite
    n = e.get("afixos", 1) + (capitulo >= e.get("afixos_dois_a_partir_do_capitulo", 99))
    return tuple(rng.sample(sorted(cam.afixos), min(n, len(cam.afixos))))


def aplicar_afixos(cam: Caminho, rival: Lutador, ids: tuple[str, ...], capitulo: int) -> None:
    """Os afixos da elite: o que é Efeito entra pelos Efeitos do rival; o resto, pelos
    campos que o combate lê (`blindagem`, `marca_ao_ferir`, `gelo`, `veloz`)."""
    efeitos = []
    for aid in ids:
        a = cam.afixos[aid]
        mais = {k: v * (capitulo - 1) for k, v in a.por_capitulo.items()}
        if a.efeitos:
            d = {k: v + mais.get(k, 0) for k, v in a.efeitos.items()}
            efeitos.append(Efeitos.de_dict({k: _como(a.efeitos[k], v) for k, v in d.items()}))
        for campo, v in a.lutador.items():
            setattr(rival, campo, getattr(rival, campo) + _como(v, v + mais.get(campo, 0)))
        if a.bloqueio_frac:
            rival.blindagem = max(1, round(rival.vida_max * a.bloqueio_frac))
            rival.bloqueio = max(rival.bloqueio, rival.blindagem)  # já chega blindado
        if a.invocacao:
            dano = a.invocacao["dano"] + int(mais.get("invocacao", 0))
            invocar(rival, [a.invocacao["turnos"], dano, f"afixo_{aid}"])
    rival.afixos = rival.afixos + tuple(ids)
    if efeitos:
        rival.aplicar_efeitos(somar([rival.efeitos, *efeitos]))
    if rival.efeitos.revide_permanente:  # os espinhos já estão de pé na primeira troca
        rival.revide = max(rival.revide, rival.efeitos.revide_permanente)


def _como(modelo, v):
    """`v` no tipo de `modelo` (o que é inteiro nos dados continua inteiro)."""
    return int(v) if isinstance(modelo, int) and not isinstance(modelo, bool) else v


def fortalecer_nemesis(
    cam: Caminho, rival: Lutador, nemesis: dict, tecnica: Tecnica | None
) -> None:
    """A Nêmesis: mais forte a cada vez que te matou, e com o golpe que te matou."""
    n = cam.nemesis
    vezes = max(1, nemesis.get("vezes", 1))
    vida = n["vida_mult"] + n["vida_por_vez"] * (vezes - 1)
    rival.vida_max = rival.base_vida_max = rival.vida = round(rival.vida_max * vida)
    rival.dano_mult *= n["dano_mult"] + n["dano_por_vez"] * (vezes - 1)
    if tecnica is not None:
        for _ in range(vezes - 1):
            tecnica = evoluir(tecnica)
        rival.tecnicas = [t for t in rival.tecnicas if t.id != tecnica.id]
        if len(rival.tecnicas) >= 4:
            rival.tecnicas.remove(min(rival.tecnicas, key=valor_tecnica))
        rival.tecnicas.append(tecnica)
    rival.nemesis = True
    rival.estilo = nemesis.get("estilo", "") or rival.estilo
    rival.nome = rival.titulo = nemesis.get("nome", "Nêmesis")


# ----------------------------------------------------------------------- encruzilhadas


def pode_escolher(op: Opcao, jogador: Lutador) -> bool:
    return not op.custa_carma or (
        jogador.carma is not None and jogador.carma.valor >= op.custa_carma
    )


def aplicar_opcao(op: Opcao, jogador: Lutador) -> None:
    """O que a escolha faz no lutador (o giro, se houver, fica com quem chamou)."""
    carma = jogador.carma
    if op.custa_carma and carma is not None:
        carma.valor = max(0.0, carma.valor - op.custa_carma)
    if op.vida_max:
        jogador.base_vida_max = max(1, jogador.base_vida_max + op.vida_max)
        if op.vida_max > 0:
            jogador.vida += op.vida_max
    jogador.base_velocidade += op.velocidade
    jogador.base_percepcao += op.percepcao
    jogador.dano_run += op.dano
    jogador.aplicar_efeitos(jogador.efeitos)
    if op.perde_vida_frac:
        jogador.vida = max(1, jogador.vida - round(jogador.vida * op.perde_vida_frac))
    if op.cura and not jogador.efeitos.sem_cura:
        cura = round(jogador.vida_max * op.cura * jogador.efeitos.cura_mult)
        jogador.vida = min(jogador.vida_max, jogador.vida + cura)
    if carma is not None:
        if op.zera_carma:
            carma.valor = 0.0
        if op.carma:
            carma.ganhar(op.carma * jogador.efeitos.carma_mult)
    if op.evoluir and jogador.tecnicas:
        melhor = max(jogador.tecnicas, key=valor_tecnica)
        jogador.tecnicas[jogador.tecnicas.index(melhor)] = evoluir(
            melhor, jogador.efeitos.fator_evolucao
        )


def escolher_opcao_auto(ev: Evento, jogador: Lutador, tem_aliado: bool = False) -> int:
    """O piloto numa encruzilhada: cura se precisa; senão o que fica para a run. Aceita um
    aliado quando ainda não tem um e está bem de vida."""
    fracao = jogador.vida / jogador.vida_max

    def nota(op: Opcao) -> float:
        if not pode_escolher(op, jogador):
            return -99
        valor = 0.0
        if op.cura:
            valor += op.cura * (12 if fracao < 0.6 else 2)
        valor += op.vida_max * 0.2 + op.dano * 3 + op.percepcao * 1.5 + op.velocidade
        valor += (4 if op.evoluir else 0) + (3 if op.giro == "reliquias" else 0)
        valor += (2.5 if op.giro == "tecnicas" else 0) + op.carma / 20
        if op.aliado:
            valor += 6 if fracao >= 0.6 and not tem_aliado else -6
        valor -= op.perde_vida_frac * (15 if fracao < 0.6 else 5) + op.custa_carma / 25
        return valor

    return max(range(len(ev.opcoes)), key=lambda i: nota(ev.opcoes[i]))

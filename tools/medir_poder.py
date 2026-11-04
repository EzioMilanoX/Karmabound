"""Quanto um item vale: python tools/medir_poder.py [ids...] [--runs N] [--dificuldade D]

Compara runs com e sem o item, em pontos de vitória — a unidade da régua do
DESIGN.md (Cinza +1 a +3, Sangue +3 a +5, Maldito +5 a +10, Divino +10 a +20).

- Técnica: começa no 3º espaço; a linha de base tem a Investida (Cinza) ali.
- Dom: a run inteira com esse Dom, contra a run sem Dom.
- Relíquia: começa a run com ela, contra a run sem ela.

Sem ids, mede todos os Dons, Relíquias e técnicas Malditas/Divinas. Roda em paralelo.
"""

from __future__ import annotations

import argparse
import copy
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from karmabound.rodas import (  # noqa: E402
    carregar_balanceamento,
    carregar_raridades,
    carregar_rodas,
)
from karmabound.run import (  # noqa: E402
    aplicar_dom,
    aplicar_linhagem,
    atualizar_efeitos,
    receber_reliquia,
)
from karmabound.simulacao import simular_com_combate  # noqa: E402

SEEDS = (1, 2, 3)


def _rodas():
    return carregar_rodas(carregar_raridades(carregar_balanceamento()))


def tipo_do_item(item: str) -> str:
    rodas = _rodas()
    pares = (
        ("tecnicas", "tecnica"),
        ("destino", "dom"),
        ("reliquias", "reliquia"),
        ("linhagem", "linhagem"),
    )
    for roda, tipo in pares:
        if any(f.id == item for f in rodas[roda].fatias):
            return tipo
    raise SystemExit(f"item desconhecido: {item}")


def _sem_dom(estado, ctx):
    estado.dom = None
    estado.jogador.tecnica_dom = None
    atualizar_efeitos(estado)


def _sem_linhagem(estado, ctx):
    """Tira a Linhagem que a run sorteou (e a técnica com que ela começa)."""
    lin = estado.linhagem
    if lin is not None and lin.inicial:
        estado.jogador.tecnicas = [t for t in estado.jogador.tecnicas if t.id != lin.inicial]
    estado.linhagem = None
    estado.jogador.tecnica_linhagem = None
    atualizar_efeitos(estado)
    estado.jogador.vida = estado.jogador.vida_max


def _uma(args: tuple[str, str, int, int, str | None]) -> tuple[tuple[str, str], int, int]:
    tipo, item, seed, runs, dificuldade = args
    bal = copy.deepcopy(carregar_balanceamento())
    preparar = None
    if tipo == "tecnica":
        bal["combate"]["jogador"]["tecnicas"] = ["golpe_direto", "guarda_alta", item]
    elif tipo == "dom":
        if item == "-":
            preparar = _sem_dom
        else:
            fatia = next(f for f in _rodas()["destino"].fatias if f.id == item)
            preparar = lambda e, c: aplicar_dom(e, c, fatia)  # noqa: E731
    elif tipo == "linhagem":
        if item == "-":
            preparar = _sem_linhagem
        else:
            fatia = next(f for f in _rodas()["linhagem"].fatias if f.id == item)

            def preparar(e, c, fatia=fatia):
                _sem_linhagem(e, c)
                aplicar_linhagem(e, c, fatia)

    elif tipo == "reliquia" and item != "-":
        fatia = next(f for f in _rodas()["reliquias"].fatias if f.id == item)
        preparar = lambda e, c: receber_reliquia(e, fatia)  # noqa: E731
    r = simular_com_combate(
        runs, seed, balanceamento=bal, dificuldade=dificuldade, preparar=preparar
    )
    return (tipo, item), r.vitorias, r.runs


def medir(itens: list[str], runs: int, dificuldade: str | None) -> dict[tuple[str, str], float]:
    tipos = {i: tipo_do_item(i) for i in itens}
    bases = {"tecnica": "investida", "dom": "-", "reliquia": "-", "linhagem": "-"}
    alvos = {(t, bases[t]) for t in tipos.values()} | {(t, i) for i, t in tipos.items()}
    tarefas = [(t, i, s, runs, dificuldade) for t, i in sorted(alvos) for s in SEEDS]
    soma: dict[tuple[str, str], list[int]] = {}
    with ProcessPoolExecutor() as ex:
        for chave, v, n in ex.map(_uma, tarefas):
            acc = soma.setdefault(chave, [0, 0])
            acc[0] += v
            acc[1] += n
    return {k: v / n for k, (v, n) in soma.items()}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("itens", nargs="*")
    ap.add_argument("--runs", type=int, default=2000, help="runs por seed (3 seeds)")
    ap.add_argument("--dificuldade", default="dificil")
    args = ap.parse_args()
    rodas = _rodas()
    itens = args.itens or (
        [f.id for f in rodas["destino"].fatias]
        + [f.id for f in rodas["reliquias"].fatias]
        + [
            f.id
            for f in rodas["tecnicas"].fatias
            if f.raridade in ("maldito", "divino") and f.combate
        ]
    )
    raridade = {f.id: f.raridade for r in rodas.values() for f in r.fatias}
    taxas = medir(itens, args.runs, args.dificuldade)
    print(f"{args.dificuldade} · {args.runs * len(SEEDS)} runs por item")
    bases = {
        "tecnica": ("investida", "com a Investida"),
        "dom": ("-", "sem Dom"),
        "reliquia": ("-", "sem relíquia"),
        "linhagem": ("-", "sem linhagem"),
    }
    for tipo, (b, nome) in bases.items():
        if (tipo, b) in taxas:
            print(f"  linha de base {nome:<16} {taxas[(tipo, b)]:6.1%}")
    for i in itens:
        tipo = tipo_do_item(i)
        v, v0 = taxas[(tipo, i)], taxas[(tipo, bases[tipo][0])]
        print(f"{tipo:<9} {i:<24} {raridade[i]:<8} {v:6.1%}  ({(v - v0) * 100:+5.1f} pts)")


if __name__ == "__main__":
    main()

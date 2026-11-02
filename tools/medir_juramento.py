"""Quanto o Juramento vale: python tools/medir_juramento.py [--runs N] [--luta L] [--dificuldade D]

Joga cada run até a luta L. Daí a run vira duas, com o mesmo futuro sorteado:
uma segue sem voto, a outra passa pelo Altar (piloto automático monta o voto).
A diferença de vitórias é o valor do Juramento em pontos, a unidade da régua do
DESIGN.md (Maldito +5 a +10).
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from karmabound.run import (  # noqa: E402
    Contexto,
    aplicar_voto,
    jogar_run,
    montar_voto_auto,
    nova_run,
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=300)
    ap.add_argument("--luta", type=int, default=4, help="o Altar abre depois desta luta")
    ap.add_argument("--dificuldade", default=None)
    ap.add_argument("--amostras", type=int, default=60, help="continuações por medição no Altar")
    ap.add_argument("--duracao", default="run", choices=("luta", "capitulo", "run"))
    ap.add_argument("--cambio", type=float, default=None, help="testar outro câmbio de preço")
    args = ap.parse_args()

    ctx = Contexto.padrao(args.dificuldade)
    if args.cambio is not None:
        ctx = replace(ctx, catalogo=replace(ctx.catalogo, preco_cambio=args.cambio))
    t0 = time.time()
    chegaram = sem = com = 0
    pontos, sacrificios = [], []
    restricoes, ganhos = Counter(), Counter()
    for i in range(args.runs):
        estado = jogar_run(nova_run(ctx, random.Random(i)), ctx, random.Random(i), ate=args.luta)
        if estado.derrotado:
            continue
        chegaram += 1
        futuro = 10_000 + i
        base = jogar_run(estado.clonar(random.Random(futuro)), ctx, random.Random(futuro))
        sem += not base.derrotado
        jurou = estado.clonar(random.Random(futuro))
        voto = montar_voto_auto(jurou, ctx, args.duracao, args.amostras, seed=i)
        if voto is not None:
            aplicar_voto(jurou, ctx, voto)
            pontos.append(voto.pontos)
            sacrificios.append(voto.sacrificio)
            restricoes.update(r.nome for r in voto.restricoes)
            ganhos.update(g.nome for g in voto.ganhos)
        jogar_run(jurou, ctx, random.Random(futuro))
        com += not jurou.derrotado
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{args.runs} runs ({time.time() - t0:.0f}s)", file=sys.stderr)

    if not chegaram:
        print("nenhuma run chegou ao Altar")
        return
    print(f"{args.runs} runs, {chegaram} chegaram à luta {args.luta} · voto {args.duracao}")
    print(f"vitória sem voto: {sem / chegaram:.1%}   com voto: {com / chegaram:.1%}")
    delta = (com - sem) / chegaram
    print(f"valor do Juramento: {delta * 100:+.1f} pontos entre quem chegou ao Altar")
    print(f"  ~{delta * chegaram / args.runs * 100:+.1f} pontos na run inteira")
    if pontos:
        media_s = sum(sacrificios) / len(sacrificios)
        media_p = sum(pontos) / len(pontos)
        print(f"sacrifício médio {media_s:.2f} lutas → {media_p:.2f} pontos")
    print("restrições escolhidas:", dict(restricoes.most_common()))
    print("ganhos comprados:", dict(ganhos.most_common()))
    print(f"({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()

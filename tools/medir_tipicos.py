"""Valores típicos do Altar: python tools/medir_tipicos.py [--runs N] [--amostras A] [--aplicar]

O Altar da tela mede cada restrição contra o build do jogador. O simulador não pode
fazer isso milhares de vezes, então o seu Altar (`run.altar_rapido`) usa valores
típicos: o sacrifício de cada restrição e o benefício do 1º nível de cada ganho, em
lutas por luta restante, medidos aqui nos fins de capítulo de muitas runs. Com
`--aplicar`, grava o campo `tipico` em karmabound/data/votos.json.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from karmabound.run import (  # noqa: E402
    Contexto,
    beneficios_dos_ganhos,
    jogar_run,
    medir_restricoes,
    nova_run,
)

VOTOS = Path(__file__).resolve().parent.parent / "karmabound" / "data" / "votos.json"


def _um(args: tuple[int, int, int, str | None]):
    seed, ate, amostras, dificuldade = args
    ctx = Contexto.padrao(dificuldade)
    estado = jogar_run(nova_run(ctx, random.Random(seed)), ctx, random.Random(seed), ate=ate)
    if estado.derrotado or estado.venceu:
        return None
    restantes = ctx.lutas - estado.proxima_luta + 1
    sac = medir_restricoes(estado, ctx, "run", amostras, seed)
    ben = beneficios_dos_ganhos(estado, ctx, [], 0.0, "run", amostras, seed)
    return {k: v / restantes for k, v in sac.items()}, {k: v / restantes for k, v in ben.items()}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=24, help="runs por fim de capítulo")
    ap.add_argument("--amostras", type=int, default=40)
    ap.add_argument("--dificuldade", default="dificil")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()
    ctx = Contexto.padrao(args.dificuldade)
    fins = [ctx.lutas_por_capitulo * c for c in range(1, ctx.capitulos)]
    tarefas = [(s, ate, args.amostras, args.dificuldade) for ate in fins for s in range(args.runs)]
    soma_r: dict[str, float] = {}
    soma_g: dict[str, float] = {}
    n = 0
    with ProcessPoolExecutor() as ex:
        for res in ex.map(_um, tarefas):
            if res is None:
                continue
            n += 1
            for k, v in res[0].items():
                soma_r[k] = soma_r.get(k, 0.0) + v
            for k, v in res[1].items():
                soma_g[k] = soma_g.get(k, 0.0) + v
    tip_r = {k: round(max(0.0, v / n), 4) for k, v in soma_r.items()}
    tip_g = {k: round(max(0.0, v / n), 4) for k, v in soma_g.items()}
    print(f"{n} estados medidos ({args.amostras} continuações cada)")
    print("restrições (lutas perdidas por luta restante):")
    for k, v in sorted(tip_r.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v:.3f}")
    print("ganhos, 1º nível (lutas ganhas por luta restante):")
    for k, v in sorted(tip_g.items(), key=lambda x: -x[1]):
        print(f"  {k:<20} {v:.3f}")
    if args.aplicar:
        d = json.loads(VOTOS.read_text(encoding="utf-8"))
        for x in d["restricoes"]:
            x["tipico"] = tip_r.get(x["id"], 0.0)
        for x in d["ganhos"]:
            x["tipico"] = tip_g.get(x["id"], 0.0)
        VOTOS.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"gravado em {VOTOS.name}")


if __name__ == "__main__":
    main()

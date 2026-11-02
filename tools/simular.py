"""Relatório da simulação de runs.

python tools/simular.py [--runs N] [--seed S]   modelo de dano simples: ritmo do Carma
python tools/simular.py --combate [--runs N]    lutas de verdade, todos os modos de dificuldade
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from karmabound.rodas import carregar_balanceamento, carregar_raridades  # noqa: E402
from karmabound.simulacao import FormaDaRun, simular, simular_com_combate  # noqa: E402

ALVO_DESPERTARES = (1.0, 2.0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos certos também quando a saída é redirecionada
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--combate", action="store_true", help="simular com lutas de verdade")
    args = ap.parse_args()
    if args.combate:
        relatorio_combate(min(args.runs, 5_000), args.seed)
        return

    forma = FormaDaRun()
    raridades = carregar_raridades(carregar_balanceamento())
    res = simular(args.runs, args.seed, forma)

    print(f"{res.runs} runs · seed {args.seed} · {forma.lutas} lutas por run")
    print(f"giros por run: {statistics.mean(res.giros_por_run):.1f}\n")

    media = res.media_despertares
    ok = "ok" if ALVO_DESPERTARES[0] <= media <= ALVO_DESPERTARES[1] else "FORA DO ALVO"
    print(f"Despertares por run: média {media:.2f} (alvo 1–2: {ok})")
    for k in range(0, 4):
        n = res.despertares[k] if k < 3 else sum(v for c, v in res.despertares.items() if c >= 3)
        rotulo = f"{k}" if k < 3 else "3+"
        print(f"  {rotulo:>2}: {100 * n / res.runs:5.1f}%")
    if res.primeira_luta_despertar:
        media_primeira = statistics.mean(res.primeira_luta_despertar)
        print(f"  primeiro Despertar, em média, na luta {media_primeira:.1f} de {forma.lutas}")
    print(f"  runs com ao menos um Divino: {100 * res.runs_com_divino / res.runs:.1f}%\n")

    total_peso = sum(r.peso for r in raridades)
    total = sum(res.raridades_sorteadas.values())
    print("Taxas por fatia sorteada   publicada   real (com pity suave)")
    for r in raridades:
        publicada = 100 * r.peso / total_peso
        real = 100 * res.raridades_sorteadas[r.id] / total
        print(f"  {r.nome:<10}               {publicada:6.1f}%    {real:6.1f}%")


def relatorio_combate(runs: int, seed: int) -> None:
    cfg = carregar_balanceamento()["combate"]
    modos = [m for m in cfg["dificuldades"] if not m.startswith("_")]
    print(f"{runs} runs por modo · seed {seed} · piloto automático\n")
    print(
        f"{'modo':<12} {'vitória':>8} {'alvo':>6} {'cai na luta':>12} "
        f"{'Carma enche':>12} {'reação':>7}"
    )
    for modo in modos:
        r = simular_com_combate(runs, seed, dificuldade=modo)
        quedas = [n for n, q in r.derrota_na_luta.items() for _ in range(q)] + [13] * r.vitorias
        alvo = cfg["dificuldades"][modo]["alvo_vitoria"]
        reacao = r.reacoes / max(1, r.golpes_perigosos_recebidos)
        print(
            f"{cfg['dificuldades'][modo]['nome']:<12} {r.vitorias / r.runs:>8.1%} {alvo:>6.0%} "
            f"{statistics.mean(quedas):>12.1f} {r.media_transbordos:>9.2f}/run {reacao:>7.0%}"
        )
    print("\n'cai na luta': média de onde as runs terminam (13 = venceu as 12).")


if __name__ == "__main__":
    main()

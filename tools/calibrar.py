"""O calibrador: o ciclo medir → ajustar → conferir, sem mão humana no meio.

    python tools/calibrar.py modos [--aplicar]   # a vida dos rivais que bate o alvo de cada modo
    python tools/calibrar.py itens               # mede todos os itens contra a régua da raridade
    python tools/calibrar.py tudo [--aplicar]    # os dois, e grava docs/CALIBRACAO.md

**Modos.** Para cada modo, mede a taxa de vitória em três valores de `vida_por_luta`
em volta do atual, ajusta uma reta (a vitória cai quase linear com a vida dos
rivais nessa faixa), acha o valor que bate `alvo_vitoria` e confere medindo de
novo. Se ainda errar por mais que a tolerância, dá mais um passo pela reta. Com
`--aplicar`, grava em `karmabound/data/balanceamento.json`.

**Itens.** Usa `medir_poder.medir` e compara cada item com a `regua` do
balanceamento (pontos de vitória por raridade). Não muda número de item sozinho:
o que mexer (dano, preço, raridade) é decisão de design, então ele só aponta o
lado. Os itens dependem da dificuldade: calibre os modos primeiro.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))

from karmabound.rodas import carregar_balanceamento  # noqa: E402

BALANCEAMENTO = RAIZ / "karmabound" / "data" / "balanceamento.json"
SEEDS = (1, 2, 3)
TOLERANCIA = 1.5  # pontos percentuais de vitória
PASSO = 0.35  # distância dos pontos medidos em volta do valor atual


def reta_ate(pontos: list[tuple[float, float]], alvo: float) -> float:
    """O x em que a reta de mínimos quadrados por `pontos` (x, y) vale `alvo`."""
    n = len(pontos)
    mx = sum(x for x, _ in pontos) / n
    my = sum(y for _, y in pontos) / n
    sxx = sum((x - mx) ** 2 for x, _ in pontos)
    if sxx == 0:
        return mx
    inclinacao = sum((x - mx) * (y - my) for x, y in pontos) / sxx
    if inclinacao == 0:
        return mx
    return mx + (alvo - my) / inclinacao


def veredito(pontos: float, faixa: tuple[float, float], folga: float = 1.0) -> str:
    """'ok' dentro da régua (com a folga do ruído), senão 'abaixo' ou 'acima'."""
    baixo, alto = faixa
    if pontos < baixo - folga:
        return "abaixo"
    if pontos > alto + folga:
        return "acima"
    return "ok"


# ----------------------------------------------------------------------- modos


def _vitorias(args: tuple[str, float, int, int]) -> tuple[str, float, int, int]:
    from karmabound.simulacao import simular_com_combate

    modo, vida, seed, runs = args
    bal = copy.deepcopy(carregar_balanceamento())
    bal["combate"]["dificuldades"][modo].setdefault("rivais", {})["vida_por_luta"] = vida
    r = simular_com_combate(runs, seed, balanceamento=bal, dificuldade=modo)
    return modo, vida, r.vitorias, r.runs


def _medir_lote(pedidos: list[tuple[str, float]], runs: int) -> dict[tuple[str, float], float]:
    tarefas = [(m, round(v, 3), s, runs) for m, v in pedidos for s in SEEDS]
    soma: dict[tuple[str, float], list[int]] = {}
    with ProcessPoolExecutor() as ex:
        for m, v, w, n in ex.map(_vitorias, tarefas):
            acc = soma.setdefault((m, v), [0, 0])
            acc[0] += w
            acc[1] += n
    return {k: 100 * w / n for k, (w, n) in soma.items()}


def calibrar_modos(runs: int, aplicar: bool) -> list[dict]:
    modos = {
        m: d
        for m, d in carregar_balanceamento()["combate"]["dificuldades"].items()
        if not m.startswith("_")
    }
    atual = {m: d["rivais"]["vida_por_luta"] for m, d in modos.items()}
    alvo = {m: 100 * d["alvo_vitoria"] for m, d in modos.items()}
    pedidos = [(m, round(atual[m] + k * PASSO, 3)) for m in modos for k in (-1, 0, 1)]
    medidas = _medir_lote(pedidos, runs)
    escolha = {}
    for m in modos:
        pontos = [(v, p) for (mm, v), p in medidas.items() if mm == m]
        escolha[m] = round(reta_ate(pontos, alvo[m]), 2)
    conferido = _medir_lote([(m, v) for m, v in escolha.items()], runs)
    resultado = []
    for m in modos:
        v = escolha[m]
        taxa = conferido[(m, round(v, 3))]
        if abs(taxa - alvo[m]) > TOLERANCIA:  # mais um passo pela reta, com o ponto novo
            pontos = [(vv, p) for (mm, vv), p in medidas.items() if mm == m] + [(v, taxa)]
            v = round(reta_ate(pontos, alvo[m]), 2)
            taxa = _medir_lote([(m, v)], runs)[(m, round(v, 3))]
        resultado.append(
            {"modo": m, "antes": atual[m], "depois": v, "vitoria": taxa, "alvo": alvo[m]}
        )
    if aplicar:
        _gravar_modos({r["modo"]: r["depois"] for r in resultado})
    return resultado


def _gravar_modos(valores: dict[str, float]) -> None:
    """Troca só os números de `vida_por_luta` de cada modo, sem reformatar o arquivo."""
    texto = BALANCEAMENTO.read_text(encoding="utf-8")
    dados = json.loads(texto)
    inicio = texto.index('"dificuldades"')
    for modo, valor in valores.items():
        antigo = dados["combate"]["dificuldades"][modo]["rivais"]["vida_por_luta"]
        i = texto.index(f'"{modo}"', inicio)
        j = texto.index('"vida_por_luta"', i)
        k = texto.index(":", j) + 1
        fim = (
            texto.index(",", k)
            if texto.find(",", k) < texto.find("\n", k)
            else texto.index("\n", k)
        )
        assert float(texto[k:fim]) == antigo, modo
        texto = texto[:k] + f" {valor:g}" + texto[fim:]
    json.loads(texto)
    BALANCEAMENTO.write_text(texto, encoding="utf-8", newline="\n")


# ----------------------------------------------------------------------- itens


def medir_itens(runs: int) -> list[dict]:
    import medir_poder

    bal = carregar_balanceamento()
    regua = {k: tuple(v) for k, v in bal["regua"].items() if not k.startswith("_")}
    rodas = medir_poder._rodas()
    itens = (
        [f.id for f in rodas["destino"].fatias]
        + [f.id for f in rodas["reliquias"].fatias]
        + [f.id for f in rodas["tecnicas"].fatias if f.combate]
    )
    raridade = {f.id: f.raridade for r in rodas.values() for f in r.fatias}
    taxas = medir_poder.medir(itens, runs, bal["combate"]["dificuldade_padrao"])
    bases = {"tecnica": "investida", "dom": "-", "reliquia": "-"}
    saida = []
    for i in itens:
        tipo = medir_poder.tipo_do_item(i)
        pts = 100 * (taxas[(tipo, i)] - taxas[(tipo, bases[tipo])])
        faixa = regua[raridade[i]]
        saida.append(
            {
                "item": i,
                "tipo": tipo,
                "raridade": raridade[i],
                "pontos": pts,
                "faixa": faixa,
                "veredito": veredito(pts, faixa),
            }
        )
    return saida


# ----------------------------------------------------------------------- relatório


def _relatorio(modos: list[dict] | None, itens: list[dict] | None) -> str:
    linhas = [
        "# Calibração",
        "",
        f"> Gerado por `python tools/calibrar.py` em {datetime.date.today().isoformat()}.",
        "",
    ]
    if modos:
        linhas += [
            "## Modos",
            "",
            "| Modo | vida por luta (antes → depois) | Vitória | Alvo |",
            "|---|---|---|---|",
        ]
        for r in modos:
            linhas.append(
                f"| {r['modo']} | {r['antes']:g} → {r['depois']:g} "
                f"| {r['vitoria']:.1f}% | {r['alvo']:.0f}% |"
            )
        linhas.append("")
    if itens:
        fora = [i for i in itens if i["veredito"] != "ok"]
        linhas += [
            "## Itens contra a régua",
            "",
            f"{len(itens) - len(fora)} de {len(itens)} dentro da régua "
            "(folga de 1 ponto para o ruído).",
            "",
            "| Item | Tipo | Raridade | Pontos | Régua | |",
            "|---|---|---|---|---|---|",
        ]
        for i in sorted(itens, key=lambda x: (x["veredito"] == "ok", x["raridade"], x["item"])):
            marca = {"ok": "✓", "abaixo": "⚠ abaixo", "acima": "⚠ acima"}[i["veredito"]]
            a, b = i["faixa"]
            linhas.append(
                f"| {i['item']} | {i['tipo']} | {i['raridade']} | {i['pontos']:+.1f} "
                f"| +{a} a +{b} | {marca} |"
            )
        linhas.append("")
    return "\n".join(linhas)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("acao", choices=("modos", "itens", "tudo"))
    ap.add_argument("--aplicar", action="store_true", help="grava os valores novos dos modos")
    ap.add_argument("--runs", type=int, default=2000, help="runs por seed (3 seeds)")
    args = ap.parse_args()
    modos = itens = None
    if args.acao in ("modos", "tudo"):
        modos = calibrar_modos(args.runs, args.aplicar)
    if args.acao in ("itens", "tudo"):
        itens = medir_itens(args.runs)
    texto = _relatorio(modos, itens)
    print(texto)
    if args.acao == "tudo":
        (RAIZ / "docs" / "CALIBRACAO.md").write_text(texto, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

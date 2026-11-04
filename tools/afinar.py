"""O afinador: python tools/afinar.py [ids...] [--rodadas N] [--runs N] [--todos] [--aplicar]

Mede itens pela régua (`medir_poder.medir`) e, para os que caem fora da faixa da
raridade, mexe no número principal do item — o dano, o efeito ou a recarga — na
direção do centro da faixa. Os preços (vida, Carma, sangria, Velocidade…) nunca
mudam: o preço é decisão de design. Repete por algumas rodadas, medindo de novo só
o que mexeu. O passo é amortecido (raiz da razão até o centro), e um passo que deixa
o item mais longe da faixa é desfeito — o item para ali. Com `--aplicar`, grava em
karmabound/data/rodas.json; sem ele, só mostra.

Sem ids, afina o que a expansão trouxe (tudo que tem marcador `{` no texto, porque o
texto acompanha o número). `--todos` inclui os itens antigos.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))

from medir_poder import medir, tipo_do_item  # noqa: E402

from karmabound.rodas import carregar_balanceamento  # noqa: E402

RODAS = RAIZ / "karmabound" / "data" / "rodas.json"
RODA_DO_TIPO = {
    "tecnica": "tecnicas", "dom": "destino", "reliquia": "reliquias", "linhagem": "linhagem",
}

# Números de técnica que são força (na ordem em que o afinador prefere mexer)
FORCA_TECNICA = (
    "dano", "bomba", "bloqueio", "cura", "regenerar", "sangrar", "fortalecer", "revide",
    "enfraquecer", "acumula", "combo", "detonar", "instinto", "espelho", "silenciar",
    "desarmar", "cegar", "expor", "foco", "intocavel", "fera", "acelerar",
)
FLOAT_TECNICA = ("drenar", "gravidade", "desespero", "executar")
# Efeitos que são força quando sobem (os multiplicadores contam pelo quanto passam de 1)
FORCA_EFEITO = (
    "bonus_dano", "basico_dano", "vida_max", "bloqueio_inicio", "ultimo_suspiro", "vida_cheia",
    "revide_permanente", "regen", "cura_inicio", "crescer", "sangrar", "sutileza", "drenar",
    "executar", "primeiro_golpe", "dano_marcado", "chance_reliquia", "esquiva", "sombra",
    "furia", "carma_por_vitoria", "vida_por_vitoria",
)
MULT_ACIMA = ("dano_mult", "dano_tecnicas_mult", "cura_mult", "bloqueio_mult", "vida_max_mult",
              "dano_chefe_mult", "fator_evolucao", "carma_mult")
MULT_ABAIXO = ("dano_recebido_mult",)


def _escalar_int(v: int, f: float) -> int:
    novo = round(v * f)
    if novo == v:
        novo = v + (1 if f > 1 else -1)
    return max(1, novo)


def ajustar_tecnica(c: dict, f: float) -> str:
    """Mexe numa técnica: o maior número de força (se for grande o bastante), senão a recarga."""
    for campo in FORCA_TECNICA:
        v = c.get(campo, 0)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 3:
            c[campo] = _escalar_int(v, f)
            return f"{campo} {v}→{c[campo]}"
    for campo in FLOAT_TECNICA:
        v = c.get(campo, 0.0)
        if v:
            c[campo] = round(min(1.0, v * f), 2)
            return f"{campo} {v}→{c[campo]}"
    rec = c.get("recarga", 0)
    if rec and rec != 99:
        c["recarga"] = max(1, rec + (-1 if f > 1 else 1))
        return f"recarga {rec}→{c['recarga']}"
    for campo in FORCA_TECNICA:  # números pequenos: um passo de cada vez
        v = c.get(campo, 0)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            c[campo] = max(1, v + (1 if f > 1 else -1))
            return f"{campo} {v}→{c[campo]}"
    return ""


def ajustar_efeito(e: dict, f: float) -> str:
    for campo in FORCA_EFEITO:
        v = e.get(campo)
        if isinstance(v, bool) or not v or v < 0:
            continue
        if isinstance(v, int) and campo not in ("drenar", "executar", "primeiro_golpe"):
            e[campo] = _escalar_int(v, f)
        else:
            e[campo] = round(v * f, 3)
        return f"{campo} {v}→{e[campo]}"
    for campo in MULT_ACIMA:
        v = e.get(campo)
        if v and v > 1:
            e[campo] = round(1 + (v - 1) * f, 3)
            return f"{campo} {v}→{e[campo]}"
    for campo in MULT_ABAIXO:
        v = e.get(campo)
        if v and v < 1:
            e[campo] = round(1 - (1 - v) * f, 3)
            return f"{campo} {v}→{e[campo]}"
    return ""


def distancia(pts: float, lo: float, hi: float) -> float:
    return 0.0 if lo <= pts <= hi else min(abs(pts - lo), abs(pts - hi))


def _numeros(fatia: dict) -> dict:
    return {k: copy.deepcopy(fatia[k]) for k in ("combate", "efeito", "tecnica") if k in fatia}


def ajustar(fatia: dict, f: float) -> str:
    if "combate" in fatia:
        return ajustar_tecnica(fatia["combate"], f)
    feito = ajustar_efeito(fatia["efeito"], f) if fatia.get("efeito") else ""
    if not feito and fatia.get("tecnica"):
        feito = ajustar_tecnica(fatia["tecnica"], f)
    return feito


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("itens", nargs="*")
    ap.add_argument("--rodadas", type=int, default=3)
    ap.add_argument("--runs", type=int, default=2000, help="runs por seed (3 seeds)")
    ap.add_argument("--dificuldade", default="dificil")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    regua = carregar_balanceamento()["regua"]
    dados = json.loads(RODAS.read_text(encoding="utf-8"))
    fatias = {
        f["id"]: f
        for r in dados["rodas"]
        if r["id"] in RODA_DO_TIPO.values()
        for f in r["fatias"]
    }
    itens = args.itens or [
        i for i, f in fatias.items() if args.todos or "{" in f.get("texto", "")
    ]
    itens = [i for i in itens if i in fatias]
    pendentes = list(itens)
    historico: dict[str, list[str]] = {}
    finais: dict[str, float] = {}
    anterior: dict[str, tuple[float, dict]] = {}  # a última medição e os números de então
    for rodada in range(1, args.rodadas + 1):
        if not pendentes:
            break
        if args.aplicar:
            RODAS.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", "utf-8")
        taxas = medir(pendentes, args.runs, args.dificuldade)
        base = {t: taxas.get((t, b)) for t, b in
                (("tecnica", "investida"), ("dom", "-"), ("reliquia", "-"), ("linhagem", "-"))}
        proximos = []
        print(f"\n— rodada {rodada}: {len(pendentes)} itens")
        for i in pendentes:
            tipo = tipo_do_item(i)
            pts = (taxas[(tipo, i)] - base[tipo]) * 100
            finais[i] = pts
            lo, hi = regua[fatias[i]["raridade"]]
            if i in anterior and distancia(pts, lo, hi) > distancia(anterior[i][0], lo, hi) + 0.5:
                fatias[i].update(copy.deepcopy(anterior[i][1]))  # piorou: desfaz e para
                finais[i] = anterior[i][0]
                historico.setdefault(i, []).append(f"{pts:+.1f} (piorou, desfeito)")
                print(f"  {i:<28} {fatias[i]['raridade']:<8} {pts:+6.1f}  piorou: desfeito")
                continue
            if lo <= pts <= hi:
                continue
            anterior[i] = (pts, _numeros(fatias[i]))
            centro = (lo + hi) / 2
            f = max(0.7, min(1.45, (centro / pts) ** 0.6)) if pts > 0.5 else 1.4
            antes = json.dumps(_numeros(fatias[i]), sort_keys=True)
            mudou = ajustar(fatias[i], f)
            if json.dumps(_numeros(fatias[i]), sort_keys=True) == antes:
                mudou = ""  # já no mínimo: nada mudou de fato
            historico.setdefault(i, []).append(f"{pts:+.1f} ({mudou or 'nada a mexer'})")
            print(f"  {i:<28} {fatias[i]['raridade']:<8} {pts:+6.1f}  [{lo}, {hi}]  {mudou}")
            if mudou:
                proximos.append(i)
        pendentes = proximos
    if args.aplicar:
        RODAS.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", "utf-8")
    fora = {i: p for i, p in finais.items() if not (
        regua[fatias[i]["raridade"]][0] - 1 <= p <= regua[fatias[i]["raridade"]][1] + 1)}
    print(f"\n{len(itens)} itens; fora da régua (±1) na última medição: {len(fora)}")
    for i, p in sorted(fora.items(), key=lambda x: x[1]):
        print(f"  {i:<28} {fatias[i]['raridade']:<8} {p:+6.1f}  {' · '.join(historico.get(i, []))}")


if __name__ == "__main__":
    main()

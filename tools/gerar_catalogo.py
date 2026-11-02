"""Gera docs/CATALOGO.md a partir dos dados: python tools/gerar_catalogo.py

O catálogo é a página para ler o conteúdo do jogo (rodas, técnicas, votos,
modos). Os JSON em karmabound/data/ continuam sendo a fonte; edite lá e rode
este script. O teste `test_catalogo_em_dia` falha se esquecer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "karmabound" / "data"
DESTINO = RAIZ / "docs" / "CATALOGO.md"

CAMPOS_COMBATE = [
    ("dano", "dano"),
    ("golpes", "golpes"),
    ("bloqueio", "bloqueio"),
    ("revide", "revide"),
    ("custo_vida", "custo de vida"),
    ("marca", "marca"),
    ("eco", "você sofre por turno"),
    ("fortalecer", "fortalecer"),
    ("dano_por_carma", "dano × Carma"),
    ("consome_carma", "consome o Carma"),
    ("consome_tecnica", "destrói outra técnica sua"),
    ("cresce_ao_consumir", "cresce por técnica consumida"),
    ("perfura", "atravessa bloqueio"),
    ("absoluto", "atravessa bloqueio, escudo e esquiva"),
    ("critico", "chance de ×2,5"),
    ("sempre_surpresa", "sempre surpresa"),
    ("selar", "sela a ação do rival por"),
    ("cura", "cura"),
    ("dano_por_dor", "dano × dor sofrida"),
    ("atordoar", "o rival perde turnos:"),
    ("inicia_em_recarga", "começa a luta em recarga"),
]


def _efeito(c: dict) -> str:
    partes = []
    for k, rot in CAMPOS_COMBATE:
        v = c.get(k)
        if v is True:
            partes.append(rot)
        elif v:
            partes.append(f"{rot} {v:g}" if isinstance(v, float) else f"{rot} {v}")
    return ", ".join(partes)


def _ler(nome: str) -> dict:
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


def _pct(v: float) -> str:
    return f"{v:.0%}"


def gerar() -> str:
    bal, rodas, votos = _ler("balanceamento.json"), _ler("rodas.json"), _ler("votos.json")
    raridades = {r["id"]: r for r in bal["raridades"]}
    total = sum(r["peso"] for r in bal["raridades"])
    out = [
        "# Catálogo do Karmabound",
        "",
        "> Gerado por `python tools/gerar_catalogo.py` a partir de `karmabound/data/`. "
        "Não edite aqui: edite os JSON e gere de novo.",
        "",
        "## Raridades",
        "",
        "| Raridade | Chance publicada | Carma por giro |",
        "|---|---|---|",
    ]
    for r in bal["raridades"]:
        carma = bal["carma"]["por_giro"].get(r["id"], 0)
        out.append(f"| {r['nome']} | {_pct(r['peso'] / total)} | {carma:+g} |")

    for roda in rodas["rodas"]:
        modo = "gira e aceita" if roda["modo"] == "aceita" else f"gira {roda['opcoes']}, escolhe 1"
        out += ["", f"## {roda['kanji']} {roda['nome']} ({modo})", ""]
        tecnicas = any("combate" in f for f in roda["fatias"])
        if tecnicas:
            out += [
                "| | Técnica | Raridade | Tipo | Efeito | Recarga | Sutileza | Perigosa | Origem |",
                "|---|---|---|---|---|---|---|---|---|",
            ]
        else:
            out += ["| | Nome | Raridade | Texto | Origem |", "|---|---|---|---|---|"]
        for f in roda["fatias"]:
            rar = raridades[f["raridade"]]["nome"]
            if tecnicas:
                c = f.get("combate", {})
                efeito = _efeito(c)
                out.append(
                    f"| {f['kanji']} | {f['nome']} | {rar} | {c.get('tipo', '')} | {efeito} | "
                    f"{c.get('recarga', 0)} | {c.get('sutileza', 0)} | "
                    f"{'sim' if c.get('perigosa') else ''} | {f.get('origem', '')} |"
                )
            else:
                out.append(
                    f"| {f['kanji']} | {f['nome']} | {rar} | {f.get('texto', '')} | "
                    f"{f.get('origem', '')} |"
                )

    b = votos["bonus"]
    out += [
        "",
        "## 誓 Votos vinculativos (Juramento)",
        "",
        f"Até {votos['limite_ativos']} votos ativos; quebrar um voto libera o espaço. "
        "O valor de cada restrição é medido contra o seu build na hora, por simulação.",
        "",
        f"**Pontos** = S × (1 + S ÷ {b['K']}) × duração × categoria. S é o sacrifício "
        "(lutas vencidas a menos no resto da run), com **retorno decrescente por restrição**: "
        f"cada uma credita no máximo {b['teto_por_restricao']:g} luta. Para ir além, junte "
        "restrições diferentes.",
        "",
        f"**Preço de um ganho** = benefício medido do 1º nível × número do nível (o 2º nível "
        f"custa o dobro do 1º) × câmbio {votos['precos']['cambio']:g}. Exclusivos custam "
        f"×{votos['precos']['exclusivo']:g}. O câmbio escala o poder total dos votos.",
        "",
        "| Duração | Multiplicador |",
        "|---|---|",
    ]
    out += [f"| {d['nome']} | ×{d['multiplicador']:g} |" for d in b["duracao"].values()]
    out += ["", "| Categoria da restrição | Multiplicador |", "|---|---|"]
    out += [f"| {c} | ×{m:g} |" for c, m in b["categoria"].items()]
    q = votos["quebra"]
    out += [
        "",
        f"**Quebrar um voto:** perde os ganhos dele, perde {_pct(q['vida_atual_perdida'])} da vida "
        f"atual{', o Carma zera' if q['zera_carma'] else ''}, e jura um voto de quebra. "
        "Quebrar o voto de quebra encerra a run.",
    ]
    out += ["", "### Restrições", "", "| | Nome | Categoria | Efeito |", "|---|---|---|---|"]
    for x in votos["restricoes"]:
        out.append(f"| {x['kanji']} | {x['nome']} | {x['categoria']} | {x['texto']} |")
    out += [
        "",
        "### Ganhos",
        "",
        "| | Nome | Categoria | Efeito | Níveis |",
        "|---|---|---|---|---|",
    ]
    for x in votos["ganhos"]:
        out.append(
            f"| {x['kanji']} | {x['nome']} | {x['categoria']} | {x['texto']} | "
            f"{x.get('niveis', 1)} |"
        )

    c = bal["combate"]
    out += [
        "",
        "## Modos de dificuldade",
        "",
        "| Modo | Vitória alvo (piloto) | Rival +vida/luta | Chefe | Sua vida |",
        "|---|---|---|---|---|",
    ]
    for mid, m in c["dificuldades"].items():
        if mid.startswith("_"):
            continue
        padrao = " (padrão)" if mid == c["dificuldade_padrao"] else ""
        riv = {**c["rivais"], **m.get("rivais", {})}
        jog = {**c["jogador"], **m.get("jogador", {})}
        out.append(
            f"| {m['nome']}{padrao} | {_pct(m['alvo_vitoria'])} | {riv['vida_base']} "
            f"+{riv['vida_por_luta']:g} | ×{riv['chefe_multiplicador']:g} | {jog['vida']} |"
        )
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    texto = gerar()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8", newline="\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"gerado: {DESTINO.relative_to(RAIZ)}")

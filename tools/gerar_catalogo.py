"""Gera docs/CATALOGO.md e docs/wiki.html a partir dos dados: python tools/gerar_catalogo.py

O catálogo é a página para ler o conteúdo do jogo (rodas, técnicas, votos,
modos); a wiki mostra o mesmo conteúdo em fichas, com busca e filtro. Os JSON em
karmabound/data/ continuam sendo a fonte; edite lá e rode este script. Os testes
`test_catalogo_em_dia` e `test_wiki_em_dia` falham se esquecer.
"""

from __future__ import annotations

import html
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from karmabound.rodas import _valores, preencher  # noqa: E402

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
            texto = preencher(f.get("texto", ""), _valores(f))
            if tecnicas:
                c = f.get("combate", {})
                efeito = texto or _efeito(c)
                out.append(
                    f"| {f['kanji']} | {f['nome']} | {rar} | {c.get('tipo', '')} | {efeito} | "
                    f"{c.get('recarga', 0)} | {c.get('sutileza', 0)} | "
                    f"{'sim' if c.get('perigosa') else ''} | {f.get('origem', '')} |"
                )
            else:
                out.append(
                    f"| {f['kanji']} | {f['nome']} | {rar} | {texto} | {f.get('origem', '')} |"
                )

    b = votos["bonus"]
    out += [
        "",
        "## 誓 Votos vinculativos (o Altar)",
        "",
        "O Altar dos Votos abre no fim de cada capítulo, fora da luta (dá para recusar). "
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

    luta = _ler("votos_luta.json")["votos"]
    tipos = {"promessa": "Promessa", "revelacao": "Revelação", "selo": "Selo"}
    out += [
        "",
        "## 約 Votos de luta",
        "",
        "Toda luta oferece um, sorteado; jurar não gasta o turno (uma vez por luta).",
        "",
        "| | Nome | Tipo | Texto | Origem |",
        "|---|---|---|---|---|",
    ]
    for x in luta:
        out.append(
            f"| {x['kanji']} | {x['nome']} | {tipos[x['tipo']]} | {x['texto']} | {x['origem']} |"
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


# --------------------------------------------------------------------------
# A wiki: docs/wiki.html, uma ficha por item, com busca e filtro de raridade.
# --------------------------------------------------------------------------

DESTINO_WIKI = RAIZ / "docs" / "wiki.html"

TIPOS_TECNICA = {
    "ataque": "Ataque",
    "defesa": "Defesa",
    "maldita": "Maldita",
    "modo": "Transformação",
}
TIPOS_VOTO_LUTA = {"promessa": "Promessa", "revelacao": "Revelação", "selo": "Selo"}

INTRO_RODA = {
    "linhagem": "O primeiro giro da run: de que sangue você vem. Um passivo, às vezes uma "
    "técnica de família.",
    "destino": "O Dom inato, o segundo giro da run. Soma com a Linhagem.",
    "tecnicas": "Golpes, defesas e técnicas malditas. Os rivais sorteiam das mesmas listas.",
    "arco": "A regra do capítulo, girada no começo de cada um.",
    "reliquias": "Itens. Duplicatas evoluem o que você já tem.",
    "despertar": "Quando o Carma transborda, na luta. Todos são Divinos.",
}


def _h(s: object) -> str:
    return html.escape(str(s), quote=True)


def _norm(s: str) -> str:
    sem = unicodedata.normalize("NFD", s)
    return "".join(c for c in sem if not unicodedata.combining(c)).lower()


def _chips_tecnica(c: dict) -> list[str]:
    chips = [TIPOS_TECNICA.get(c.get("tipo", ""), c.get("tipo", ""))]
    if c.get("modo"):
        chips.append(f"dura {c['modo']['turnos']} turnos")
    if c.get("livre"):
        chips.append("não gasta o turno")
    rec = c.get("recarga", 0)
    chips.append("1× por luta" if rec >= 99 else f"recarga {rec}" if rec else "sem recarga")
    if c.get("sutileza"):
        chips.append(f"sutileza {c['sutileza']}")
    if c.get("perigosa"):
        chips.append("perigosa")
    return [x for x in chips if x]


ROTULO_RODA = {
    "linhagem": "Linhagem",
    "destino": "Dom",
    "tecnicas": "Técnica",
    "arco": "Arco",
    "reliquias": "Relíquia",
    "despertar": "Despertar",
    "chefes": "Técnica de chefe",
    "votos-luta": "Voto de luta",
}


def anime_de(origem: str) -> str:
    """'Amaterasu (Itachi) · Naruto' -> 'Naruto'."""
    return origem.rsplit(" · ", 1)[1].strip() if " · " in origem else ""


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in _norm(s)).strip("-")


@dataclass
class _Item:
    secao: str
    item: dict
    texto: str
    rotulo: str = ""
    rar: dict | None = None
    chips: tuple[str, ...] = ()

    @property
    def anime(self) -> str:
        return anime_de(self.item.get("origem", ""))


def _ficha(x: _Item, prefixo: str = "", rotulo: str | None = None) -> str:
    rar_id = x.rar["id"] if x.rar else ""
    rot = x.rotulo if rotulo is None else rotulo
    linha = " · ".join(p for p in (x.rar["nome"] if x.rar else "", rot) if p)
    origem = x.item.get("origem", "")
    busca = _norm(" ".join([x.item["nome"], x.item["id"], x.texto, origem, linha, *x.chips]))
    ancora = f"{prefixo}{x.secao}-{_h(x.item['id'])}"
    partes = [
        f'<article class="card{" r-" + rar_id if rar_id else ""}" id="{ancora}" '
        f'data-rar="{rar_id}" data-anime="{_slug(x.anime)}" data-busca="{_h(busca)}">',
        f'<div class="k">{_h(x.item.get("kanji", ""))}</div>',
        "<div>",
        f'<h3><a href="#{ancora}">{_h(x.item["nome"])}</a></h3>',
        f'<p class="rot">{_h(linha)}</p>' if linha else "",
        f"<p>{_h(x.texto)}</p>" if x.texto else "",
    ]
    if x.chips:
        partes.append(
            '<ul class="chips">' + "".join(f"<li>{_h(c)}</li>" for c in x.chips) + "</ul>"
        )
    if origem:
        partes.append(f'<p class="origem">{_h(origem)}</p>')
    partes += ["</div>", "</article>"]
    return "".join(p for p in partes if p)


def _secao(sid: str, kanji: str, nome: str, intro: str, fichas: list[str]) -> str:
    return (
        f'<section class="secao" id="{sid}">\n'
        f'<h2><span class="kanji">{_h(kanji)}</span>{_h(nome)} '
        f'<small>(<span class="conta">{len(fichas)}</span>)</small></h2>\n'
        + (f'<p class="intro">{intro}</p>\n' if intro else "")
        + '<div class="grade">\n'
        + "\n".join(fichas)
        + "\n</div>\n</section>"
    )


def _indice(nav_id: str, secoes: list[tuple[str, str, str, int]], escondido: bool) -> str:
    itens = "".join(
        f'<li><a href="#{sid}">'
        + (f'<span class="kanji">{_h(k)}</span>' if k else "")
        + f'{_h(n)} <span class="conta-nav" data-de="{sid}">{q}</span></a></li>'
        for sid, k, n, q in secoes
    )
    return (
        f'<nav id="{nav_id}"{" hidden" if escondido else ""}><ul class="indice">{itens}</ul></nav>'
    )


def _itens_da_wiki() -> tuple[list[tuple[str, str, str, str, list[_Item]]], dict, dict]:
    """As seções da wiki (id, kanji, nome, intro, itens), as raridades e os votos."""
    bal, rodas = _ler("balanceamento.json"), _ler("rodas.json")
    votos, luta, chefes = _ler("votos.json"), _ler("votos_luta.json"), _ler("chefes.json")
    raridades = {r["id"]: r for r in bal["raridades"]}
    secoes = []
    for roda in rodas["rodas"]:
        modo = (
            "Gira e aceita." if roda["modo"] == "aceita" else f"Gira {roda['opcoes']}, escolhe 1."
        )
        itens = []
        for f in roda["fatias"]:
            if "combate" in f:
                chips = _chips_tecnica(f["combate"])
            elif "tecnica" in f:
                chips = ["técnica", *_chips_tecnica(f["tecnica"])]
            else:
                chips = []
            texto = preencher(f.get("texto", ""), _valores(f))
            itens.append(_Item(roda["id"], f, texto, "", raridades[f["raridade"]], tuple(chips)))
        intro = f"{_h(INTRO_RODA.get(roda['id'], ''))} <strong>{modo}</strong>"
        secoes.append((roda["id"], roda["kanji"], roda["nome"], intro, itens))
    itens = [
        _Item(
            "chefes",
            t,
            t["texto"],
            "",
            raridades[t["raridade"]],
            tuple(_chips_tecnica(t["combate"])),
        )
        for t in chefes["tecnicas"]
    ]
    secoes.append(
        (
            "chefes",
            "鬼",
            "Técnicas de chefe",
            "A assinatura de cada chefe: uma é sorteada e somada às técnicas dele.",
            itens,
        )
    )
    itens = [
        _Item("restricoes", x, x["texto"], f"Restrição {x['categoria']}")
        for x in votos["restricoes"]
    ]
    secoes.append(
        (
            "restricoes",
            "縛",
            "Votos: restrições",
            "O que você jura abrir mão no Altar dos Votos, que abre no fim de cada capítulo "
            f"(até {votos['limite_ativos']} votos ativos). O valor de cada uma é medido "
            "contra o seu build na hora. As regras de pontos estão no "
            '<a href="index.html#votos">manual</a>.',
            itens,
        )
    )
    itens = []
    for x in votos["ganhos"]:
        niveis = x.get("niveis", 1)
        chips = (f"até {niveis} níveis",) if niveis > 1 else ()
        itens.append(_Item("ganhos", x, x["texto"], f"Ganho {x['categoria']}", chips=chips))
    secoes.append(
        (
            "ganhos",
            "誓",
            "Votos: ganhos",
            "O que os pontos do voto compram. O 2º nível custa o dobro do 1º; exclusivos custam "
            f"×{votos['precos']['exclusivo']:g}.",
            itens,
        )
    )
    itens = [_Item("votos-luta", x, x["texto"], TIPOS_VOTO_LUTA[x["tipo"]]) for x in luta["votos"]]
    secoes.append(
        (
            "votos-luta",
            "約",
            "Votos de luta",
            "Toda luta oferece um, sorteado; jurar não gasta o turno (uma vez por luta). "
            "<strong>Promessa</strong> cobra uma meta, <strong>Revelação</strong> mostra algo do "
            "rival, <strong>Selo</strong> troca uma regra da luta.",
            itens,
        )
    )
    return secoes, bal, votos


def gerar_wiki() -> str:
    secoes, bal, _ = _itens_da_wiki()
    total = sum(r["peso"] for r in bal["raridades"])

    # por roda
    corpo_roda, nav_roda = [], []
    for sid, kanji, nome, intro, itens in secoes:
        corpo_roda.append(_secao(sid, kanji, nome, intro, [_ficha(x) for x in itens]))
        nav_roda.append((sid, kanji, nome, len(itens)))

    # por anime: tudo que tem origem, agrupado pela obra (a mais citada primeiro)
    por_anime: dict[str, list[_Item]] = {}
    for *_, itens in secoes:
        for x in itens:
            if x.anime:
                por_anime.setdefault(x.anime, []).append(x)
    ordem = sorted(por_anime, key=lambda a: (-len(por_anime[a]), _norm(a)))
    corpo_anime, nav_anime = [], []
    for a in ordem:
        sid = f"anime-{_slug(a)}"
        fichas = [_ficha(x, "a-", ROTULO_RODA.get(x.secao, x.rotulo)) for x in por_anime[a]]
        rodas_de = sorted({ROTULO_RODA.get(x.secao, x.rotulo) for x in por_anime[a]})
        corpo_anime.append(_secao(sid, "", a, _h(", ".join(rodas_de)) + ".", fichas))
        nav_anime.append((sid, "", a, len(fichas)))

    filtros = "".join(
        f'<button type="button" class="filtro r-{r["id"]}" data-filtro="{r["id"]}" '
        f'aria-pressed="false">{_h(r["nome"])} <span>{_pct(r["peso"] / total)}</span></button>'
        for r in bal["raridades"]
    )
    opcoes_anime = "".join(
        f'<option value="{_slug(a)}">{_h(a)} ({len(por_anime[a])})</option>' for a in ordem
    )
    total_itens = sum(q for *_, q in nav_roda)
    return (
        WIKI_TOPO
        + f'<p class="lead">Todos os {total_itens} itens do jogo, um por ficha: linhagens, '
        "Dons, técnicas, arcos, relíquias, Despertares e votos, de "
        f"{len(ordem)} animes. Para entender as regras, "
        'leia o <a href="index.html">manual</a>.</p>\n'
        '<div class="vistas" role="group" aria-label="Agrupar">'
        '<button type="button" data-vista="roda" aria-pressed="true">Por roda</button>'
        '<button type="button" data-vista="anime" aria-pressed="false">Por anime</button></div>\n'
        + _indice("nav-roda", nav_roda, False)
        + "\n"
        + _indice("nav-anime", nav_anime, True)
        + "\n</header>\n"
        '<div class="barra">\n'
        '<input id="busca" type="search" placeholder="Buscar por nome, efeito ou origem…" '
        'aria-label="Buscar">\n'
        '<select id="anime" aria-label="Anime"><option value="">Todos os animes</option>'
        f"{opcoes_anime}</select>\n"
        f'<div class="filtros" role="group" aria-label="Raridade">{filtros}</div>\n'
        "</div>\n"
        '<p id="nada" class="vazio" hidden>Nada encontrado com essa busca e esse filtro.</p>\n'
        '<div id="por-roda">\n' + "\n\n".join(corpo_roda) + "\n</div>\n"
        '<div id="por-anime" hidden>\n' + "\n\n".join(corpo_anime) + "\n</div>" + WIKI_FIM
    )


WIKI_TOPO = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wiki de Karmabound</title>
<!-- Gerado por python tools/gerar_catalogo.py a partir de karmabound/data/. Não edite aqui. -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Yuji+Syuku&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
  :root {
    --fundo: #141210; --laca: #1f1c19; --laca-2: #2a2622; --linha: #3a3530;
    --tinta: #d8cfc0; --suave: #a39a8c; --fraca: #6f675c; --sangue: #c41e24;
    --cinza: #8a8a8a; --rar-sangue: #c43a3e; --maldito: #9d5ce0; --ouro: #e9c46a;
  }
  @media (prefers-color-scheme: light) {
    :root {
      --fundo: #efe8da; --laca: #f7f2e8; --laca-2: #e6dccb; --linha: #cbbfa9;
      --tinta: #1c1915; --suave: #4f483e; --fraca: #81786a; --sangue: #9e1418;
      --cinza: #6b6b6b; --rar-sangue: #a4161a; --maldito: #6a2fb0; --ouro: #8a6113;
    }
  }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  html { scroll-behavior: smooth; scroll-padding-top: 120px; }
  body { margin: 0; background: var(--fundo); color: var(--tinta);
    font: 17px/1.6 "Source Serif 4", Georgia, serif; }
  main { max-width: 1120px; margin: 0 auto; padding: 0 16px 96px; }
  h1, h2, h3, .kanji, .k { font-family: "Yuji Syuku", serif; font-weight: 400; }
  h1 { font-size: clamp(44px, 8vw, 72px); line-height: 1; margin: 0; }
  h2 { font-size: 28px; line-height: 1.25; margin: 64px 0 4px; }
  h2 .kanji { color: var(--sangue); margin-right: .35em; }
  h2 small { font: 16px "Source Serif 4", serif; color: var(--fraca); }
  a { color: var(--ouro); }
  .heroi { padding: 56px 0 20px; }
  .heroi .selo { font-size: 22px; color: var(--ouro); letter-spacing: .3em; }
  .lead { font-size: 19px; color: var(--suave); max-width: 40em; }
  .intro { color: var(--suave); margin: 4px 0 18px; max-width: 48em; }
  .indice { list-style: none; padding: 0; margin: 20px 0 0;
    display: flex; flex-wrap: wrap; gap: 8px; }
  .indice a { display: inline-flex; gap: 6px; align-items: baseline; padding: 4px 12px;
    border: 1px solid var(--linha); border-radius: 999px; color: var(--suave);
    text-decoration: none; font-size: 15px; background: var(--laca); }
  .indice a:hover { color: var(--tinta); border-color: var(--suave); }
  .indice .kanji { color: var(--sangue); }
  .conta-nav { font: 12px "IBM Plex Mono", monospace; color: var(--fraca); }
  .indice a.zerado { opacity: .4; }
  .barra { position: sticky; top: 0; z-index: 2; background: var(--fundo);
    padding: 12px 0; border-bottom: 1px solid var(--linha);
    display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
  #busca { flex: 1 1 260px; min-width: 0; font: 16px "Source Serif 4", serif;
    color: var(--tinta); background: var(--laca); border: 1px solid var(--linha);
    border-radius: 8px; padding: 9px 12px; }
  #busca:focus { outline: 2px solid var(--ouro); outline-offset: 1px; }
  .filtros { display: flex; flex-wrap: wrap; gap: 6px; }
  .filtro { font: 15px "Source Serif 4", serif; background: var(--laca); color: inherit;
    border: 1px solid var(--linha); border-radius: 999px; padding: 6px 12px; cursor: pointer; }
  .filtro span { font: 12px "IBM Plex Mono", monospace; color: var(--fraca); }
  .filtro[aria-pressed="true"] { border-color: currentColor; background: var(--laca-2); }
  .grade { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
  .card { display: grid; grid-template-columns: 44px 1fr; gap: 12px; padding: 14px 16px;
    background: var(--laca); border: 1px solid var(--linha); border-left: 3px solid var(--linha);
    border-radius: 8px; }
  .card:target { outline: 2px solid var(--ouro); }
  .card .k { font-size: 32px; line-height: 1.1; text-align: center; color: var(--suave); }
  .card h3 { font-size: 20px; margin: 0; line-height: 1.3; }
  .card h3 a { color: var(--tinta); text-decoration: none; }
  .card h3 a:hover { text-decoration: underline; }
  .card p { margin: 6px 0 0; font-size: 16px; }
  .card .rot { margin: 0; font-size: 14px; color: var(--fraca); }
  .card .origem { font-size: 14px; color: var(--fraca); font-style: italic; }
  .chips { list-style: none; padding: 0; margin: 8px 0 0;
    display: flex; flex-wrap: wrap; gap: 4px; }
  .chips li { font: 12px/1.6 "IBM Plex Mono", monospace; background: var(--laca-2);
    color: var(--suave); padding: 0 8px; border-radius: 4px; }
  .r-cinza { --rar: var(--cinza); } .r-sangue { --rar: var(--rar-sangue); }
  .r-maldito { --rar: var(--maldito); } .r-divino { --rar: var(--ouro); }
  .card[class*=" r-"] { border-left-color: var(--rar); }
  .card[class*=" r-"] .k, .card[class*=" r-"] .rot, .filtro[class*=" r-"] { color: var(--rar); }
  .vazio { color: var(--fraca); font-style: italic; margin: 40px 0; }
  .vistas { display: inline-flex; margin-top: 20px; border: 1px solid var(--linha);
    border-radius: 999px; overflow: hidden; }
  .vistas button { font: 15px "Source Serif 4", serif; color: var(--suave);
    background: var(--laca); border: 0; padding: 6px 16px; cursor: pointer; }
  .vistas button[aria-pressed="true"] { background: var(--laca-2); color: var(--tinta);
    box-shadow: inset 0 -2px 0 var(--ouro); }
  #anime { font: 15px "Source Serif 4", serif; color: var(--tinta); background: var(--laca);
    border: 1px solid var(--linha); border-radius: 8px; padding: 8px 10px; max-width: 100%; }
  footer { margin-top: 96px; padding-top: 20px; border-top: 1px solid var(--linha);
    font-size: 15px; color: var(--fraca); }
</style>
</head>
<body>
<main>
<header class="heroi">
<div class="selo">業 · 命 · 覚醒</div>
<h1>Wiki de Karmabound</h1>
"""

WIKI_FIM = """

<footer>Gerada por <code>python tools/gerar_catalogo.py</code> a partir de
<code>karmabound/data/</code>; os números são os do jogo. · <a href="index.html">Manual</a></footer>
</main>
<script>
(() => {
  const norm = s => s.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").toLowerCase();
  const $ = s => document.querySelector(s);
  const busca = $("#busca"), anime = $("#anime"), nada = $("#nada");
  const botoes = [...document.querySelectorAll("[data-filtro]")];
  const alternar = [...document.querySelectorAll("[data-vista]")];
  const vistas = { roda: $("#por-roda"), anime: $("#por-anime") };
  const navs = { roda: $("#nav-roda"), anime: $("#nav-anime") };
  const rars = new Set();
  let vista = "roda";
  function filtrar() {
    const termos = norm(busca.value).split(/\\s+/).filter(Boolean);
    const a = anime.value;
    let total = 0;
    vistas[vista].querySelectorAll("section.secao").forEach(sec => {
      let n = 0;
      sec.querySelectorAll(".card").forEach(c => {
        const ok = termos.every(t => c.dataset.busca.includes(t))
          && (!rars.size || rars.has(c.dataset.rar))
          && (!a || c.dataset.anime === a);
        c.hidden = !ok;
        n += ok;
      });
      sec.querySelector(".conta").textContent = n;
      sec.hidden = n === 0;
      total += n;
      const nav = navs[vista].querySelector(`.conta-nav[data-de="${sec.id}"]`);
      nav.textContent = n;
      nav.closest("a").classList.toggle("zerado", n === 0);
    });
    nada.hidden = total > 0;
  }
  function mostrar(v) {
    vista = v;
    for (const k of Object.keys(vistas)) {
      vistas[k].hidden = k !== v;
      navs[k].hidden = k !== v;
    }
    alternar.forEach(b => b.setAttribute("aria-pressed", b.dataset.vista === v));
    filtrar();
  }
  busca.addEventListener("input", filtrar);
  anime.addEventListener("change", filtrar);
  alternar.forEach(b => b.addEventListener("click", () => mostrar(b.dataset.vista)));
  botoes.forEach(b => b.addEventListener("click", () => {
    const r = b.dataset.filtro;
    rars.has(r) ? rars.delete(r) : rars.add(r);
    b.setAttribute("aria-pressed", rars.has(r));
    filtrar();
  }));
  const h = location.hash;
  if (h.startsWith("#anime-") || h.startsWith("#a-")) {
    mostrar("anime");
    const alvo = document.getElementById(h.slice(1));
    if (alvo) alvo.scrollIntoView();
  } else if (busca.value || anime.value) {
    filtrar();
  }
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    texto = gerar()
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8", newline="\n")
    DESTINO_WIKI.write_text(gerar_wiki(), encoding="utf-8", newline="\n")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"gerado: {DESTINO.relative_to(RAIZ)}, {DESTINO_WIKI.relative_to(RAIZ)}")

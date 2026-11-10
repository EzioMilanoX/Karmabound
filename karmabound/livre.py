"""O Laboratório: o modo livre de dev, aberto pela sequência secreta do título.

Escolha a Linhagem, o Destino, as técnicas, as Relíquias, o Arco, o rival e o capítulo,
e lute direto. Nada disso salva nem conta para o Legado; ao fim da luta, volta à
montagem. Tudo vem aberto, até os itens de recompensa dos votos.
"""

from __future__ import annotations

from karmabound.jornada import Jornada
from karmabound.run import (
    aplicar_arco,
    aplicar_dom,
    aplicar_linhagem,
    atualizar_efeitos,
    criar_tecnica,
    receber_reliquia,
)
from karmabound.viloes import PAPEIS
from karmabound.votos import carregar_catalogo

TECNICAS = 4
RELIQUIAS = 3
CAPITULOS = 3

# (chave, rótulo, roda); a roda None é o rival ou o capítulo
LINHAS = (
    [("linhagem", "Linhagem", "linhagem"), ("destino", "Destino", "destino")]
    + [(f"tecnica{i}", f"Técnica {i + 1}", "tecnicas") for i in range(TECNICAS)]
    + [(f"reliquia{i}", f"Relíquia {i + 1}", "reliquias") for i in range(RELIQUIAS)]
    + [("arco", "Arco", "arco"), ("rival", "Rival", None), ("capitulo", "Capítulo", None)]
)


def _tudo_aberto() -> frozenset[str]:
    return frozenset(carregar_catalogo().recompensas.values())


def jornada_base(modo: str | None, seed: int | None = None) -> Jornada:
    """Uma run nova com tudo aberto (as rodas e os vilões de todas as obras)."""
    return Jornada.nova(modo, seed, alem=True, desbloqueios=_tudo_aberto())


def opcoes(j: Jornada, chave: str, roda: str | None) -> list:
    """O que cabe na linha: fatias da roda, vilões ou capítulos (o primeiro é 'nenhum')."""
    if chave == "capitulo":
        return list(range(1, CAPITULOS + 1))
    if chave == "rival":
        ordem = {p: i for i, p in enumerate(PAPEIS)}
        viloes = sorted(j.ctx.elenco.viloes, key=lambda v: (ordem[v.papel], v.nome))
        return [None, *viloes]
    fatias = j.ctx.rodas[roda].fatias
    if roda == "tecnicas":
        fatias = [f for f in fatias if f.combate]
    return [None, *fatias]


def montar(escolha: dict, modo: str | None, seed: int | None = None) -> Jornada:
    """A Jornada pronta para a luta: a build da `escolha` (chave -> id) contra o rival."""
    j = jornada_base(modo, seed)
    ctx, e = j.ctx, j.estado
    fatias = {f.id: f for roda in ctx.rodas.values() for f in roda.fatias}

    def pega(chave):
        return fatias.get(escolha.get(chave) or "")

    if pega("linhagem"):
        aplicar_linhagem(e, ctx, pega("linhagem"))
    if pega("destino"):
        aplicar_dom(e, ctx, pega("destino"))
    tem = {t.id for t in e.jogador.tecnicas}
    for i in range(TECNICAS):
        f = pega(f"tecnica{i}")
        if f is not None and f.id not in tem:  # sem limite de espaços no Laboratório
            e.jogador.tecnicas.append(criar_tecnica(ctx, f))
            tem.add(f.id)
    atualizar_efeitos(e)
    for i in range(RELIQUIAS):
        if pega(f"reliquia{i}"):
            receber_reliquia(e, pega(f"reliquia{i}"))
    if pega("arco"):
        aplicar_arco(e, ctx, pega("arco"))
    cap = int(escolha.get("capitulo") or 1)
    e.capitulo = cap
    e.luta_no_capitulo = e.tamanho_capitulo  # a luta do chefe do capítulo
    e.proxima_luta = cap * ctx.lutas_por_capitulo
    e.porta = None
    e.vilao_forcado = escolha.get("rival") or ""
    e.jogador.vida = e.jogador.vida_max
    j._comecar_luta()
    return j

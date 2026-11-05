import importlib.util
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _gerador():
    spec = importlib.util.spec_from_file_location(
        "gerar_catalogo", RAIZ / "tools" / "gerar_catalogo.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo  # o @dataclass do gerador procura o módulo aqui
    spec.loader.exec_module(modulo)
    return modulo


# seções de regras do jogo, sem homenagem a um anime
SEM_ANIME = (
    "restricoes",
    "ganhos",
    "portas",
    "papeis",
    "encruzilhadas",
    "legado",
    "ressonancias",
    "mecanicas",
    "afixos",
    "ascensao",
)


def test_toda_origem_diz_o_anime():
    """A wiki agrupa por anime: toda origem termina em ' · <anime>'."""
    gerador = _gerador()
    secoes, *_ = gerador._itens_da_wiki()
    sem = [
        x.item["id"]
        for sid, *_, itens in secoes
        if sid not in SEM_ANIME
        for x in itens
        if not x.anime
    ]
    assert sem == []


def test_catalogo_em_dia():
    """docs/CATALOGO.md é gerado dos JSON: mudou dado, rode `python tools/gerar_catalogo.py`."""
    gerador = _gerador()
    atual = gerador.DESTINO.read_text(encoding="utf-8")
    assert atual == gerador.gerar(), "catálogo desatualizado: rode python tools/gerar_catalogo.py"


def test_wiki_em_dia():
    """docs/wiki.html é gerada dos JSON pelo mesmo script do catálogo."""
    gerador = _gerador()
    atual = gerador.DESTINO_WIKI.read_text(encoding="utf-8")
    assert atual == gerador.gerar_wiki(), "wiki desatualizada: rode python tools/gerar_catalogo.py"

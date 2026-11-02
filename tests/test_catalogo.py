import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _gerador():
    spec = importlib.util.spec_from_file_location(
        "gerar_catalogo", RAIZ / "tools" / "gerar_catalogo.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_catalogo_em_dia():
    """docs/CATALOGO.md é gerado dos JSON: mudou dado, rode `python tools/gerar_catalogo.py`."""
    gerador = _gerador()
    atual = gerador.DESTINO.read_text(encoding="utf-8")
    assert atual == gerador.gerar(), "catálogo desatualizado: rode python tools/gerar_catalogo.py"

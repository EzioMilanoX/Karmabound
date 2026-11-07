"""O que o release automático precisa (tools/release.ps1 e .github/workflows/release.yml)."""

import re
import sys
from pathlib import Path

import karmabound

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))

from notas_da_versao import COMO_JOGAR, notas, secoes  # noqa: E402

EXEMPLO = """# Changelog

## Ainda sem versão

## v0.4.0 — Vilões e o Dono (2026-11-07)

Os chefes têm nome.

### Novidades

- O Dono da Roda.

## Até a v0.3.0

Nos Releases.
"""


def test_a_versao_e_a_mesma_no_pyproject_e_no_pacote():
    pyproject = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    versao = re.search(r'(?m)^version = "([^"]+)"', pyproject).group(1)
    assert versao == karmabound.__version__


def test_as_notas_de_uma_versao_saem_do_changelog():
    titulo, corpo = notas("v0.4.0", EXEMPLO)
    assert titulo == "v0.4.0 — Vilões e o Dono"
    assert corpo.startswith("Os chefes têm nome.") and "### Novidades" in corpo
    assert "Nos Releases" not in corpo  # só a seção dela
    assert corpo.endswith(COMO_JOGAR)


def test_o_changelog_tem_a_secao_das_proximas_notas():
    assert "Ainda sem versão" in secoes((RAIZ / "CHANGELOG.md").read_text(encoding="utf-8"))


def test_o_commit_da_engine_esta_gravado():
    assert re.fullmatch(r"[0-9a-f]{40}", (RAIZ / "engine.ref").read_text().strip())


def test_o_script_tem_bom_para_o_powershell_5():
    """Sem BOM, o PowerShell 5.1 lê o script como ANSI e "versão" vira "versÃ£o"."""
    assert (RAIZ / "tools" / "release.ps1").read_bytes()[:3] == b"\xef\xbb\xbf"

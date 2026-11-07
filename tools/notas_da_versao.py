"""As notas de uma versão, tiradas do CHANGELOG.md, para o Release do GitHub.

    python tools/notas_da_versao.py v0.4.0            # o corpo (com o "Como jogar")
    python tools/notas_da_versao.py v0.4.0 --titulo   # "v0.4.0 — Vilões com nome..."
    python tools/notas_da_versao.py v0.4.0 --arquivos  # grava notas.md e titulo.txt (UTF-8)

Cada versão é uma seção `## v0.4.0 — Título (AAAA-MM-DD)` do CHANGELOG.md, que o
tools/release.ps1 cria a partir da seção "Ainda sem versão".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CHANGELOG = RAIZ / "CHANGELOG.md"
SEM_VERSAO = "Ainda sem versão"

COMO_JOGAR = """
## Como jogar (Windows)

1. Baixe o **Karmabound-windows.zip** abaixo, em *Assets*.
2. Extraia a pasta inteira (o jogo precisa dos arquivos ao lado do .exe).
3. Abra **Karmabound.exe**. O Windows pode avisar que o programa não é assinado: \
*Mais informações → Executar assim mesmo*.

O progresso fica em `%USERPROFILE%\\.karmabound` e passa de uma versão para a outra.
"""


def secoes(texto: str) -> dict[str, tuple[str, str]]:
    """Cabeçalho `## ...` -> (a linha inteira sem os ##, o corpo)."""
    partes = re.split(r"^## (.+)$", texto, flags=re.M)
    achadas = {}
    for i in range(1, len(partes), 2):
        cabeca, corpo = partes[i].strip(), partes[i + 1].strip()
        chave = cabeca.split(" ", 1)[0] if cabeca.startswith("v") else cabeca
        achadas[chave] = (cabeca, corpo)
    return achadas


def notas(versao: str, texto: str | None = None) -> tuple[str, str]:
    """(título, corpo) da versão `versao` ("v0.4.0")."""
    texto = texto if texto is not None else CHANGELOG.read_text(encoding="utf-8")
    achadas = secoes(texto)
    if versao not in achadas:
        raise SystemExit(f"o CHANGELOG não tem a seção {versao} (rode tools/release.ps1)")
    cabeca, corpo = achadas[versao]
    titulo = re.sub(r"\s*\(\d{4}-\d{2}-\d{2}\)$", "", cabeca)
    return titulo, f"{corpo}\n{COMO_JOGAR}"


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    titulo, corpo = notas(argv[0])
    if "--arquivos" in argv:  # o Actions lê daqui: o console do Windows estraga acento
        Path("notas.md").write_text(corpo, encoding="utf-8")
        Path("titulo.txt").write_text(titulo, encoding="utf-8")
        return
    sys.stdout.reconfigure(encoding="utf-8")
    print(titulo if "--titulo" in argv else corpo)


if __name__ == "__main__":
    main(sys.argv[1:])

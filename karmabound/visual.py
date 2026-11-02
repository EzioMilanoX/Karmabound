"""Paleta, fonte e utilitários de desenho compartilhados pelas telas.

Tinta clara sobre laca escura, a mesma do manual. As cores de raridade vêm do
balanceamento.json; aqui ficam só as do próprio jogo.
"""

from __future__ import annotations

FONTE_PINCEL = 1  # id da Yuji Syuku no renderer (game.py a carrega)

LARGURA, ALTURA = 960, 640

FUNDO = (20, 18, 16, 255)
LACA = (31, 28, 25, 255)
TINTA = (216, 207, 192, 255)
FERRO = (92, 86, 80, 255)
SANGUE_VIVO = (196, 30, 36, 255)
OURO = (233, 196, 106, 255)
VERDE_JADE = (110, 168, 130, 255)  # cura e reação: o único verde do jogo

Cor = tuple[int, int, int, int]


def hex_cor(cor: str) -> Cor:
    cor = cor.lstrip("#")
    return (int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16), 255)


def mistura(a: Cor, b: Cor, t: float) -> Cor:
    t = max(0.0, min(1.0, t))
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def alpha(cor: Cor, a: float) -> Cor:
    return (cor[0], cor[1], cor[2], max(0, min(255, round(a))))


def ease_out(x: float) -> float:
    return 1 - (1 - x) ** 3


def pct(v: float) -> str:
    return f"{v:.1f}%".replace(".", ",")


def quebrar(texto: str, largura: int) -> list[str]:
    """Quebra `texto` em linhas de até `largura` caracteres (o renderer não mede texto)."""
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split():
        if atual and len(atual) + 1 + len(palavra) > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = f"{atual} {palavra}".strip()
    return linhas + ([atual] if atual else [])

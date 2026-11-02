"""Ponto de entrada: python -m karmabound [--roleta] [--headless]

`--headless` desenha um quadro e sai (para testar um build sem abrir janela)."""

import sys

from karmabound.game import run


def main() -> None:
    args = sys.argv[1:]
    run(headless="--headless" in args, roleta="--roleta" in args)


if __name__ == "__main__":
    main()

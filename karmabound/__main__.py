"""Ponto de entrada: python -m karmabound [--roleta]"""

import sys

from karmabound.game import run


def main() -> None:
    run(roleta="--roleta" in sys.argv[1:])


if __name__ == "__main__":
    main()

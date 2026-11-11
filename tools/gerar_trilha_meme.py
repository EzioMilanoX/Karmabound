"""Gera a trilha dos chefes secretos: uma caixinha de música saltitante, boba de propósito.

Original (sem direito autoral de ninguém): melodia em Dó maior sobre um baixo que pula,
140 bpm, 8 compassos que fecham em loop. Grava em karmabound/data/memes/<pasta>/musica.wav
(a pasta é do .gitignore; se você puser outra `musica.*` lá, ela vale no lugar desta).

Uso: python tools/gerar_trilha_meme.py [pasta]   (padrão: speaki)
"""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

TAXA = 22_050
BPM = 140
COLCHEIA = 60 / BPM / 2
RAIZ = Path(__file__).resolve().parent.parent

# semitons a partir do Dó 5 (None = pausa), uma colcheia cada; 8 compassos de 8
MELODIA = [
    0,
    4,
    7,
    12,
    7,
    4,
    9,
    7,
    5,
    9,
    12,
    9,
    7,
    None,
    4,
    None,
    0,
    4,
    7,
    12,
    14,
    12,
    9,
    7,
    5,
    4,
    2,
    4,
    0,
    None,
    None,
    None,
    9,
    12,
    9,
    7,
    5,
    7,
    9,
    None,
    7,
    11,
    14,
    11,
    7,
    None,
    2,
    None,
    4,
    7,
    4,
    0,
    2,
    4,
    5,
    7,
    12,
    11,
    9,
    7,
    5,
    4,
    2,
    None,
]
BAIXO = [0, 5, 0, 7, 9, 5, 7, 0]  # um por compasso (Dó 3), saltitando em oitavas
TOMBA = {0: 1.0, 4: 0.7}  # o "tum" de brinquedo em cada tempo forte


def _hz(semi: float, base: float = 523.25) -> float:
    return base * 2 ** (semi / 12)


def _nota(freq: float, seg: float, timbre: str) -> np.ndarray:
    t = np.arange(int(seg * TAXA)) / TAXA
    if timbre == "caixinha":  # sino de caixinha de música: fundamental + 4ª harmônica
        som = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 4 * t)
        return som * np.exp(-t / 0.18)
    quadrada = np.sign(np.sin(2 * np.pi * freq * t)) * 0.5  # o baixo de videogame
    return quadrada * np.exp(-t / 0.09)


def gerar() -> np.ndarray:
    total = int(len(MELODIA) * COLCHEIA * TAXA)
    mix = np.zeros(total + TAXA)

    def por(i_colcheia: float, som: np.ndarray, vol: float) -> None:
        i = int(i_colcheia * COLCHEIA * TAXA)
        mix[i : i + len(som)] += som * vol

    for k, semi in enumerate(MELODIA):
        if semi is not None:
            por(k, _nota(_hz(semi), COLCHEIA * 3, "caixinha"), 0.5)
    for c, semi in enumerate(BAIXO):
        for k in range(8):
            oitava = 12 if k % 2 else 0
            por(c * 8 + k, _nota(_hz(semi + oitava, 130.81), COLCHEIA, "baixo"), 0.22)
        for k, vol in TOMBA.items():
            t = np.arange(int(0.12 * TAXA)) / TAXA
            tum = np.sin(2 * np.pi * (180 - 600 * t) * t) * np.exp(-t / 0.04)
            por(c * 8 + k, tum, 0.5 * vol)
    rabo = mix[total:]  # o que passou do fim volta no começo: o loop não estala
    mix = mix[:total]
    mix[: len(rabo)] += rabo
    return mix


def salvar(caminho: Path, som: np.ndarray) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    som = som / (np.max(np.abs(som)) or 1) * 0.7
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes((np.clip(som, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    pasta = sys.argv[1] if len(sys.argv) > 1 else "speaki"
    destino = RAIZ / "karmabound" / "data" / "memes" / pasta / "musica.wav"
    salvar(destino, gerar())
    print(destino)

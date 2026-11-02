"""Sintetiza os sons e as músicas do jogo em WAV: python tools/gerar_sons.py

Tudo nasce aqui, de senos, ruído e cordas dedilhadas (Karplus-Strong), sem
nenhum arquivo de terceiros: taiko, gongo, sinos, shamisen, koto, correntes,
vento e cortes. As músicas usam escalas japonesas (hirajoshi e in) e fecham o
loop sem emenda: as caudas que passam do fim voltam para o começo.

Saída: assets/sons/*.wav (efeitos) e assets/musica/*.wav (faixas em loop),
22.050 Hz, mono, 16 bits. Seed fixa: os arquivos saem iguais a cada execução.
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

TAXA = 22_050
RAIZ = Path(__file__).resolve().parent.parent / "assets"
RNG = np.random.default_rng(7)

# A hirajoshi em Lá: A B C E F (e oitavas)
HIRAJOSHI = [220.0, 246.94, 261.63, 329.63, 349.23]
IN = [220.0, 233.08, 293.66, 329.63, 349.23]  # a escala in (miyako-bushi), mais sombria


def _t(seg: float) -> np.ndarray:
    return np.arange(int(seg * TAXA)) / TAXA


def _decai(seg: float, tau: float) -> np.ndarray:
    return np.exp(-_t(seg) / tau)


def _ataque(sinal: np.ndarray, seg: float = 0.004) -> np.ndarray:
    n = min(len(sinal), int(seg * TAXA))
    sinal = sinal.copy()
    sinal[:n] *= np.linspace(0, 1, n)
    return sinal


def _passa_baixa(x: np.ndarray, corte: float) -> np.ndarray:
    """Filtro de um polo, o bastante para escurecer ruído."""
    a = np.exp(-2 * np.pi * corte / TAXA)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def _ruido(seg: float) -> np.ndarray:
    return RNG.uniform(-1, 1, int(seg * TAXA))


# ----------------------------------------------------------------------- instrumentos


def taiko(freq: float = 70, seg: float = 0.9, forca: float = 1.0) -> np.ndarray:
    t = _t(seg)
    queda = freq * (1 + 0.6 * np.exp(-t / 0.03))  # a pele afina logo depois da batida
    corpo = np.sin(2 * np.pi * np.cumsum(queda) / TAXA) * np.exp(-t / (0.25 * forca))
    estalo = _passa_baixa(_ruido(seg), 1800) * np.exp(-t / 0.012) * 1.6
    return _ataque((corpo + estalo) * forca)


def kane(seg: float = 0.25) -> np.ndarray:
    """O 'ka' da borda do taiko: madeira seca."""
    t = _t(seg)
    return _ataque(
        np.sin(2 * np.pi * 1400 * t) * np.exp(-t / 0.02) + _ruido(seg) * np.exp(-t / 0.006) * 0.4
    )


def gongo(freq: float = 98, seg: float = 4.0) -> np.ndarray:
    t = _t(seg)
    som = np.zeros_like(t)
    for mult, amp, tau in (
        (1.0, 1.0, 1.8),
        (1.483, 0.6, 1.3),
        (1.932, 0.5, 1.0),
        (2.546, 0.35, 0.8),
        (3.31, 0.2, 0.5),
    ):
        batimento = 1 + 0.004 * np.sin(2 * np.pi * 0.7 * t)
        som += amp * np.sin(2 * np.pi * freq * mult * batimento * t) * np.exp(-t / tau)
    inchar = 1 - np.exp(-t / 0.05)  # o gongo cresce um instante antes de cantar
    return som * inchar / 2.2


def sino(freq: float = 880, seg: float = 1.6) -> np.ndarray:
    t = _t(seg)
    som = sum(
        a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t / tau)
        for m, a, tau in ((1, 1, 0.9), (2.76, 0.4, 0.4), (5.4, 0.2, 0.15))
    )
    return _ataque(som / 1.6, 0.002)


def corda(freq: float, seg: float = 1.2, brilho: float = 0.5, zumbido: float = 0.0) -> np.ndarray:
    """Karplus-Strong: shamisen (brilho alto, zumbido de sawari) ou koto (macio)."""
    n = int(seg * TAXA)
    periodo = max(2, int(TAXA / freq))
    buf = RNG.uniform(-1, 1, periodo)
    saida = np.empty(n)
    mistura = 0.5 + 0.49 * brilho
    for i in range(n):
        j = i % periodo
        v = buf[j]
        saida[i] = v
        buf[j] = mistura * v + (1 - mistura) * buf[(j + 1) % periodo]
        buf[j] *= 0.996
    if zumbido:
        saida = np.tanh(saida * (1 + 4 * zumbido)) / np.tanh(1 + 4 * zumbido)
    return saida


def shamisen(freq: float, seg: float = 0.7) -> np.ndarray:
    return corda(freq, seg, brilho=0.95, zumbido=0.6) * 0.8


def koto(freq: float, seg: float = 1.8) -> np.ndarray:
    return corda(freq, seg, brilho=0.35) * 0.9


def corte(seg: float = 0.32, agudo: bool = False) -> np.ndarray:
    t = _t(seg)
    r = _ruido(seg)
    varredura = _passa_baixa(r, 5000 if agudo else 2600) - _passa_baixa(r, 700)
    env = np.minimum(t / 0.03, 1) * np.exp(-t / 0.08)
    return varredura * env * 2.2


def corrente(seg: float = 0.6) -> np.ndarray:
    som = np.zeros(int(seg * TAXA))
    for k, inicio in enumerate((0.0, 0.07, 0.16, 0.22, 0.34)):
        elo = sino(2200 + 340 * k, 0.25) * 0.5 + _ruido(0.25) * np.exp(-_t(0.25) / 0.01) * 0.3
        i = int(inicio * TAXA)
        som[i : i + len(elo)] += elo[: len(som) - i]
    return som


def vento(seg: float = 4.0) -> np.ndarray:
    t = _t(seg)
    base = _passa_baixa(_ruido(seg), 500)
    return base * (0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * t)) * 3


def drone(freq: float, seg: float, sombrio: bool = False) -> np.ndarray:
    t = _t(seg)
    quinta = 1.5 if not sombrio else 1.414  # o trítono deixa o chefe mais pesado
    som = (
        np.sin(2 * np.pi * freq * t)
        + 0.5 * np.sin(2 * np.pi * freq * quinta * t)
        + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    )
    return som * (0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * t)) / 1.8


def _soma(*partes: tuple[float, np.ndarray]) -> np.ndarray:
    fim = max(int(t * TAXA) + len(s) for t, s in partes)
    total = np.zeros(fim)
    for t, s in partes:
        i = int(t * TAXA)
        total[i : i + len(s)] += s
    return total


# ----------------------------------------------------------------------- efeitos

EFEITOS = {
    "tique": lambda: kane(0.08) * 0.35,
    "parar": lambda: taiko(80, 0.8),
    "revela_cinza": lambda: koto(220, 1.2),
    "revela_sangue": lambda: _soma((0, koto(220)), (0.06, koto(329.63)), (0.12, koto(440))),
    "revela_maldito": lambda: _soma(
        (0, shamisen(233.08, 1.0)), (0, gongo(73, 2.0) * 0.7), (0.1, shamisen(220, 1.0))
    ),
    "revela_divino": lambda: _soma(
        (0, gongo(98, 3.0)), (0.05, sino(880)), (0.15, sino(1318.5)), (0.25, sino(1760))
    ),
    "despertar": lambda: _soma(
        (0, gongo(65, 4.0) * 1.3),
        *((0.2 + 0.09 * k, sino(440 * 2 ** (k / 5), 1.4) * 0.5) for k in range(10)),
    ),
    "corrente": lambda: corrente(),
    "golpe": lambda: _soma((0, taiko(90, 0.5, 0.8)), (0, kane(0.1) * 0.5)),
    "corte": lambda: corte(),
    "corte_agudo": lambda: corte(0.25, agudo=True),
    "defesa": lambda: _soma((0, kane(0.12)), (0.08, kane(0.12) * 0.7)),
    "cura": lambda: _soma(*((0.07 * k, sino(f * 2, 1.0) * 0.45) for k, f in enumerate(HIRAJOSHI))),
    "dano": lambda: taiko(52, 0.6, 0.9),
    "percebeu": lambda: sino(1975, 0.8) * 0.7,
    "maldita": lambda: _soma(
        (0, gongo(55, 2.2) * 0.8), (0, shamisen(116.5, 1.2)), (0.12, shamisen(110, 1.2))
    ),
    "raio": lambda: _soma(
        *((0.03 * k, corte(0.08, agudo=True) * (1 - k * 0.12)) for k in range(6)),
        (0, taiko(120, 0.4, 0.6)),
    ),
    "critico": lambda: _soma(
        (0, taiko(60, 1.0, 1.3)), (0.02, gongo(130, 1.6) * 0.8), (0.05, sino(1760, 1.0) * 0.6)
    ),
    "dominio": lambda: _soma(
        (0, gongo(49, 4.0) * 1.2), (0, drone(55, 2.5) * np.linspace(0, 1, int(2.5 * TAXA)))
    ),
    "tempo": lambda: sino(660, 1.8)[::-1] * 0.9,  # o tempo andando para trás
    "mover": lambda: kane(0.06) * 0.25,
    "confirmar": lambda: koto(440, 0.8) * 0.8,
    "vitoria": lambda: _soma(
        *((0.11 * k, koto(f * 2, 1.6)) for k, f in enumerate(HIRAJOSHI)), (0.6, gongo(110, 3.0))
    ),
    "derrota": lambda: _soma(
        (0, gongo(49, 4.0) * 1.2),
        (0.2, shamisen(220, 1.4)),
        (0.55, shamisen(196, 1.4)),
        (0.9, shamisen(164.8, 2.0)),
    ),
    "rival_entra": lambda: _soma(
        (0, taiko(70, 0.6, 0.7)),
        (0.32, taiko(70, 0.6, 0.8)),
        (0.52, taiko(75, 0.6, 0.9)),
        (0.62, corte(0.35)),
    ),
    "chefe_entra": lambda: _soma(
        (0, taiko(45, 1.4, 1.6)), (0.6, taiko(45, 1.4, 1.6)), (0.9, gongo(49, 4.0) * 1.3)
    ),
}


# ----------------------------------------------------------------------- músicas


def _loop(seg: float, eventos: list[tuple[float, np.ndarray]]) -> np.ndarray:
    """Mistura num buffer circular: o que passa do fim volta para o começo."""
    n = int(seg * TAXA)
    buf = np.zeros(n)
    for inicio, som in eventos:
        i = int(inicio * TAXA) % n
        idx = (np.arange(len(som)) + i) % n
        np.add.at(buf, idx, som)
    return buf


CRUZA = 1.0  # segundos de transição sobre a emenda do loop


def _continuo(som: np.ndarray) -> np.ndarray:
    """Uma camada contínua (drone, vento) gerada CRUZA segundos mais longa: entra e sai
    em rampa, e no buffer circular a saída se sobrepõe à entrada — a emenda some."""
    n = int(CRUZA * TAXA)
    som = som.copy()
    som[:n] *= np.sqrt(np.linspace(0, 1, n))
    som[-n:] *= np.sqrt(np.linspace(1, 0, n))
    return som


def _tambores(seg: float, bpm: float, padrao: str, freq: float = 70, forca: float = 1.0) -> list:
    """`padrao` por semicolcheia: D = don (centro), K = ka (borda), . = pausa."""
    passo = 60 / bpm / 4
    eventos = []
    n = int(seg / passo)
    for i in range(n):
        c = padrao[i % len(padrao)]
        if c == "D":
            eventos.append((i * passo, taiko(freq, 0.8, forca) * 0.8))
        elif c == "O":  # odaiko: o tambor grande
            eventos.append((i * passo, taiko(freq * 0.6, 1.4, forca * 1.4)))
        elif c == "K":
            eventos.append((i * passo, kane(0.12) * 0.35))
    return eventos


def _melodia(
    seg: float, bpm: float, notas: list[int], escala: list[float], instrumento, oitava: float = 1.0
) -> list:
    """`notas`: graus da escala por colcheia (-1 = pausa)."""
    passo = 60 / bpm / 2
    eventos = []
    for i in range(int(seg / passo)):
        g = notas[i % len(notas)]
        if g < 0:
            continue
        f = escala[g % len(escala)] * oitava * (2 ** (g // len(escala)))
        eventos.append((i * passo, instrumento(f) * 0.5))
    return eventos


def musica_titulo() -> np.ndarray:
    seg = 24.0
    ev = [(0, _continuo(drone(55, seg + CRUZA)) * 0.5), (0, _continuo(vento(seg + CRUZA)) * 0.25)]
    frase = [
        4,
        -1,
        3,
        -1,
        2,
        -1,
        -1,
        -1,
        0,
        -1,
        1,
        -1,
        2,
        -1,
        -1,
        -1,
        7,
        -1,
        5,
        -1,
        4,
        -1,
        3,
        -1,
        2,
        -1,
        -1,
        -1,
        -1,
        -1,
        -1,
        -1,
    ]
    ev += _melodia(seg, 80, frase, HIRAJOSHI, koto)
    ev += [(k * 8.0, gongo(73, 4.0) * 0.4) for k in range(3)]
    return _loop(seg, ev)


def musica_roleta() -> np.ndarray:
    seg = 16.0
    ev = [(0, _continuo(drone(55, seg + CRUZA, sombrio=True)) * 0.45)]
    ev += _tambores(seg, 60, "D...D...........", 55, 0.7)  # batida de coração
    ev += [(k * 2.0 + 1.0, sino(1760 * (1.0 if k % 2 else 1.189), 1.4) * 0.18) for k in range(8)]
    return _loop(seg, ev)


def _luta(seg: float, bpm: float, intensa: bool) -> np.ndarray:
    ev = [(0, _continuo(drone(55, seg + CRUZA)) * 0.35)]
    ev += _tambores(seg, bpm, "D..KD.K.D.KKD.K." if not intensa else "D.KKD.KKD.KDDKKD", 72, 0.9)
    ev += _tambores(seg, bpm, "O...............O.......O.......", 72, 1.0)
    riff = [0, 0, 3, 2, 0, -1, 4, 3, 2, 2, 0, 1, 2, -1, -1, -1]
    ev += _melodia(seg, bpm, riff, HIRAJOSHI, shamisen, oitava=0.5)
    if intensa:
        ev += _melodia(seg, bpm, [7, -1, 5, -1, 4, -1, 2, -1], HIRAJOSHI, shamisen, oitava=1.0)
    return _loop(seg, ev)


def musica_chefe() -> np.ndarray:
    seg = 19.2
    bpm = 100
    ev = [(0, _continuo(drone(41.2, seg + CRUZA, sombrio=True)) * 0.55)]
    ev += _tambores(seg, bpm, "O..DO.D.O..DOKDK", 60, 1.1)
    ev += [(k * 4.8, gongo(55, 4.0) * 0.6) for k in range(4)]
    ev += _melodia(
        seg,
        bpm,
        [0, -1, 1, -1, 0, -1, -1, -1, 4, -1, 3, -1, 1, -1, 0, -1],
        IN,
        shamisen,
        oitava=0.5,
    )
    return _loop(seg, ev)


MUSICAS = {
    "titulo": musica_titulo,
    "roleta": musica_roleta,
    "luta": lambda: _luta(16.0, 120, intensa=False),
    "luta_carma": lambda: _luta(16.0, 120, intensa=True),
    "chefe": musica_chefe,
}


def _salvar(caminho: Path, som: np.ndarray, pico: float) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    som = som / (np.max(np.abs(som)) or 1) * pico
    dados = (np.clip(som, -1, 1) * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAXA)
        w.writeframes(dados.tobytes())


def gerar() -> list[Path]:
    feitos = []
    for nome, fazer in EFEITOS.items():
        caminho = RAIZ / "sons" / f"{nome}.wav"
        _salvar(caminho, fazer(), 0.85)
        feitos.append(caminho)
    for nome, fazer in MUSICAS.items():
        caminho = RAIZ / "musica" / f"{nome}.wav"
        _salvar(caminho, fazer(), 0.6)
        feitos.append(caminho)
    return feitos


if __name__ == "__main__":
    for p in gerar():
        print(p.relative_to(RAIZ.parent), f"{p.stat().st_size // 1024} KB")

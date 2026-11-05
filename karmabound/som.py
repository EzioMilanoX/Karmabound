"""Som: efeitos e música por nome, sobre o `IAudioEngine` da engine.

Mudo até `configurar` (o jogo chama ao montar o loop): testes, simulador e
ferramentas nunca tocam nada. `musica(nome, cruzar=s)` troca de faixa com uma
passagem (a faixa velha baixa, a nova entra no mesmo ponto do compasso e sobe); quem
pede a passagem chama `atualizar(dt)` a cada quadro. Os arquivos são gerados por
`python tools/gerar_sons.py` (síntese em código, sem assets de terceiros); um
arquivo que falta é só silêncio, nunca erro.
"""

from __future__ import annotations

import wave
from pathlib import Path

from karmabound.opcoes import OPCOES

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# volume de cada efeito (o que não está aqui toca em 1,0)
VOLUMES = {
    "tique": 0.35,
    "mover": 0.4,
    "corrente": 0.6,
    "golpe": 0.8,
    "dano": 0.8,
    "percebeu": 0.7,
}

# o som de cada efeito visual da luta (vfx.py)
SOM_DO_EFEITO = {
    "impacto": "golpe",
    "punho": "golpe",
    "investida": "golpe",
    "clones": "golpe",
    "espiral": "golpe",
    "esfera": "golpe",
    "guarda": "defesa",
    "rotacao": "defesa",
    "corte_x": "corte",
    "presa": "corte",
    "sangue": "corte",
    "trovao": "raio",
    "clarao_negro": "raio",
    "selo": "maldita",
    "ilusao": "maldita",
    "demonio": "maldita",
    "olho": "maldita",
    "repulsao": "critico",
    "corte_mundo": "critico",
    "dominio": "dominio",
    "tempo": "tempo",
    "correntes": "corrente",
    "cura": "cura",
    "fogo": "critico",
    "gelo": "corte_agudo",
    "veneno": "maldita",
    "vento": "corte",
    "explosao": "critico",
    "feixe": "critico",
    "raio_na_mao": "raio",
    "punho_gigante": "critico",
    "trovao_flamejante": "raio",
    "vermelho": "critico",
    "espirais": "golpe",
    "transmutacao": "corte_agudo",
    "roda_dharma": "roda",
    "espelho": "vidro",
}


class _Som:
    def __init__(self) -> None:
        self.audio = None
        self.sons: set[str] = set()
        self.musicas: set[str] = set()
        self.musica_atual: str | None = None  # a faixa pedida
        self.tocando: str | None = None  # a que a engine toca agora (na passagem, a velha)
        self.duracoes: dict[str, float] = {}  # segundos de cada faixa (para casar o compasso)
        self.passagem: tuple[str, float, float, bool] | None = None  # (nova, passou, total, trocou)

    def configurar(self, audio, pasta: Path = ASSETS) -> None:
        self.audio = audio
        for arquivo in sorted((pasta / "sons").glob("*.wav")):
            try:
                audio.load_sound(arquivo.stem, str(arquivo))
                self.sons.add(arquivo.stem)
            except Exception:  # sem placa de som ou arquivo ruim: segue mudo
                pass
        for arquivo in sorted((pasta / "musica").glob("*.wav")):
            try:
                audio.load_track(arquivo.stem, str(arquivo))
                self.musicas.add(arquivo.stem)
                with wave.open(str(arquivo), "rb") as w:
                    self.duracoes[arquivo.stem] = w.getnframes() / w.getframerate()
            except Exception:
                pass
        self.aplicar_volume()

    def _efeitos(self) -> float:
        return 0.0 if OPCOES.mudo else OPCOES.volume_efeitos / 10

    def _volume_musica(self) -> float:
        return 0.0 if OPCOES.mudo else OPCOES.volume_musica / 10

    def aplicar_volume(self, fracao: float = 1.0) -> None:
        """Leva o volume da música das opções para a engine (M17: `set_track_volume`);
        `fracao` é o quanto dele vale agora (a passagem entre faixas)."""
        if self.audio is None or not hasattr(self.audio, "set_track_volume"):
            return
        try:
            self.audio.set_track_volume(self._volume_musica() * max(0.0, min(1.0, fracao)))
        except Exception:
            pass

    def tocar(self, nome: str, volume: float = 1.0) -> None:
        if self.audio is None or nome not in self.sons:
            return
        alto = volume * VOLUMES.get(nome, 1.0) * self._efeitos()
        if alto <= 0:
            return
        try:
            self.audio.play_one_shot(nome, alto)
        except Exception:
            pass

    def musica(self, nome: str | None, cruzar: float = 0.0) -> None:
        """Troca a faixa em loop (a mesma faixa não recomeça). `None` para a música.

        `cruzar` (segundos): em vez de cortar, a faixa velha baixa até o silêncio, a
        nova entra no mesmo ponto do compasso (quando as duas têm a mesma duração) e
        sobe; `atualizar(dt)` conduz a passagem."""
        if self.audio is None or nome == self.musica_atual:
            return
        if cruzar > 0 and self.tocando is not None and nome in self.musicas:
            self.musica_atual = nome
            self.passagem = (nome, 0.0, cruzar, False)
            return
        self.passagem = None
        try:
            if self.tocando is not None:
                self.audio.stop_track(self.tocando)
            self.tocando = None
            if nome is not None and nome in self.musicas:
                self.audio.play_track(nome, loop=True)
                self.tocando = nome
        except Exception:
            pass
        self.musica_atual = nome
        self.aplicar_volume()

    def _onde(self, velha: str, nova: str) -> float:
        """Onde a faixa nova entra: o mesmo ponto do loop da velha, se casam."""
        dv, dn = self.duracoes.get(velha, 0.0), self.duracoes.get(nova, 0.0)
        if not dv or abs(dv - dn) > 0.05:
            return 0.0
        try:
            return self.audio.get_clock().now_seconds() % dv
        except Exception:
            return 0.0

    def atualizar(self, dt: float) -> None:
        """Conduz a passagem entre faixas (sem passagem, não faz nada)."""
        if self.passagem is None or self.audio is None:
            return
        nova, passou, total, trocou = self.passagem
        passou += max(0.0, dt)
        meio = total / 2
        if not trocou and passou >= meio:
            velha, onde = self.tocando, self._onde(self.tocando or "", nova)
            try:
                if velha is not None:
                    self.audio.stop_track(velha)
                try:
                    self.audio.play_track(nova, start_offset_seconds=onde, loop=True)
                except Exception:  # o formato não deixa começar no meio: do começo
                    self.audio.play_track(nova, loop=True)
                self.tocando = nova
            except Exception:
                pass
            trocou = True
        if passou >= total:
            self.passagem = None
            self.aplicar_volume()
            return
        self.passagem = (nova, passou, total, trocou)
        self.aplicar_volume(abs(passou - meio) / meio)


SOM = _Som()
tocar = SOM.tocar
musica = SOM.musica

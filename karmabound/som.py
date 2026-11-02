"""Som: efeitos e música por nome, sobre o `IAudioEngine` da engine.

Mudo até `configurar` (o jogo chama ao montar o loop): testes, simulador e
ferramentas nunca tocam nada. Os arquivos são gerados por
`python tools/gerar_sons.py` (síntese em código, sem assets de terceiros); um
arquivo que falta é só silêncio, nunca erro.
"""

from __future__ import annotations

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
}


class _Som:
    def __init__(self) -> None:
        self.audio = None
        self.sons: set[str] = set()
        self.musicas: set[str] = set()
        self.musica_atual: str | None = None

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
            except Exception:
                pass
        self.aplicar_volume()

    def _efeitos(self) -> float:
        return 0.0 if OPCOES.mudo else OPCOES.volume_efeitos / 10

    def aplicar_volume(self) -> None:
        """Leva o volume da música das opções para a engine (M17: `set_track_volume`)."""
        if self.audio is None or not hasattr(self.audio, "set_track_volume"):
            return
        try:
            self.audio.set_track_volume(0.0 if OPCOES.mudo else OPCOES.volume_musica / 10)
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

    def musica(self, nome: str | None) -> None:
        """Troca a faixa em loop (a mesma faixa não recomeça). `None` para a música."""
        if self.audio is None or nome == self.musica_atual:
            return
        try:
            if self.musica_atual is not None:
                self.audio.stop_track(self.musica_atual)
            if nome is not None and nome in self.musicas:
                self.audio.play_track(nome, loop=True)
        except Exception:
            pass
        self.musica_atual = nome


SOM = _Som()
tocar = SOM.tocar
musica = SOM.musica

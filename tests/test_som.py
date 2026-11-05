"""Som: todo nome usado nas telas existe em assets/, e nada toca sem configurar."""

import re
from pathlib import Path

from karmabound import som
from karmabound.rodas import carregar_balanceamento, carregar_raridades

RAIZ = Path(__file__).resolve().parent.parent
TELAS = ("tela_luta", "tela_roleta", "tela_menus", "tela_grimorio")


def _usados(funcao: str) -> set[str]:
    """Os nomes entre aspas nas linhas que chamam som.<funcao>(...)."""
    nomes = set()
    for modulo in TELAS:
        texto = (RAIZ / "karmabound" / f"{modulo}.py").read_text(encoding="utf-8")
        for linha in texto.splitlines():
            if f"som.{funcao}(" in linha:
                nomes |= set(re.findall(r'"([a-z_]+)"', linha))
    return nomes


def test_todo_efeito_usado_existe():
    existentes = {p.stem for p in (RAIZ / "assets" / "sons").glob("*.wav")}
    raridades = [r.id for r in carregar_raridades(carregar_balanceamento())]
    usados = _usados("tocar") | set(som.SOM_DO_EFEITO.values()) | {f"revela_{r}" for r in raridades}
    usados |= {"cutin", "quebra", "vidro", "roda"}  # a luta agenda estes (_agendar_som)
    assert usados <= existentes, usados - existentes


def test_toda_musica_usada_existe():
    existentes = {p.stem for p in (RAIZ / "assets" / "musica").glob("*.wav")}
    usadas = _usados("musica") | {"luta", "luta_carma", "chefe", "chefe_furia"}
    assert usadas <= existentes, usadas - existentes


def test_todo_efeito_visual_tem_som():
    from karmabound import vfx

    sem = {n for n in vfx.EFEITOS if n not in som.SOM_DO_EFEITO and n != "nada"}
    assert not sem, sem


class AudioFalso:
    def __init__(self):
        self.tocados, self.faixas, self.carregados = [], [], []

    def load_sound(self, nome, caminho):
        self.carregados.append(nome)

    def load_track(self, nome, caminho):
        pass

    def play_one_shot(self, nome, volume=1.0):
        self.tocados.append((nome, volume))

    def play_track(self, nome, start_offset_seconds=0.0, loop=False):
        self.faixas.append(nome)

    def stop_track(self, nome):
        pass


def test_mudo_ate_configurar_e_depois_toca():
    s = som._Som()
    s.tocar("golpe")  # sem áudio: nada acontece, nada quebra
    s.musica("luta")
    audio = AudioFalso()
    s.configurar(audio)
    assert "golpe" in audio.carregados
    s.tocar("golpe")
    s.tocar("nao_existe")
    s.musica("luta")
    s.musica("luta")  # a mesma faixa não recomeça
    assert [n for n, _ in audio.tocados] == ["golpe"] and audio.faixas == ["luta"]


def test_audio_quebrado_nao_derruba_o_jogo():
    class Quebrado(AudioFalso):
        def play_one_shot(self, nome, volume=1.0):
            raise RuntimeError("sem placa de som")

    s = som._Som()
    s.configurar(Quebrado())
    s.tocar("golpe")

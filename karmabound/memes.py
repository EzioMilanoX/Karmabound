"""Os chefes secretos: memes, de propósito toscos.

Ficam escondidos até a sequência ↑ ↑ ↓ ↓ ← → ← → no título (a mesma que liga o modo
desenvolvedor do BulletHell; W W S S A D A D também vale). Ligados, cada chefe de
capítulo que não é fixo tem MEME_CHANCE de dar lugar a um deles.

Um chefe secreto é um vilão de papel "meme" em data/viloes.json com `imagens`: o nome
da pasta com os quadros dele (PNG), em `karmabound/data/memes/<imagens>/`. A pasta vai
no executável, mas fica no .gitignore: a arte não é nossa. Sem nenhum PNG na pasta, o chefe
não aparece. A animação é tosca de propósito: troca de quadro a cada `troca` segundos,
com um pulo e um tremor, sem transição nenhuma.

Os sons ficam em `<pasta>/sons/`, pelo momento no começo do nome: `entrada`, `golpe`
(quando ele ataca), `dor` (quando apanha), `derrota` e `vitoria` (`golpe_1.mp3`,
`golpe_2.mp3`... sorteia entre os do mesmo momento). Sem arquivo, fica mudo. A trilha
da luta é `<pasta>/musica.*` (tools/gerar_trilha_meme.py gera uma original).
"""

from __future__ import annotations

import os
import random
import struct
import zlib
from pathlib import Path

import numpy as np

from karmabound.viloes import Elenco, Vilao

SEQUENCIA = ("cima", "cima", "baixo", "baixo", "esquerda", "direita", "esquerda", "direita")
MEME_CHANCE = 0.2  # a chance de um chefe de capítulo (não fixo) ser um chefe secreto


def pasta_memes() -> Path:
    """Onde ficam as imagens dos chefes secretos (dentro do jogo; os testes trocam)."""
    outra = os.environ.get("KARMABOUND_MEMES")
    return Path(outra) if outra else Path(__file__).parent / "data" / "memes"


def quadros(vilao: Vilao, pasta: Path | None = None) -> list[Path]:
    """Os PNG do chefe secreto, em ordem de nome."""
    if not vilao.imagens:
        return []
    dele = (pasta or pasta_memes()) / vilao.imagens
    return sorted(dele.glob("*.png")) if dele.is_dir() else []


def memes_disponiveis(elenco: Elenco, pasta: Path | None = None) -> tuple[Vilao, ...]:
    """Os chefes secretos que têm imagem para aparecer."""
    return tuple(v for v in elenco.do_papel("meme") if quadros(v, pasta))


SONS = (".mp3", ".wav", ".ogg")


def sons(vilao: Vilao, momento: str, pasta: Path | None = None) -> list[Path]:
    """Os sons do chefe secreto para o momento (entrada, golpe, dor, derrota, vitoria)."""
    if not vilao.imagens:
        return []
    dele = (pasta or pasta_memes()) / vilao.imagens / "sons"
    if not dele.is_dir():
        return []
    return sorted(p for p in dele.glob(f"{momento}*") if p.suffix.lower() in SONS)


def tocar_meme(vilao: Vilao | None, momento: str, rng: random.Random | None = None) -> bool:
    """Toca um som do chefe secreto (False se ele não é meme ou não tem som)."""
    if vilao is None or vilao.papel != "meme":
        return False
    lista = sons(vilao, momento)
    if not lista:
        return False
    from karmabound.som import SOM

    SOM.tocar_arquivo((rng or random).choice(lista))
    return True


def trilha(vilao: Vilao | None, pasta: Path | None = None) -> Path | None:
    """A música da luta contra o chefe secreto (None: a de chefe de sempre)."""
    if vilao is None or vilao.papel != "meme" or not vilao.imagens:
        return None
    dele = (pasta or pasta_memes()) / vilao.imagens
    achadas = sorted(p for p in dele.glob("musica.*") if p.suffix.lower() in SONS)
    return achadas[0] if achadas else None


class Sequencia:
    """Lembra as últimas setas e avisa quando elas formam a SEQUENCIA."""

    def __init__(self) -> None:
        self.feitas: list[str] = []

    def apertou(self, entrada) -> bool:
        """Chame a cada quadro; True no quadro em que a sequência fecha."""
        for seta in ("cima", "baixo", "esquerda", "direita"):
            if entrada.is_action_pressed(seta):
                self.feitas = [*self.feitas, seta][-len(SEQUENCIA) :]
        if tuple(self.feitas) == SEQUENCIA:
            self.feitas = []
            return True
        return False


# ----------------------------------------------------------------------- o desenho


def tamanho_png(caminho: Path) -> tuple[int, int]:
    """(largura, altura) lidos do cabeçalho do PNG, sem abrir a imagem."""
    with caminho.open("rb") as f:
        cabeca = f.read(24)
    if cabeca[:8] != b"\x89PNG\r\n\x1a\n":
        return 256, 256
    return struct.unpack(">II", cabeca[16:24])


_carregadas: dict[int, set[int]] = {}  # renderer -> texturas já carregadas


def _textura(r, caminho: Path) -> int:
    tid = zlib.crc32(str(caminho).encode("utf-8")) & 0x7FFFFFFF
    feitas = _carregadas.setdefault(id(r), set())
    if tid not in feitas:
        r.load_texture(tid, str(caminho))
        feitas.add(tid)
    return tid


def desenhar_meme(
    r, vilao: Vilao, x: float, y: float, altura: float, relogio: float, visivel: float = 1.0
) -> bool:
    """O quadro da vez do chefe secreto, com os pés em (x, y). False se não há imagem."""
    lista = quadros(vilao)
    if not lista or visivel <= 0:
        return bool(lista)
    n = int(relogio / max(0.05, vilao.troca))
    caminho = lista[n % len(lista)]
    largura, alto = tamanho_png(caminho)
    escala = altura / max(1, alto) * (1.08 if n % 2 else 1.0)  # o pulo, sem suavizar nada
    tremor = 6 if n % 3 == 0 else -4
    w, h = largura * escala, alto * escala
    r.draw_batch(
        np.array([[x + tremor, y - h / 2]], dtype=np.float32),
        np.zeros(1, dtype=np.float32),
        np.array([[w / 8, h / 8]], dtype=np.float32),  # o backend mede o sprite em 8 px
        np.array([_textura(r, caminho)], dtype=np.int64),
        np.array([[255, 255, 255, round(255 * visivel)]], dtype=np.uint8),
        np.zeros(1, dtype=np.int32),
        1,
    )
    return True

"""Grimório: as habilidades que já saíram da roleta, guardadas entre runs.

Um arquivo JSON pequeno com os ids vistos. O caminho padrão é
`~/.karmabound/grimorio.json`; a variável `KARMABOUND_SAVE` troca a pasta (os
testes usam uma pasta temporária). Só a Jornada (uma pessoa jogando) registra:
o piloto automático e o simulador nunca tocam no arquivo.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from karmabound.rodas import Fatia


def caminho_padrao() -> Path:
    pasta = os.environ.get("KARMABOUND_SAVE") or Path.home() / ".karmabound"
    return Path(pasta) / "grimorio.json"


class Grimorio:
    def __init__(self, caminho: Path | None = None) -> None:
        """`caminho=None`: só em memória (nada é salvo)."""
        self.caminho = caminho
        self.vistos: set[str] = set()
        if caminho is not None and caminho.exists():
            try:
                self.vistos = set(json.loads(caminho.read_text(encoding="utf-8"))["vistos"])
            except (ValueError, KeyError, TypeError):
                self.vistos = set()  # arquivo estragado: recomeça em vez de travar o jogo

    @classmethod
    def padrao(cls) -> Grimorio:
        return cls(caminho_padrao())

    def ver(self, fatias: Iterable[Fatia]) -> list[Fatia]:
        """Registra as fatias que apareceram; devolve as que eram novas."""
        novas = [f for f in fatias if f.id not in self.vistos]
        if not novas:
            return []
        self.vistos.update(f.id for f in novas)
        if self.caminho is not None:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            dados = {"vistos": sorted(self.vistos)}
            self.caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        return novas

    def viu(self, fatia_id: str) -> bool:
        return fatia_id in self.vistos

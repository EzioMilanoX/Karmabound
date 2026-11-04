"""Votos de luta: o voto vinculativo feito no calor da luta. Regras puras, sem tela.

Mais limitado que o Altar (que fica entre capítulos): a cada luta a roleta oferece
um voto pronto, de um destes três tipos, e o jogador pode jurá-lo uma vez, quando
quiser no seu turno — jurar não gasta o turno.

- **Promessa:** uma meta com prazo. A força vem na hora (`agora`); cumprir dá o
  `premio`, falhar cobra a `falha`.
- **Revelação:** você expõe algo de si ao rival (ele ganha Percepção, ou o seu
  dano fica à mostra) e a técnica revelada fica muito mais forte.
- **Selo:** você sela parte de si até o fim da luta e a força selada volta, na
  hora, em outro lugar.

Os efeitos (`agora`, `premio`, `falha`) usam as mesmas chaves de `Luta.aplicar`
(as do Despertar e as de preço).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from karmabound.rodas import DADOS

TIPOS = ("promessa", "revelacao", "selo")
CONDICOES = ("vencer_em", "sem_dano", "so_golpe", "sem_defesa", "dano_em")
PILOTOS = ("inicio", "chefe", "fechar", "seguro", "vida_alta")


@dataclass(frozen=True)
class VotoDeLuta:
    id: str
    nome: str
    kanji: str
    tipo: str
    texto: str
    origem: str = ""
    agora: dict = field(default_factory=dict, hash=False, compare=False)
    condicao: dict | None = field(default=None, hash=False, compare=False)
    premio: dict = field(default_factory=dict, hash=False, compare=False)
    falha: dict = field(default_factory=dict, hash=False, compare=False)
    piloto: str = "inicio"  # quando o piloto automático jura (ver `PILOTOS`)


def carregar_votos_luta(caminho: Path | None = None) -> tuple[VotoDeLuta, ...]:
    bruto = json.loads((caminho or DADOS / "votos_luta.json").read_text(encoding="utf-8"))
    votos = tuple(VotoDeLuta(**v) for v in bruto["votos"])
    ids = [v.id for v in votos]
    if len(ids) != len(set(ids)):
        raise ValueError("voto de luta com id repetido")
    for v in votos:
        if v.tipo not in TIPOS:
            raise ValueError(f"voto de luta {v.id}: tipo '{v.tipo}' inválido")
        if v.piloto not in PILOTOS:
            raise ValueError(f"voto de luta {v.id}: piloto '{v.piloto}' inválido")
        if v.tipo == "promessa":
            if not v.condicao or set(v.condicao) - set(CONDICOES) or len(v.condicao) != 1:
                raise ValueError(f"voto de luta {v.id}: a promessa precisa de uma condição")
        elif v.condicao:
            raise ValueError(f"voto de luta {v.id}: só a promessa tem condição")
    return votos


@dataclass
class Promessa:
    """Uma promessa em andamento."""

    condicao: str
    restante: int  # turnos (seus, ou do rival em `sem_dano`); 0 = até o fim da luta
    meta: int = 0  # dano a causar (`dano_em`)
    feito: int = 0

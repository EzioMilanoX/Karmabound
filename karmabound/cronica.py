"""A Crônica: o histórico das runs e os Feitos, salvos entre sessões.

`~/.karmabound/cronica.json` (a pasta do Grimório). O Fluxo chama `registrar` no
fim de cada run; os Feitos são avaliados do estado final, então não precisam de
contadores espalhados pelo jogo. Arquivo estragado: recomeça, nunca quebra.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from karmabound.grimorio import caminho_padrao
from karmabound.jornada import Jornada


def caminho() -> Path:
    return caminho_padrao().parent / "cronica.json"


@dataclass(frozen=True)
class Feito:
    id: str
    kanji: str
    nome: str
    texto: str
    vale: Callable[[Jornada, list[dict], int, int], bool]  # (run, runs antes, vistos, total)


def _venceu(j: Jornada) -> bool:
    return j.fase == "vitoria"


def _votos(j: Jornada) -> int:
    return len(j.estado.votos.ativos) + len(j.estado.votos.quebrados)


FEITOS: tuple[Feito, ...] = (
    Feito(
        "primeira_vitoria",
        "勝",
        "O torneio é seu",
        "Vencer uma run.",
        lambda j, h, v, t: _venceu(j),
    ),
    Feito(
        "brutal",
        "鬼",
        "Além do brutal",
        "Vencer uma run no Brutal.",
        lambda j, h, v, t: _venceu(j) and j.modo == "brutal",
    ),
    Feito(
        "tres_despertares",
        "覚",
        "Desperto três vezes",
        "Despertar três vezes numa run.",
        lambda j, h, v, t: j.estado.despertares >= 3,
    ),
    Feito(
        "sem_despertar",
        "静",
        "Sem acordar",
        "Vencer sem nenhum Despertar.",
        lambda j, h, v, t: _venceu(j) and j.estado.despertares == 0,
    ),
    Feito(
        "sem_reliquias",
        "裸",
        "De mãos vazias",
        "Vencer sem nenhuma Relíquia.",
        lambda j, h, v, t: _venceu(j) and not j.estado.reliquias,
    ),
    Feito(
        "tres_votos",
        "誓",
        "Três vezes jurado",
        "Jurar três votos numa run.",
        lambda j, h, v, t: _votos(j) >= 3,
    ),
    Feito(
        "quebrou_e_venceu",
        "破",
        "A dívida paga",
        "Quebrar um voto e ainda vencer.",
        lambda j, h, v, t: _venceu(j) and bool(j.estado.votos.quebrados),
    ),
    Feito(
        "contrato",
        "契",
        "Pacto cumprido",
        "Vencer com o Contrato entre as técnicas.",
        lambda j, h, v, t: _venceu(j) and any(x.id == "contrato" for x in j.jogador.tecnicas),
    ),
    Feito(
        "invasao",
        "侵",
        "Treze lutas",
        "Vencer uma run com uma Invasão (mais de 12 lutas).",
        lambda j, h, v, t: _venceu(j) and j.estado.lutas_vencidas > 12,
    ),
    Feito(
        "diaria",
        "暦",
        "A sorte de hoje",
        "Vencer a Semente do dia.",
        lambda j, h, v, t: _venceu(j) and bool(j.diaria),
    ),
    Feito(
        "grimorio",
        "書",
        "Grimório completo",
        "Ver todas as habilidades da roleta.",
        lambda j, h, v, t: t > 0 and v >= t,
    ),
    Feito(
        "dez_runs", "道", "Dez caminhos", "Terminar dez runs.", lambda j, h, v, t: len(h) + 1 >= 10
    ),
)


class Cronica:
    def __init__(self, arquivo: Path | None = None) -> None:
        self.arquivo = arquivo
        self.runs: list[dict] = []
        self.feitos: list[str] = []
        if arquivo is not None and arquivo.exists():
            try:
                dados = json.loads(arquivo.read_text(encoding="utf-8"))
                self.runs, self.feitos = list(dados["runs"]), list(dados["feitos"])
            except (ValueError, KeyError, TypeError):
                self.runs, self.feitos = [], []

    @classmethod
    def padrao(cls) -> Cronica:
        return cls(caminho())

    def registrar(self, j: Jornada, vistos: int = 0, total: int = 0) -> list[Feito]:
        """Guarda a run que acabou e devolve os Feitos conquistados agora."""
        novos = [
            f for f in FEITOS if f.id not in self.feitos and f.vale(j, self.runs, vistos, total)
        ]
        self.runs.append(
            {
                "data": datetime.date.today().isoformat(),
                "modo": j.modo,
                "venceu": j.fase == "vitoria",
                "lutas": j.estado.lutas_vencidas,
                "dom": j.dom.nome if j.dom else "",
                "despertares": j.estado.despertares,
                "votos": _votos(j),
                "reliquias": len(j.estado.reliquias),
                "diaria": j.diaria,
                "ascensao": getattr(j, "ascensao", 0),
            }
        )
        self.feitos += [f.id for f in novos]
        if self.arquivo is not None:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            dados = {"runs": self.runs[-200:], "feitos": self.feitos}
            self.arquivo.write_text(
                json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        return novos

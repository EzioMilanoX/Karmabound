"""Opções do jogador: volume, tela cheia, velocidade das animações e dicas.

Salvas em `opcoes.json`, na mesma pasta do Grimório (`~/.karmabound`, ou
`KARMABOUND_SAVE`). `KARMABOUND_DICAS=0` desliga as dicas da primeira run (os
testes usam, para nenhuma janela de dica travar uma run jogada pelas telas).
`OPCOES` começa só em memória; o jogo carrega o arquivo ao montar o loop.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from karmabound.grimorio import caminho_padrao

VELOCIDADES = (1.0, 1.5, 2.0)


def caminho_opcoes() -> Path:
    return caminho_padrao().parent / "opcoes.json"


@dataclass
class Opcoes:
    volume_musica: int = 7  # 0 a 10
    volume_efeitos: int = 8
    mudo: bool = False
    tela_cheia: bool = False
    velocidade: float = 1.0  # multiplica o tempo das animações
    dicas: bool = True
    kokusen: bool = True  # a barra do golpe (o Kokusen); desligada, só estratégia
    dicas_vistas: list[str] = field(default_factory=list)
    caminho: Path | None = field(default=None, repr=False, compare=False)

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> Opcoes:
        caminho = caminho or caminho_opcoes()
        o = cls(caminho=caminho)
        if caminho.exists():
            try:
                dados = json.loads(caminho.read_text(encoding="utf-8"))
                for k, v in dados.items():
                    if k in o.__dataclass_fields__ and k != "caminho":
                        setattr(o, k, v)
            except (ValueError, TypeError):
                pass  # arquivo estragado: fica o padrão
        if os.environ.get("KARMABOUND_DICAS") == "0":
            o.dicas = False
        o.velocidade = o.velocidade if o.velocidade in VELOCIDADES else 1.0
        return o

    def salvar(self) -> None:
        if self.caminho is None:
            return
        dados = {k: v for k, v in asdict(self).items() if k != "caminho"}
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    def mostrar_dica(self, dica_id: str) -> bool:
        """Se a dica deve aparecer agora (e a marca como vista)."""
        if not self.dicas or dica_id in self.dicas_vistas:
            return False
        self.dicas_vistas.append(dica_id)
        self.salvar()
        return True


OPCOES = Opcoes(dicas=os.environ.get("KARMABOUND_DICAS") != "0")


def configurar(caminho: Path | None = None) -> Opcoes:
    """Carrega as opções do disco para o `OPCOES` compartilhado (o jogo chama uma vez)."""
    novas = Opcoes.carregar(caminho)
    for k in novas.__dataclass_fields__:
        setattr(OPCOES, k, getattr(novas, k))
    return OPCOES

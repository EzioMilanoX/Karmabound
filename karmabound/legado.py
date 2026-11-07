"""O Legado: o que fica de uma run para a outra. Regras puras, sem tela.

- **Memória → a roda se abre.** Cada run deixa Memória (lutas vencidas, capítulos
  fechados, vitória, Nêmesis vingada). A cada `CUSTO_ANIME` de Memória, um anime
  novo entra nas rodas. Começa com os `INICIAIS` animes mais ricos; nada mais forte
  fica para sempre: só mais variedade.
- **Maestria.** Cada uso de uma técnica numa run conta. Com `MAESTRIA[0]` usos ela
  chega à sua mão já evoluída uma vez (★); com `MAESTRIA[1]`, duas (★★).
- **Nêmesis.** Quem te matou volta numa run seguinte, mais forte e com o golpe que te
  matou. Vencê-la paga bem e a apaga; perder de novo a deixa mais forte.
- **Ascensão.** Vencer na Ascensão N de uma dificuldade abre a N+1 nela (até 10); os
  níveis e o que cada um faz estão em `ascensao.py`.

Arquivo `~/.karmabound/legado.json` (a pasta do Grimório). Só quem joga registra: o
piloto automático e o simulador nunca tocam nele. Arquivo estragado: recomeça.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from karmabound.ascensao import maximo as maximo_ascensao
from karmabound.grimorio import caminho_padrao
from karmabound.rodas import Roda, anime_de

INICIAIS = 7  # animes abertos desde a primeira run
CUSTO_ANIME = 6  # Memória por anime novo
MAESTRIA = (20, 60)  # usos para ★ e ★★
DONOS_PARA_ALEM = 3  # vitórias sobre o Dono da Roda que abrem o capítulo secreto
MEMORIA_LUTA, MEMORIA_CAPITULO, MEMORIA_VITORIA, MEMORIA_VINGANCA = 1, 2, 5, 3


def caminho() -> Path:
    return caminho_padrao().parent / "legado.json"


def ordem_dos_animes(rodas: dict[str, Roda]) -> list[str]:
    """Os animes na ordem em que se abrem: o mais rico (mais fatias) primeiro."""
    conta = Counter(anime_de(f.origem) for roda in rodas.values() for f in roda.fatias)
    conta.pop("", None)
    return sorted(conta, key=lambda a: (-conta[a], a))


def nivel_maestria(usos: int) -> int:
    return sum(usos >= m for m in MAESTRIA)


@dataclass
class Fechamento:
    """O que uma run deixou no Legado, para a tela do fim mostrar."""

    memoria: int = 0
    animes: list[str] = field(default_factory=list)  # abertos agora
    maestrias: list[tuple[str, int]] = field(default_factory=list)  # (técnica, nível novo)
    nemesis: str = ""  # "nasceu" | "cresceu" | "vingada" | ""
    nemesis_nome: str = ""
    ascensao_aberta: int = 0  # a Ascensão que esta vitória abriu (0: nenhuma)
    alem_aberto: bool = False  # esta vitória sobre o Dono abriu o capítulo secreto
    final_novo: str = ""  # um final que você ainda não tinha visto (quebrar | tomar | verdadeiro)


class Legado:
    def __init__(self, arquivo: Path | None = None, memoria_inicial: int = 0) -> None:
        """`arquivo=None`: só em memória. `memoria_inicial`: para quem já jogava antes do
        Legado existir (a Crônica conta), usada só se o arquivo ainda não existe."""
        self.arquivo = arquivo
        self.memoria = memoria_inicial
        self.usos: Counter = Counter()
        self.nemesis: dict | None = None
        self.vingancas = 0
        self.ascensoes: dict[str, int] = {}  # dificuldade -> a maior Ascensão aberta
        # Leva 5: o Dono da Roda, os finais e o bestiário
        self.donos = 0  # vezes que venceu o Dono da Roda (DONOS_PARA_ALEM abre o secreto)
        self.finais: list[str] = []  # os finais já vistos
        self.vencidos: Counter = Counter()  # vilão -> vezes que você o venceu
        self.campanhas: list[str] = []  # as campanhas do modo História já terminadas
        if arquivo is not None and arquivo.exists():
            try:
                d = json.loads(arquivo.read_text(encoding="utf-8"))
                self.memoria = int(d["memoria"])
                self.usos = Counter(d.get("usos", {}))
                self.nemesis = d.get("nemesis")
                self.vingancas = int(d.get("vingancas", 0))
                self.ascensoes = {k: int(v) for k, v in d.get("ascensoes", {}).items()}
                self.donos = int(d.get("donos", 0))
                self.finais = list(d.get("finais", []))
                self.vencidos = Counter(d.get("vencidos", {}))
                self.campanhas = list(d.get("campanhas", []))
            except (ValueError, KeyError, TypeError, AttributeError):
                self.memoria, self.usos, self.nemesis = memoria_inicial, Counter(), None
                self.ascensoes = {}

    @classmethod
    def padrao(cls, memoria_inicial: int = 0) -> Legado:
        return cls(caminho(), memoria_inicial)

    def salvar(self) -> None:
        if self.arquivo is None:
            return
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        d = {
            "memoria": self.memoria,
            "usos": dict(self.usos),
            "nemesis": self.nemesis,
            "vingancas": self.vingancas,
            "ascensoes": self.ascensoes,
            "donos": self.donos,
            "finais": self.finais,
            "vencidos": dict(self.vencidos),
            "campanhas": self.campanhas,
        }
        self.arquivo.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------------------- a roda se abre

    def abertos(self, ordem: list[str]) -> frozenset[str]:
        n = INICIAIS + self.memoria // CUSTO_ANIME
        return frozenset(ordem[:n])

    def proximo(self, ordem: list[str]) -> tuple[str, int] | None:
        """O próximo anime a abrir e a Memória que falta (None: tudo aberto)."""
        n = INICIAIS + self.memoria // CUSTO_ANIME
        if n >= len(ordem):
            return None
        return ordem[n], CUSTO_ANIME - self.memoria % CUSTO_ANIME

    # ------------------------------------------------------------- maestria

    def maestria(self) -> dict[str, int]:
        """Nível de maestria de cada técnica que já tem algum."""
        return {tid: n for tid, u in self.usos.items() if (n := nivel_maestria(u))}

    # ------------------------------------------------------------- Ascensão

    def ascensao_maxima(self, dificuldade: str) -> int:
        """A maior Ascensão aberta nesta dificuldade (0: só a run normal)."""
        return self.ascensoes.get(dificuldade, 0)

    # ------------------------------------------------------------- além da Roda

    @property
    def alem_aberto(self) -> bool:
        """O capítulo secreto: abre depois de vencer o Dono da Roda DONOS_PARA_ALEM vezes."""
        return self.donos >= DONOS_PARA_ALEM

    # ------------------------------------------------------------- fim de run

    def fechar_run(
        self,
        ordem: list[str],
        lutas: int,
        capitulos: int,
        venceu: bool,
        usos: Counter,
        vingou: bool = False,
        assassino: dict | None = None,
        nomes: dict[str, str] | None = None,
        ascensao: int = 0,
        dificuldade: str = "",
        dono: bool = False,
        final: str = "",
        vencidos: list[str] | None = None,
        campanha: str = "",
    ) -> Fechamento:
        """Registra a run que acabou. `capitulos`: fechados; `usos`: técnica → usos na run;
        `assassino`: quem te matou ({nome, estilo, tecnica, nemesis}), se perdeu.
        `ascensao`, `dificuldade`: vencer na Ascensão N abre a N+1 nessa dificuldade.
        `dono`: venceu o Dono da Roda; `final`: o final que viu; `vencidos`: os vilões que
        caíram; `campanha`: a campanha do modo História que terminou."""
        f = Fechamento()
        if dono:
            antes = self.alem_aberto
            self.donos += 1
            f.alem_aberto = self.alem_aberto and not antes
        if final and final not in self.finais:
            self.finais.append(final)
            f.final_novo = final
        self.vencidos.update(vencidos or [])
        if campanha and campanha not in self.campanhas:
            self.campanhas.append(campanha)
        if venceu and dificuldade:
            nova = min(ascensao + 1, maximo_ascensao())
            if nova > self.ascensao_maxima(dificuldade):
                self.ascensoes[dificuldade] = f.ascensao_aberta = nova
        antes_abertos = self.abertos(ordem)
        antes_nivel = self.maestria()
        f.memoria = (
            MEMORIA_LUTA * lutas
            + MEMORIA_CAPITULO * capitulos
            + MEMORIA_VITORIA * venceu
            + MEMORIA_VINGANCA * vingou
        )
        self.memoria += f.memoria
        f.animes = [a for a in ordem if a in self.abertos(ordem) and a not in antes_abertos]
        self.usos.update(usos)
        nomes = nomes or {}
        for tid, n in self.maestria().items():
            if n > antes_nivel.get(tid, 0):
                f.maestrias.append((nomes.get(tid, tid), n))
        if vingou:
            f.nemesis, f.nemesis_nome = "vingada", (self.nemesis or {}).get("nome", "")
            self.nemesis = None
            self.vingancas += 1
        if assassino is not None:
            if assassino.get("nemesis") and self.nemesis is not None:
                self.nemesis["vezes"] = self.nemesis.get("vezes", 1) + 1
                f.nemesis = "cresceu"
            else:
                self.nemesis = {
                    "nome": assassino["nome"],
                    "estilo": assassino.get("estilo", ""),
                    "tecnica": assassino.get("tecnica", ""),
                    "vezes": 1,
                }
                f.nemesis = "nasceu"
            f.nemesis_nome = self.nemesis["nome"]
        self.salvar()
        return f


def memoria_da_cronica(runs: list[dict]) -> int:
    """A Memória de quem jogou antes do Legado existir, contada pela Crônica."""
    return sum(
        MEMORIA_LUTA * r.get("lutas", 0) + MEMORIA_VITORIA * bool(r.get("venceu")) for r in runs
    )

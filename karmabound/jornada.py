"""Jornada: uma run jogada por uma pessoa, fase a fase. Regras puras, sem tela.

As regras da run estão nos passos de `run.py`; a Jornada só pára em cada decisão
do jogador e chama o passo certo. O piloto automático (`run.jogar_run`) usa os
mesmos passos, então a simulação mede este mesmo jogo.

Fases:
    destino    gira a roda do Destino (uma vez, no começo): o Dom
    arco       gira a roda do Arco (começo de cada capítulo): a regra do capítulo
    luta       a luta em andamento (`self.luta`)
    tecnica    depois de vencer: gira Técnicas e escolhe 1 de 3
    substituir os 4 espaços estão cheios: troca uma técnica ou descarta a nova
    altar      saiu o Juramento: monta um voto ou recusa
    reliquia   depois da técnica, às vezes (sempre, na Invasão): gira Relíquias
    vitoria    venceu os 3 capítulos
    derrota    caiu
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from karmabound.combate import Luta, Lutador, Tecnica, valor_tecnica
from karmabound.grimorio import Grimorio
from karmabound.mesa import Giro, Mesa
from karmabound.rodas import Fatia
from karmabound.run import (
    Contexto,
    EstadoRun,
    aplicar_arco,
    aplicar_dom,
    aplicar_voto,
    atualizar_efeitos,
    avaliar_restricoes,
    beneficios_dos_ganhos,
    comecar_luta,
    comprar_ganhos,
    custo_dos_ganhos,
    encerrar_luta,
    girar,
    medir_restricoes,
    receber_reliquia,
    receber_tecnica,
    saldo_do_voto,
    substituir_tecnica,
    vai_ter_reliquia,
)
from karmabound.votos import FimDaRun, Voto, Votos


@dataclass
class PropostaDeVoto:
    """O voto que o Altar oferece: as restrições, os pontos e a compra sugerida.

    O jogador mexe na compra; `beneficio` dá o preço de cada ganho (a tela não mostra
    números: só se um nível ainda cabe nos pontos).
    """

    voto: Voto  # os ganhos aqui são a sugestão do Altar
    sacrificio: float  # lutas vencidas a menos, medido junto
    pontos: float = 0.0  # os do voto + os guardados de votos anteriores
    beneficio: dict[str, float] = field(default_factory=dict)
    saldo: float | None = None  # só com estimar=True: lutas vencidas a mais com o voto

    def custo(self, ctx: Contexto, ganhos: list) -> float:
        return custo_dos_ganhos(ctx, ganhos, self.beneficio)

    def cabe(self, ctx: Contexto, ganhos: list, mais) -> bool:
        """Se mais um nível de `mais` cabe nos pontos (e ainda há nível a comprar)."""
        n = sum(1 for g in ganhos if g.id == mais.id)
        return n < mais.niveis and self.custo(ctx, [*ganhos, mais]) <= self.pontos + 1e-9


@dataclass
class Jornada:
    ctx: Contexto
    estado: EstadoRun
    rng: random.Random
    modo: str
    fase: str = "destino"
    luta: Luta | None = None
    giro: Giro | None = None  # o último giro, para a tela mostrar
    pendente: Fatia | None = None  # técnica nova esperando espaço
    resultado_tecnica: str = ""  # equipada | fragmento | evoluiu | cheio | altar
    aviso: str = ""  # mensagem para a próxima tela (fragmento, evolução)
    sacrificios: dict[str, dict[str, float]] = field(default_factory=dict)  # cache do Altar
    amostras_altar: int = 80
    grimorio: Grimorio | None = None  # registra o que sai da roleta (só quem joga)

    # ------------------------------------------------------------------ começo

    @classmethod
    def nova(cls, modo: str | None = None, seed: int | None = None) -> Jornada:
        ctx = Contexto.padrao(modo)
        rng = random.Random(seed)
        mesa = Mesa(ctx.rodas, ctx.raridades, ctx.config_carma, rng)
        j = ctx.combate["jogador"]
        jogador = Lutador(
            "Você",
            j["vida"],
            j["velocidade"],
            j["percepcao"],
            [Tecnica.de_fatia(ctx.tecnicas[t]) for t in j["tecnicas"]],
            carma=mesa.carma,
        )
        estado = EstadoRun(jogador, mesa, Votos(ctx.catalogo))
        return cls(ctx, estado, rng, ctx.combate["dificuldade"])

    # ------------------------------------------------------------------ atalhos

    @property
    def jogador(self) -> Lutador:
        return self.estado.jogador

    @property
    def carma(self):
        return self.estado.mesa.carma

    @property
    def n_luta(self) -> int:
        return self.estado.proxima_luta

    @property
    def capitulo(self) -> int:
        return self.estado.capitulo

    @property
    def chefe(self) -> bool:
        return self.estado.chefe

    @property
    def dom(self) -> Fatia | None:
        return self.estado.dom

    @property
    def arco(self) -> Fatia | None:
        return self.estado.arco

    @property
    def despertares(self) -> int:
        return self.estado.despertares

    def _exigir(self, *fases: str) -> None:
        if self.fase not in fases:
            raise RuntimeError(f"ação de {fases} chamada na fase '{self.fase}'")

    def _girar(self, roda: str) -> Giro:
        self.giro = girar(self.estado, self.ctx, roda)
        if self.grimorio is not None:
            self.grimorio.ver(self.giro.fatias)
        return self.giro

    # ------------------------------------------------------------------ fases

    def girar_destino(self) -> Giro:
        self._exigir("destino")
        giro = self._girar("destino")
        aplicar_dom(self.estado, self.ctx, giro.fatias[0])
        self.fase = "arco"
        return giro

    def girar_arco(self) -> Giro:
        self._exigir("arco")
        giro = self._girar("arco")
        aplicar_arco(self.estado, self.ctx, giro.fatias[0])
        self._comecar_luta()
        return giro

    def _comecar_luta(self) -> None:
        self.luta = comecar_luta(self.estado, self.ctx, self.rng)
        self.fase = "luta"

    def terminar_luta(self) -> bool:
        """Chame quando `luta.acabou`. Devolve se o jogador venceu."""
        self._exigir("luta")
        assert self.luta is not None and self.luta.acabou
        if not encerrar_luta(self.estado, self.ctx, self.luta):
            self.fase = "derrota"
            return False
        self.fase = "vitoria" if self.estado.venceu else "tecnica"
        return True

    def girar_tecnica(self) -> Giro:
        self._exigir("tecnica")
        return self._girar("tecnicas")

    def escolher_tecnica(self, indice: int) -> None:
        """Escolhe uma das opções do último giro de Técnicas (no Despertar só há uma)."""
        self._exigir("tecnica")
        assert self.giro is not None
        fatia = self.giro.fatias[indice]
        self.resultado_tecnica = receber_tecnica(self.estado, self.ctx, fatia)
        if self.resultado_tecnica == "fragmento":
            n = self.estado.fragmentos[fatia.id]
            self.aviso = f"{fatia.nome}: fragmento {n} de 2"
        elif self.resultado_tecnica == "evoluiu":
            nova = next(t for t in self.jogador.tecnicas if t.id == fatia.id)
            self.aviso = f"{nova.nome}: a técnica evoluiu"
        if self.resultado_tecnica == "altar" and self.estado.votos.pode_jurar():
            self.sacrificios = {}
            self.fase = "altar"
        elif self.resultado_tecnica == "cheio":
            self.pendente = fatia
            self.fase = "substituir"
        else:
            self._depois_da_tecnica()

    def substituir(self, sai: Tecnica | None) -> None:
        """Troca `sai` pela técnica pendente; `None` descarta a nova."""
        self._exigir("substituir")
        assert self.pendente is not None
        substituir_tecnica(self.estado, sai, self.pendente)
        self.pendente = None
        self._depois_da_tecnica()

    def _depois_da_tecnica(self) -> None:
        if vai_ter_reliquia(self.estado, self.ctx, self.rng):
            self.fase = "reliquia"
        else:
            self._proxima_luta()

    def girar_reliquia(self) -> Giro:
        self._exigir("reliquia")
        giro = self._girar("reliquias")
        receber_reliquia(self.estado, giro.fatias[0])
        self._proxima_luta()
        return giro

    def _proxima_luta(self) -> None:
        if self.estado.arco is None:
            self.fase = "arco"
        else:
            self._comecar_luta()

    # ------------------------------------------------------------------ Altar

    def pesar_restricoes(self, duracao: str = "run") -> dict[str, float]:
        """Sacrifício de cada restrição para o seu build (cacheado por duração)."""
        self._exigir("altar")
        if duracao not in self.sacrificios:
            self.sacrificios[duracao] = medir_restricoes(
                self.estado, self.ctx, duracao, self.amostras_altar, seed=self.n_luta
            )
        return self.sacrificios[duracao]

    def propor_voto(
        self, ids: list[str], duracao: str = "run", estimar: bool = False
    ) -> PropostaDeVoto | None:
        """Mede as restrições juntas, dá os pontos (com os guardados) e sugere uma compra.

        `estimar`: também mede o saldo do voto sugerido (o Altar não mostra; é para testes
        e ferramentas).
        """
        self._exigir("altar")
        cat = self.ctx.catalogo
        restricoes = [cat.restricoes[i] for i in ids]
        if not restricoes:
            return None
        individuais = self.pesar_restricoes(duracao)
        seed, n, e = self.n_luta, self.amostras_altar, self.estado
        pontos, junto = avaliar_restricoes(e, self.ctx, restricoes, individuais, duracao, n, seed)
        pontos += e.pontos_guardados
        beneficio = beneficios_dos_ganhos(e, self.ctx, restricoes, junto, duracao, n, seed)
        ganhos = comprar_ganhos(e, self.ctx, restricoes, pontos, junto, duracao, n, seed, beneficio)
        voto = Voto(restricoes, ganhos, duracao, pontos=pontos, sacrificio=junto)
        proposta = PropostaDeVoto(voto, junto, pontos, beneficio)
        if estimar:
            proposta.saldo = saldo_do_voto(e, self.ctx, voto, n, seed)
        return proposta

    def jurar(self, proposta: PropostaDeVoto, ganhos: list | None = None) -> None:
        """Jura com a compra do jogador (`ganhos`; sem ela, a sugestão). A sobra fica guardada."""
        self._exigir("altar")
        compra = list(proposta.voto.ganhos if ganhos is None else ganhos)
        custo = proposta.custo(self.ctx, compra)
        if custo > proposta.pontos + 1e-9:
            raise ValueError("a compra passa dos pontos do voto")
        proposta.voto.ganhos = compra
        proposta.voto.sobra = proposta.pontos - custo
        aplicar_voto(self.estado, self.ctx, proposta.voto)
        self.estado.pontos_guardados = proposta.voto.sobra
        self._depois_da_tecnica()

    def recusar_altar(self) -> None:
        self._exigir("altar")
        self._depois_da_tecnica()

    def quebrar_voto(self, voto: Voto, ids_quebra: list[str]) -> bool:
        """Quebra `voto` (de qualquer fase da run): perde os ganhos, metade da vida e o Carma,
        e jura um voto de quebra com as restrições `ids_quebra`, pelo prazo que faltava.

        Devolve False se a run acabou (quebrar um voto de quebra encerra a run).
        """
        cat = self.ctx.catalogo
        quebra = Voto(
            [cat.restricoes[i] for i in ids_quebra],
            [],
            voto.duracao,
            lutas_restantes=voto.lutas_restantes,
        )
        try:
            self.estado.votos.quebrar(voto, quebra, self.jogador, self.carma)
        except FimDaRun:
            self.estado.derrotado = True
            self.jogador.vida = 0
            self.fase = "derrota"
            return False
        atualizar_efeitos(self.estado)
        return True

    # ------------------------------------------------------------------ ajuda às telas

    def tecnica_mais_fraca(self) -> Tecnica:
        return min(self.jogador.tecnicas, key=valor_tecnica)

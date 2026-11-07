"""Jornada: uma run jogada por uma pessoa, fase a fase. Regras puras, sem tela.

As regras da run estão nos passos de `run.py`; a Jornada só pára em cada decisão
do jogador e chama o passo certo. O piloto automático (`run.jogar_run`) usa os
mesmos passos, então a simulação mede este mesmo jogo.

Fases:
    linhagem   gira a roda da Linhagem (uma vez, no começo): de que sangue você vem
    destino    gira a roda do Destino (uma vez, no começo): o Dom
    arco       gira a roda do Arco (começo de cada capítulo): a regra do capítulo
    caminho    antes de cada luta que não é de chefe: escolhe 1 de 3 portas (rival,
               bando, elite, encruzilhada ou a Nêmesis)
    encruzilhada  a porta sem luta: escolhe uma opção (às vezes ela leva a um giro)
    luta       a luta em andamento (`self.luta`)
    treino     depois de vencer: escolhe 1 de 3 treinos (fica mais forte pela run)
    tecnica    depois do treino: gira Técnicas e escolhe 1 de 3
    substituir os 4 espaços estão cheios: troca uma técnica ou descarta a nova (também
               quando uma fusão nasce sem espaço; depois, segue `retomar`)
    altar    o capítulo acabou: o Altar dos Votos abre (monta um voto ou recusa)
    reliquia   depois da técnica, às vezes (sempre, na Invasão): gira Relíquias
    cena       uma cena do modo História (ou o convite do Dono): avança linha a linha;
               depois, segue `cena_depois`
    convite    venceu o Dono com o capítulo secreto aberto: ir além da Roda ou terminar
    final      modo História, Torneio da Roda: Quebrar ou Tomar a Roda
    vitoria    venceu os 3 capítulos (ou o 4º, além da Roda)
    derrota    caiu
"""

from __future__ import annotations

import pickle
import random
from collections import Counter
from dataclasses import dataclass, field

from karmabound.caminho import Evento, Porta, nome_de_nemesis, pode_escolher
from karmabound.combate import HESITAR, Luta, Lutador, Tecnica, valor_tecnica
from karmabound.fusoes import fundir
from karmabound.grimorio import Grimorio
from karmabound.historias import ORIGINAL, Capitulo, Cena, carregar_historias
from karmabound.mesa import Giro, Mesa
from karmabound.rodas import Fatia
from karmabound.run import (
    Contexto,
    EstadoRun,
    aceitar_convite,
    aplicar_arco,
    aplicar_dom,
    aplicar_linhagem,
    aplicar_voto,
    atravessar_encruzilhada,
    atualizar_efeitos,
    avaliar_restricoes,
    beneficios_dos_ganhos,
    comecar_luta,
    comprar_ganhos,
    convite_aberto,
    custo_dos_ganhos,
    encerrar_luta,
    escolher_porta,
    girar,
    girar_arco,
    medir_restricoes,
    oferecer_caminho,
    oferecer_treinos,
    receber_reliquia,
    receber_tecnica,
    saldo_do_voto,
    substituir_tecnica,
    tecnicas_iniciais,
    tem_caminho,
    vai_ter_reliquia,
)
from karmabound.treino import Treino
from karmabound.treino import aplicar as aplicar_treino
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
    fase: str = "linhagem"
    luta: Luta | None = None
    giro: Giro | None = None  # o último giro, para a tela mostrar
    pendente: Fatia | None = None  # técnica nova esperando espaço
    resultado_tecnica: str = ""  # equipada | fragmento | evoluiu | cheio | altar
    aviso: str = ""  # mensagem para a próxima tela (fragmento, evolução)
    sacrificios: dict[str, dict[str, float]] = field(default_factory=dict)  # cache do Altar
    amostras_altar: int = 30
    horizonte_altar: int = 4  # o Altar mede o próximo capítulo e projeta para o resto da run
    grimorio: Grimorio | None = None  # registra o que sai da roleta (só quem joga)
    antes_da_luta: bytes | None = field(default=None, repr=False)  # a foto para continuar
    diaria: str = ""  # a data, numa run da semente do dia
    oferta_treino: tuple[Treino, ...] = ()  # os treinos que a fase "treino" oferece
    oferta_caminho: tuple[Porta, ...] = ()  # as portas que a fase "caminho" oferece
    encruzilhada: Evento | None = None  # o encontro da fase "encruzilhada"
    giro_da_encruzilhada: bool = False  # o giro veio de uma escolha, não de uma vitória
    usos: Counter = field(default_factory=Counter)  # técnica -> usos nesta run (Maestria)
    assassino: dict | None = None  # quem te matou (vira a Nêmesis no Legado)
    legado: dict = field(default_factory=dict)  # abertos/maestria/nemesis: o Contexto refeito
    # fusões (fusoes.py): as que nasceram, para a tela anunciar (ela lê e esvazia)
    fusoes_novas: list[Fatia] = field(default_factory=list)
    fila_fusao: list[Fatia] = field(default_factory=list)  # nasceram sem espaço: a trocar
    retomar: str = ""  # depois da troca de uma fusão: a fase (ou o passo "_metodo") que segue
    # Leva 5: as cenas do modo História e do capítulo secreto
    cena: Cena = ()  # as linhas da fase "cena"
    cena_depois: str = ""  # a fase (ou o passo "_metodo") que vem depois da cena

    # ------------------------------------------------------------------ começo

    @classmethod
    def nova(
        cls,
        modo: str | None = None,
        seed: int | None = None,
        jogo: str = "classico",
        anime: str = "",
        abertos: frozenset[str] | None = None,
        maestria: dict[str, int] | None = None,
        nemesis: dict | None = None,
        ascensao: int = 0,
        historia: str = "",
        alem: bool = False,
    ) -> Jornada:
        """`modo`: a dificuldade. `jogo`: Clássico, História (com `historia`), Torre sem
        fim, Desfile de chefes ou Mundo de um anime (com `anime`). `abertos`, `maestria`,
        `nemesis`: do Legado. `ascensao`: o degrau da Ascensão (0 na semente do dia).
        `alem`: o capítulo secreto está aberto (o Legado venceu o Dono vezes bastantes)."""
        legado = {"abertos": abertos, "maestria": maestria, "nemesis": nemesis}
        legado["ascensao"] = ascensao  # guardado junto: salvar.carregar refaz o Contexto
        legado["historia"], legado["alem"] = historia, alem
        ctx = Contexto.padrao(modo, jogo=jogo, anime=anime, **legado)
        rng = random.Random(seed)
        mesa = Mesa(ctx.rodas, ctx.raridades, ctx.config_carma, rng)
        j = ctx.combate["jogador"]
        jogador = Lutador(
            "Você",
            j["vida"],
            j["velocidade"],
            j["percepcao"],
            tecnicas_iniciais(ctx),
            carma=mesa.carma,
        )
        estado = EstadoRun(jogador, mesa, Votos(ctx.catalogo))
        return cls(ctx, estado, rng, ctx.combate["dificuldade"], legado=legado)

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

    @property
    def ascensao(self) -> int:
        return self.ctx.ascensao

    @property
    def proximas_portas(self) -> tuple[Porta, ...]:
        """O mapa: as portas do passo seguinte do capítulo (vazio: o próximo é o chefe)."""
        return self.estado.proximas_portas

    def _exigir(self, *fases: str) -> None:
        if self.fase not in fases:
            raise RuntimeError(f"ação de {fases} chamada na fase '{self.fase}'")

    def _girar(self, roda: str) -> Giro:
        self.giro = girar(self.estado, self.ctx, roda)
        if self.grimorio is not None:
            self.grimorio.ver(self.giro.fatias)
        return self.giro

    # ------------------------------------------------------------------ fases

    def girar_linhagem(self) -> Giro:
        self._exigir("linhagem")
        giro = self._girar("linhagem")
        aplicar_linhagem(self.estado, self.ctx, giro.fatias[0])
        self.fase = "destino"
        self._fundir("destino")
        return giro

    def girar_destino(self) -> Giro:
        self._exigir("destino")
        giro = self._girar("destino")
        aplicar_dom(self.estado, self.ctx, giro.fatias[0])
        self._ir_para_arco()
        self._fundir(self.fase)
        return giro

    def girar_arco(self) -> Giro:
        """O Arco do capítulo (na História e além da Roda, o fixo cai sem sorteio)."""
        self._exigir("arco")
        self.giro = girar_arco(self.estado, self.ctx)
        if self.grimorio is not None:
            self.grimorio.ver(self.giro.fatias)
        aplicar_arco(self.estado, self.ctx, self.giro.fatias[0])
        self._antes_da_luta()
        return self.giro

    def _antes_da_luta(self) -> None:
        """Chefe: a luta começa (na História, depois da cena dele). Senão, o caminho
        oferece as portas."""
        if tem_caminho(self.estado, self.ctx):
            self.oferta_caminho = oferecer_caminho(self.estado, self.ctx, self.rng)
            self.fase = "caminho"
            return
        cap = self.capitulo_da_cena(self.estado.capitulo)
        if self.estado.chefe and cap is not None and cap.antes_do_chefe:
            self._mostrar(cap.antes_do_chefe, "_comecar_luta")
        else:
            self._comecar_luta()

    # ------------------------------------------------------------------ cenas

    @property
    def original(self):
        """A campanha do Torneio da Roda (as cenas do Dono e de além da Roda valem também
        fora dela)."""
        return carregar_historias().get(ORIGINAL)

    def capitulo_da_cena(self, n: int) -> Capitulo | None:
        """As cenas do capítulo `n`: as da campanha; além da Roda, as do capítulo secreto."""
        if self.ctx.historia is not None:
            return self.ctx.historia.capitulo(n)
        if self.estado.alem and n > self.ctx.capitulos and self.original is not None:
            return self.original.alem
        return None

    def _mostrar(self, linhas: Cena, depois: str) -> None:
        """Abre a fase "cena" com `linhas` e segue para `depois` ao fim (sem linhas: segue já)."""
        if not linhas:
            self._seguir(depois)
            return
        self.cena, self.cena_depois, self.fase = tuple(linhas), depois, "cena"

    def avancar_cena(self) -> None:
        """A cena acabou (a tela mostrou todas as linhas): segue."""
        self._exigir("cena")
        depois, self.cena, self.cena_depois = self.cena_depois, (), ""
        self._seguir(depois)

    def _ir_para_arco(self) -> None:
        """O começo de um capítulo: a abertura dele (na História) e o giro do Arco."""
        self.fase = "arco"
        cap = self.capitulo_da_cena(self.estado.capitulo)
        if cap is not None and cap.abertura:
            self._mostrar(cap.abertura, "arco")

    def _venceu_a_run(self, capitulo: int) -> None:
        """O último chefe caiu: as cenas do fim, o convite para além da Roda ou a escolha."""
        h = self.ctx.historia
        cap = self.capitulo_da_cena(capitulo)
        depois_do_chefe = cap.depois if cap is not None else ()
        if self.estado.alem:  # o Reflexo caiu: o final verdadeiro
            self._mostrar(depois_do_chefe, "vitoria")
        elif convite_aberto(self.estado, self.ctx):
            self._mostrar(depois_do_chefe, "_convidar")
        elif h is not None and h.escolha:
            self._mostrar(depois_do_chefe, "_fim_e_escolha")
        elif h is not None:
            self._mostrar((*depois_do_chefe, *h.fim), "vitoria")
        else:
            self.fase = "vitoria"

    def _convidar(self) -> None:
        h = self.ctx.historia or self.original
        self._mostrar(h.convite if h is not None else (), "convite")

    def _fim_e_escolha(self) -> None:
        h = self.ctx.historia
        self._mostrar(h.fim if h is not None else (), "final" if h and h.escolha else "vitoria")

    @property
    def finais(self):
        """Os finais à escolha da fase "final"."""
        return self.ctx.historia.escolha if self.ctx.historia is not None else ()

    def responder_convite(self, seguir: bool) -> None:
        """Além da Roda (o capítulo secreto) ou o fim de sempre."""
        self._exigir("convite")
        if seguir:
            aceitar_convite(self.estado, self.ctx)
            self._proxima_luta()
        elif self.ctx.historia is not None and self.ctx.historia.escolha:
            self._fim_e_escolha()
        else:
            self.fase = "vitoria"

    def escolher_final(self, indice: int) -> None:
        """Quebrar ou Tomar a Roda: a cena do final escolhido, e a vitória."""
        self._exigir("final")
        final = self.finais[indice]
        self.estado.final = final.id
        self._mostrar(final.texto, "vitoria")

    def escolher_caminho(self, indice: int) -> Porta:
        """Atravessa a porta `indice`: a luta (ou a encruzilhada) começa."""
        self._exigir("caminho")
        porta = self.oferta_caminho[indice]
        self.oferta_caminho = ()
        if porta.tipo == "evento":
            self.encruzilhada = porta.evento
            self.fase = "encruzilhada"
        else:
            escolher_porta(self.estado, porta)
            self._comecar_luta()
        return porta

    def pode_escolher(self, indice: int) -> bool:
        """Se a opção `indice` da encruzilhada cabe (algumas custam Carma)."""
        assert self.encruzilhada is not None
        return pode_escolher(self.encruzilhada.opcoes[indice], self.jogador)

    def escolher_encruzilhada(self, indice: int) -> None:
        self._exigir("encruzilhada")
        assert self.encruzilhada is not None
        op = self.encruzilhada.opcoes[indice]
        if not pode_escolher(op, self.jogador):
            raise ValueError("Carma insuficiente para esta escolha")
        self.encruzilhada = None
        giro = atravessar_encruzilhada(self.estado, op)
        if giro:
            self.giro_da_encruzilhada = True
            self.fase = "tecnica" if giro == "tecnicas" else "reliquia"
        else:
            self._proxima_luta()

    def _comecar_luta(self) -> None:
        self.antes_da_luta = pickle.dumps((self.estado, self.rng))  # continuar = a mesma luta
        self.luta = comecar_luta(self.estado, self.ctx, self.rng)
        self.fase = "luta"

    def _contar_usos(self, luta: Luta) -> None:
        """A Maestria conta cada técnica das rodas que você usou nesta luta."""
        nao = {self.ctx.basico.id, HESITAR.id}
        for acao in luta.log:
            if acao.ator == self.jogador.nome and acao.tecnica not in nao:
                if acao.tecnica in self.ctx.tecnicas:
                    self.usos[acao.tecnica] += 1

    def _quem_matou(self, luta: Luta) -> dict | None:
        """O rival que deu o último golpe (vira a Nêmesis no Legado)."""
        if self.jogador.vivo:
            return None
        nomes = {r.nome: r for r in luta.rivais}
        acao = next((a for a in reversed(luta.log) if a.ator in nomes and a.dano), None)
        acao = acao or next((a for a in reversed(luta.log) if a.ator in nomes), None)
        quem = nomes[acao.ator] if acao is not None else luta.rival
        golpe = acao.tecnica if acao is not None else ""
        conhecidas = {t.id for t in quem.tecnicas if t.id != self.ctx.basico.id}
        if golpe not in conhecidas:  # o Golpe não é assinatura: leva a melhor que ele tinha
            golpe = max(quem.tecnicas, key=valor_tecnica).id if quem.tecnicas else ""
        if quem.nemesis:
            nome = quem.nome
        else:
            fatia = self.ctx.tecnicas.get(golpe) or next(
                (c for c in self.ctx.chefes if c.id == golpe), None
            )
            nome = nome_de_nemesis(quem.estilo, fatia.nome if fatia else "")
        return {
            "nome": nome,
            "estilo": quem.estilo,
            "tecnica": golpe,
            "nemesis": quem.nemesis,
            "chefe": quem.chefe,
        }

    def terminar_luta(self) -> bool:
        """Chame quando `luta.acabou`. Devolve se o jogador venceu."""
        self._exigir("luta")
        assert self.luta is not None and self.luta.acabou
        self._contar_usos(self.luta)
        capitulo = self.estado.capitulo
        chefe = any(r.chefe for r in self.luta.rivais)
        if not encerrar_luta(self.estado, self.ctx, self.luta):
            self.assassino = self._quem_matou(self.luta)
            self.fase = "derrota"
            if self.ctx.historia is not None:
                self._mostrar(self.ctx.historia.derrota, "derrota")
            return False
        if self.estado.venceu:
            self._venceu_a_run(capitulo)
            return True
        if self.ctx.treinos:
            self.oferta_treino = oferecer_treinos(self.ctx, self.rng, self.estado)
            self.fase = "treino"
        else:
            self.fase = "tecnica"
        self._fundir(self.fase)  # o Despertar da luta pode completar uma fusão
        cap = self.capitulo_da_cena(capitulo)
        if chefe and cap is not None and cap.depois:  # a cena depois do chefe do capítulo
            self._mostrar(cap.depois, self.fase)
        return True

    def escolher_treino(self, indice: int) -> Treino:
        self._exigir("treino")
        t = self.oferta_treino[indice]
        aplicar_treino(self.jogador, t)
        self.oferta_treino = ()
        self.fase = "tecnica"
        return t

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
        elif not self._fundir("_depois_da_tecnica"):
            self._depois_da_tecnica()

    def substituir(self, sai: Tecnica | None) -> None:
        """Troca `sai` pela técnica pendente (ou pela fusão que nasceu sem espaço); `None`
        descarta a nova."""
        self._exigir("substituir")
        assert self.pendente is not None
        substituir_tecnica(self.estado, sai, self.pendente, self.ctx)
        self.pendente = None
        depois, self.retomar = self.retomar or "_depois_da_tecnica", ""
        if not self._fundir(depois):
            self._seguir(depois)

    # ------------------------------------------------------------------ fusões

    def _fundir(self, depois: str) -> bool:
        """Confere as fusões (fusoes.py). O que nasceu vai para `fusoes_novas` (a tela
        anuncia), para o Grimório e para o `aviso`. Uma fusão sem espaço abre a fase de
        substituir; `depois` é o que segue a troca: uma fase ou um passo ("_metodo").
        Devolve True se parou para a troca."""
        for n in fundir(self.estado, self.ctx):
            self.fusoes_novas.append(n.fatia)
            if self.grimorio is not None:
                self.grimorio.ver([n.fatia])
            texto = f"Fusão: {n.fatia.nome} nasceu"
            self.aviso = f"{self.aviso} · {texto}" if self.aviso else texto
            if n.resultado == "cheio":
                self.fila_fusao.append(n.fatia)
        if not self.fila_fusao:
            return False
        self.pendente = self.fila_fusao.pop(0)
        self.resultado_tecnica = "cheio"
        self.retomar = depois
        self.fase = "substituir"
        return True

    def _seguir(self, depois: str) -> None:
        if depois.startswith("_"):
            getattr(self, depois)()
        else:
            self.fase = depois

    def _depois_da_tecnica(self) -> None:
        if self.giro_da_encruzilhada:  # o giro foi a escolha: o caminho segue
            self.giro_da_encruzilhada = False
            self._proxima_luta()
        elif vai_ter_reliquia(self.estado, self.ctx, self.rng):
            self.fase = "reliquia"
        else:
            self._proxima_luta()

    def girar_reliquia(self) -> Giro:
        self._exigir("reliquia")
        giro = self._girar("reliquias")
        receber_reliquia(self.estado, giro.fatias[0])
        self.giro_da_encruzilhada = False
        if not self._fundir("_proxima_luta"):
            self._proxima_luta()
        return giro

    def _proxima_luta(self) -> None:
        if self.estado.altar_pendente:  # fim de capítulo: o Altar abre antes do próximo Arco
            self.estado.altar_pendente = False
            if self.estado.votos.pode_jurar():
                self.estado.altares += 1
                self.sacrificios = {}
                self.fase = "altar"
                return
        if self.estado.arco is None:
            self._ir_para_arco()
        else:
            self._antes_da_luta()

    # ------------------------------------------------------------------ Altar

    def pesar_restricoes(self, duracao: str = "run") -> dict[str, float]:
        """Sacrifício de cada restrição para o seu build (cacheado por duração)."""
        self._exigir("altar")
        if duracao not in self.sacrificios:
            self.sacrificios[duracao] = medir_restricoes(
                self.estado,
                self.ctx,
                duracao,
                self.amostras_altar,
                seed=self.n_luta,
                horizonte=self.horizonte_altar,
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
        seed, n, e, h = self.n_luta, self.amostras_altar, self.estado, self.horizonte_altar
        pontos, junto = avaliar_restricoes(
            e, self.ctx, restricoes, individuais, duracao, n, seed, h
        )
        pontos += e.pontos_guardados
        beneficio = beneficios_dos_ganhos(e, self.ctx, restricoes, junto, duracao, n, seed, h)
        ganhos = comprar_ganhos(e, self.ctx, restricoes, pontos, junto, duracao, n, seed, beneficio)
        voto = Voto(restricoes, ganhos, duracao, pontos=pontos, sacrificio=junto)
        proposta = PropostaDeVoto(voto, junto, pontos, beneficio)
        if estimar:
            proposta.saldo = saldo_do_voto(e, self.ctx, voto, n, seed, h)
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
        self._proxima_luta()

    def recusar_altar(self) -> None:
        self._exigir("altar")
        self._proxima_luta()

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

"""Composição: a OuroborosEngine com o fluxo da run por cima.

O `Fluxo` olha a fase da `Jornada` e põe a tela certa no topo da pilha; cada
tela, ao terminar, chama de volta `Fluxo.passo`. Nenhuma regra mora aqui.

Por cima das telas da run, o Fluxo empilha a pausa (Esc), as opções, a quebra de
um voto e as dicas da primeira run; cada uma desempilha ao fechar.

Entre uma fase e a tela dela, o Fluxo anuncia o que acabou de acontecer: a fusão que
nasceu (`FusaoScene`, esvazia `Jornada.fusoes_novas`) e o aliado que chegou
(`AliadoScene`, comparando `EstadoRun.aliado` com o último anunciado). O Grimório guarda
as fusões, os aliados e os afixos de elite que o jogador conheceu.

Toda troca de tela da run passa pela `Transicao` (transicoes.py): a pincelada de tinta
cobre a tela velha e descobre a nova; entrar na luta é um corte na diagonal. Ela desenha
pelo callback de UI do GameLoop, por cima de qualquer tela, sem que a tela saiba.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from ouroboros.bootstrap.composition_root import CompositionRoot
from ouroboros.bootstrap.engine_config import EngineConfig
from ouroboros.bootstrap.game_loop import GameLoop
from ouroboros.bootstrap.scene import GameplayScene

from karmabound import livre, opcoes, salvar
from karmabound.aliados import aliado as aliado_de
from karmabound.cronica import Cronica
from karmabound.grimorio import Grimorio
from karmabound.jornada import Jornada
from karmabound.legado import Legado, memoria_da_cronica, ordem_dos_animes
from karmabound.mesa import Mesa
from karmabound.ressonancia import ressonancias_ativas
from karmabound.rodas import DADOS, carregar_rodas
from karmabound.run import Contexto
from karmabound.som import SOM
from karmabound.tela_caminho import CaminhoScene, EncruzilhadaScene
from karmabound.tela_cronica import CronicaScene
from karmabound.tela_grimorio import GrimorioScene
from karmabound.tela_historia import CenaScene, EscolhaScene
from karmabound.tela_livre import LivreScene
from karmabound.tela_luta import LutaScene
from karmabound.tela_menus import (
    AliadoScene,
    AltarScene,
    FimScene,
    FusaoScene,
    SubstituirScene,
    TituloScene,
    TreinoScene,
)
from karmabound.tela_pacto import PactoScene
from karmabound.tela_pausa import DicaScene, OpcoesScene, PausaScene, VotosScene
from karmabound.tela_roleta import RoletaScene
from karmabound.transicoes import Transicao
from karmabound.visual import ALTURA, FONTE_PINCEL, LARGURA

FONTES = Path(__file__).resolve().parent.parent / "assets" / "fonts"

TITULOS_RODA = {
    "linhagem": "Seu sangue",
    "destino": "Seu destino",
    "arco": "O arco do capítulo",
    "tecnicas": "Uma técnica nova",
    "reliquias": "Uma relíquia",
}


def _montar_loop() -> GameLoop:
    config = EngineConfig(
        window_width=LARGURA,
        window_height=ALTURA,
        window_title="Karmabound",
        entity_capacity=8,  # o jogo não usa entidades; o World só precisa existir
        difficulty_path=str(DADOS / "balanceamento.json"),
        input_bindings_path=str(DADOS / "controles.json"),
    )
    loop = CompositionRoot(config).build()
    loop.renderer.load_font(FONTE_PINCEL, str(FONTES / "YujiSyuku-Regular.ttf"))
    escolhas = opcoes.configurar()
    SOM.configurar(loop.audio_engine)
    if escolhas.tela_cheia:
        try:
            loop.renderer.set_fullscreen(True)
        except Exception:
            escolhas.tela_cheia = False
    return loop


KANJI_FINAL = {"quebrar": "砕", "tomar": "握"}
PROMESSA_FINAL = {  # o que cada carta promete (a cena do final conta o resto)
    "quebrar": "Todos livres, inclusive do poder. Você deixa de ser quem é.",
    "tomar": "Você senta no eixo. O ciclo continua, agora pela sua mão.",
}


def final_da_run(j: Jornada) -> str:
    """O final que a run viu: o escolhido na História, ou o verdadeiro (além da Roda)."""
    if j.fase != "vitoria":
        return ""
    if j.estado.alem:
        return "verdadeiro"
    return j.estado.final


def vencidos_da_run(j: Jornada) -> list[str]:
    """Os vilões que caíram nesta run (numa derrota, o último visto foi quem venceu)."""
    vistos = list(j.estado.viloes_vistos)
    return vistos[:-1] if j.fase == "derrota" and vistos else vistos


class Fluxo:
    def __init__(self, loop: GameLoop, seed: int | None = None) -> None:
        self.loop = loop
        self.seed = seed
        self.jornada: Jornada | None = None
        self.grimorio = Grimorio.padrao()
        self.cronica = Cronica.padrao()
        # o Legado: quem já jogava antes dele começa com a Memória que a Crônica conta
        self.legado = Legado.padrao(memoria_inicial=memoria_da_cronica(self.cronica.runs))
        self.ctx_completo = Contexto.padrao()  # as rodas inteiras: a ordem em que os animes abrem
        self.ordem = ordem_dos_animes(self.ctx_completo.rodas)
        self.transicao = Transicao(lambda: self.loop.input_provider, lambda: self.loop.world)
        self.aliado_anunciado = ""  # o aliado que o jogador já viu chegar nesta run
        self.veio_de = ""  # a última fase mostrada (de onde veio o aliado)
        self.modo_livre: str | None = None  # o Laboratório (livre.py): a dificuldade e a build
        self.escolha_livre: dict = {}
        loop.set_on_draw_ui(self.transicao.quadro)

    @property
    def entrada(self):
        return self.loop.input_provider

    def _cena(self, cena) -> None:
        """Troca a tela: a nova já fica no topo (e recebe entrada); a tinta cobre a troca."""
        velha = self.loop.current_scene
        if isinstance(velha, GameplayScene):  # a abertura do jogo: nada para cobrir
            velha = None
        cena.sem_revelar = True  # quem revela a tela nova é a transição
        self.loop.reset_scenes(cena)
        luta = isinstance(cena, LutaScene)
        if luta:
            SOM.tocar("corte")
        self.transicao.comecar(velha, "corte" if luta else "tinta")

    def _rodape_legado(self) -> list[str]:
        """'Memória 14 · próximo anime em 4' e a Nêmesis à espera, para o canto do título."""
        prox = self.legado.proximo(self.ordem)
        resto = f"próximo anime em {prox[1]}" if prox else "todos os animes abertos"
        linhas = [f"Memória {self.legado.memoria} · {resto}"]
        if self.legado.nemesis:
            linhas.append(f"Nêmesis à espera: {self.legado.nemesis.get('nome', '')}")
        return linhas

    def titulo(self) -> None:
        self.jornada = None
        hoje = datetime.date.today().isoformat()
        self._cena(
            TituloScene(
                self.entrada,
                self.comecar,
                self.loop.stop,
                self.abrir_grimorio,
                ao_opcoes=lambda: self.abrir_opcoes(self.loop.current_scene),
                continuar=salvar.resumo(),
                ao_continuar=self.continuar,
                ao_diaria=self.semente_do_dia,
                recorde_diaria=salvar.melhor_diaria(hoje),
                ao_cronica=self.abrir_cronica,
                abertos=self.legado.abertos(self.ordem),
                legado=self._rodape_legado(),
                ascensoes=dict(self.legado.ascensoes),
                campanhas=list(self.legado.campanhas),
                ao_votos=self.abrir_pacto,
                ao_segredo=self.legado.alternar_segredos,
                ao_livre=self.abrir_livre,
                segredos=self.legado.segredos,
                votos=self._resumo_pacto(),
            )
        )
        if any(n > 0 for n in self.legado.ascensoes.values()):
            self.dica("ascensao")

    def _resumo_pacto(self) -> str:
        p = self.legado.pacto
        r, g = len(p.get("restricoes", [])), len(p.get("ganhos", []))
        if not r:
            return ""
        return f"{r} restrição" + ("ões" if r > 1 else "") + (f" · {g} ganhos" if g else "")

    def abrir_pacto(self) -> None:
        """Os votos do menu: jurados antes da run, valem a run inteira (pacto.py)."""
        cat = self.ctx_completo.catalogo
        nomes = {}
        for roda in carregar_rodas(self.ctx_completo.raridades).values():
            nomes.update({f.id: f.nome for f in roda.fatias})

        def voltar(escolha: dict) -> None:
            self.legado.pacto = escolha
            self.legado.salvar()
            self.titulo()

        self._cena(
            PactoScene(
                cat, self.legado.pacto, nomes, self.legado.desbloqueios, self.entrada, voltar
            )
        )

    def abrir_livre(self, modo: str | None = None) -> None:
        """O Laboratório (livre.py): a build e o rival a dedo; a luta volta para cá."""
        self.modo_livre = modo or self.modo_livre

        def lutar(escolha: dict) -> None:
            self.escolha_livre = escolha
            self.jornada = livre.montar(escolha, self.modo_livre)
            self.jornada.grimorio = self.grimorio
            self._cena(
                LutaScene(
                    self.jornada,
                    self.entrada,
                    lambda _v: self.abrir_livre(),
                    self.pausar,
                    self.dica,
                )
            )

        def voltar(escolha: dict) -> None:
            self.escolha_livre = escolha
            self.titulo()

        self._cena(LivreScene(self.modo_livre, self.escolha_livre, self.entrada, lutar, voltar))

    def abrir_cronica(self) -> None:
        self._cena(CronicaScene(self.cronica, self.entrada, self.titulo, self.titulo))

    def abrir_grimorio(self) -> None:
        self._cena(
            GrimorioScene(
                self.grimorio,
                self.entrada,
                self.titulo,
                self.titulo,
                ctx=self.ctx_completo,
                abertos=self.legado.abertos(self.ordem),
                usos=self.legado.usos,
            )
        )

    # ------------------------------------------------------------------ por cima das telas

    def _fechar(self) -> None:
        self.loop.pop_scene()

    def pausar(self) -> None:
        """Esc numa tela da run: a pausa por cima dela."""
        baixo = self.loop.current_scene
        self.loop.push_scene(
            PausaScene(baixo, self.jornada, self.entrada, self._fechar, self.loop.stop, self)
        )

    def abrir_opcoes(self, baixo) -> None:
        self.loop.push_scene(
            OpcoesScene(baixo, self.entrada, self._fechar, self.loop.stop, self.loop.renderer)
        )

    def abrir_votos(self, baixo) -> None:
        self.loop.push_scene(
            VotosScene(baixo, self.jornada, self.entrada, self._fechar, self.loop.stop, self.passo)
        )

    def dica(self, dica_id: str) -> None:
        """A dica da primeira vez de cada sistema (uma vez só, e só com as dicas ligadas)."""
        if opcoes.OPCOES.mostrar_dica(dica_id):
            baixo = self.loop.current_scene
            self.loop.push_scene(
                DicaScene(baixo, dica_id, self.entrada, self._fechar, self.loop.stop)
            )

    def comecar(
        self,
        modo: str,
        seed: int | None = None,
        diaria: str = "",
        jogo: str = "classico",
        anime: str = "",
        ascensao: int = 0,
        historia: str = "",
    ) -> None:
        """`ascensao`: o degrau escolhido no título (a semente do dia joga sempre na 0).
        `historia`: a campanha do modo História."""
        seed = self.seed if seed is None else seed
        legado = {}
        if not diaria:  # a semente do dia é igual para todos: tudo aberto, sem Legado
            legado = {
                "abertos": self.legado.abertos(self.ordem),
                "maestria": self.legado.maestria(),
                "nemesis": dict(self.legado.nemesis) if self.legado.nemesis else None,
            }
            legado["alem"] = self.legado.alem_aberto  # o capítulo secreto (o Dono convida)
            legado["pacto"] = self.legado.pacto  # os votos jurados no menu (pacto.py)
            legado["desbloqueios"] = frozenset(self.legado.desbloqueios)
            legado["memes"] = self.legado.segredos  # os chefes secretos (memes.py)
        else:
            ascensao = 0
        self.jornada = Jornada.nova(
            modo, seed, jogo=jogo, anime=anime, ascensao=ascensao, historia=historia, **legado
        )
        self.jornada.grimorio = self.grimorio
        self.jornada.diaria = diaria
        self.aliado_anunciado, self.veio_de = "", ""
        self.passo()

    def continuar(self) -> None:
        """A run salva, de onde parou (no meio de uma luta: a mesma luta, desde o começo)."""
        j = salvar.carregar()
        if j is None:
            self.titulo()
            return
        j.grimorio = self.grimorio
        self.jornada = j
        self.aliado_anunciado, self.veio_de = j.estado.aliado, ""
        self.passo()

    def semente_do_dia(self) -> None:
        """Todo mundo gira a mesma sorte hoje: Difícil, seed tirada da data."""
        hoje = datetime.date.today()
        self.comecar("dificil", seed=int(hoje.strftime("%Y%m%d")), diaria=hoje.isoformat())

    def _roleta(self, roda: str, girar, depois) -> None:
        j = self.jornada
        titulo = TITULOS_RODA[roda]
        if roda == "arco":
            titulo = f"Capítulo {j.capitulo}: {titulo.lower()}"
        self._cena(
            RoletaScene(
                j.estado.mesa,
                self.entrada,
                self.loop.stop,
                roda_fixa=roda,
                girar=girar,
                ao_concluir=depois,
                titulo=titulo,
                jornada=j,
            )
        )
        self.loop.current_scene.ao_sair = self.pausar

    def _anunciar(self, j: Jornada) -> bool:
        """Antes da tela da fase: a fusão que nasceu e o aliado que chegou, um anúncio por
        vez (cada um chama `passo` de volta ao terminar). Devolve se anunciou algo."""
        if j.fusoes_novas:
            novas = list(j.fusoes_novas)
            j.fusoes_novas.clear()
            self.grimorio.marcar("fusoes", j.estado.fusoes_nascidas)
            self._cena(FusaoScene(j, novas, self.entrada, self.passo, self.pausar))
            self.dica("fusao")
            return True
        if j.estado.aliado != self.aliado_anunciado:
            self.aliado_anunciado = j.estado.aliado
            a = aliado_de(j.estado.aliado)
            if a is not None:
                self.grimorio.marcar("aliados", [a.id])
                motivo = {
                    "luta": "Quem a elite mantinha preso agora segue você.",
                    "encruzilhada": "O lutador ferido da estrada agora segue você.",
                }.get(self.veio_de, "")
                self._cena(AliadoScene(j, a, self.entrada, self.passo, self.pausar, motivo))
                self.dica("aliado")
                return True
        return False

    def passo(self, *_args) -> None:
        """Mostra a tela da fase atual da Jornada (antes, os anúncios do que mudou)."""
        j = self.jornada
        fase = j.fase
        if fase not in ("vitoria", "derrota") and self._anunciar(j):
            return
        self.veio_de = fase
        if fase == "luta":  # os afixos da elite entram no Grimório
            afixos = [a for r in j.luta.rivais for a in getattr(r, "afixos", ())]
            if afixos:
                self.grimorio.marcar("afixos", afixos)
            viloes = [r.vilao for r in j.luta.rivais if getattr(r, "vilao", "")]
            if viloes:  # o bestiário: quem você enfrentou
                self.grimorio.marcar("viloes", viloes)
        if fase == "linhagem":
            self._roleta("linhagem", j.girar_linhagem, self.passo)
        elif fase == "destino":
            self._roleta("destino", j.girar_destino, self.passo)
        elif fase == "arco":
            self._roleta("arco", j.girar_arco, self.passo)
        elif fase == "luta":
            self._cena(LutaScene(j, self.entrada, self._fim_da_luta, self.pausar, self.dica))
        elif fase == "caminho":
            self._cena(CaminhoScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "encruzilhada":
            self._cena(EncruzilhadaScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "treino":
            self._cena(TreinoScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "tecnica":
            self._roleta("tecnicas", j.girar_tecnica, self._tecnica_escolhida)
        elif fase == "substituir":
            self._cena(SubstituirScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "altar":
            self._cena(AltarScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "reliquia":
            self._roleta("reliquias", j.girar_reliquia, self.passo)
        elif fase == "cena":
            self._cena(CenaScene(j, self.entrada, self.passo, self.pausar))
        elif fase == "convite":
            self._cena(
                EscolhaScene(
                    "輪  A Roda range",
                    "Há algo do outro lado. Você pode terminar aqui, ou ir além.",
                    [
                        ("越", "Ir além da Roda", "Um capítulo a mais, e quem espera no fim dele."),
                        ("終", "Terminar aqui", "A vitória que você já tem."),
                    ],
                    self.entrada,
                    lambda i: (j.responder_convite(i == 0), self.passo()),
                    self.pausar,
                    arco=j.arco.id if j.arco else None,
                )
            )
        elif fase == "final":
            self._cena(
                EscolhaScene(
                    "主  O eixo está vazio",
                    "A Roda espera a sua mão.",
                    [
                        (KANJI_FINAL.get(f.id, "輪"), f.nome, PROMESSA_FINAL.get(f.id, ""))
                        for f in j.finais
                    ],
                    self.entrada,
                    lambda i: (j.escolher_final(i), self.passo()),
                    self.pausar,
                    arco=j.arco.id if j.arco else None,
                )
            )
        else:  # vitoria | derrota
            salvar.apagar()
            recorde = None
            if j.diaria:
                recorde = salvar.registrar_diaria(j.diaria, j.estado.lutas_vencidas)
            elif j.ctx.jogo == "torre":  # na Torre, o recorde é a altura
                chave = salvar.chave_torre(j.modo)
                recorde = salvar.registrar_recorde(chave, j.estado.lutas_vencidas)
            total = sum(len(r.fatias) for r in j.ctx.rodas.values()) + len(j.ctx.chefes)
            feitos = self.cronica.registrar(j, len(self.grimorio.vistos), total)
            fechamento = self._fechar_legado(j)
            self._cena(
                FimScene(
                    j,
                    self.entrada,
                    self.titulo,
                    self.loop.stop,
                    recorde,
                    feitos,
                    fechamento=fechamento,
                    proximo=self.legado.proximo(self.ordem),
                )
            )
            return
        salvar.salvar(j)
        dica = {
            "linhagem": "roleta",
            "destino": "roleta",
            "arco": "arco",
            "caminho": "caminho",
            "encruzilhada": "encruzilhada",
            "luta": "luta",
            "treino": "treino",
            "tecnica": "tecnicas",
            "substituir": "espacos",
            "altar": "altar",
            "reliquia": "reliquia",
        }.get(fase)
        if dica:
            self.dica(dica)
        if ressonancias_ativas(j.estado):
            self.dica("ressonancia")

    def _fechar_legado(self, j: Jornada):
        """A run acabou: o que ela deixa no Legado (Memória, Maestria, a Nêmesis).

        Na semente do dia, a Memória e os usos contam, mas quem te matou não vira Nêmesis
        (a run dela não tem Legado nenhum)."""
        e = j.estado
        nomes = {tid: f.nome for tid, f in self.ctx_completo.tecnicas.items()}
        return self.legado.fechar_run(
            self.ordem,
            lutas=e.lutas_vencidas,
            capitulos=e.capitulo - 1,
            venceu=j.fase == "vitoria",
            usos=j.usos,
            vingou=e.vingou,
            assassino=None if j.diaria else j.assassino,
            nomes=nomes,
            ascensao=j.ascensao,
            dificuldade=j.modo,
            dono=e.dono_vencido and not j.diaria,
            final=final_da_run(j),
            vencidos=vencidos_da_run(j),
            campanha=j.ctx.historia.id if j.ctx.historia and j.fase == "vitoria" else "",
            recompensas=j.recompensas_cumpridas() if not j.diaria else [],
        )

    def _fim_da_luta(self, _venceu: bool) -> None:
        self.jornada.terminar_luta()
        self.passo()

    def _tecnica_escolhida(self, indice: int) -> None:
        self.jornada.escolher_tecnica(indice)
        self.passo()


def build_game(seed: int | None = None, roleta: bool = False) -> GameLoop:
    """O jogo completo (título → run). `roleta=True`: só a caixa de areia da roleta."""
    loop = _montar_loop()
    if roleta:
        loop.reset_scenes(RoletaScene(Mesa.padrao(seed), loop.input_provider, ao_sair=loop.stop))
    else:
        fluxo = Fluxo(loop, seed)
        loop.fluxo = fluxo  # para testes e ferramentas chegarem ao fluxo
        fluxo.titulo()
    return loop


def run(headless: bool = False, roleta: bool = False) -> None:
    """Abre o jogo. headless=True desenha um quadro e sai (para testes)."""
    loop = build_game(roleta=roleta)
    if headless:
        loop.tick_once(1 / 60)
        loop.renderer.shutdown()
        return
    try:
        loop.run()
    finally:
        loop.renderer.shutdown()
